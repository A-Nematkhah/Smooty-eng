"""Tests for `LearningService` (Phase 5)."""

from __future__ import annotations

import pytest

from app.core.exceptions import CardNotFoundError, DuplicateEntityError
from app.models.enums import (
    CEFRLevel,
    CardState,
    LearningGoal,
    LearningMode,
    WordSource,
)
from app.repositories.card_repository import CardRepository
from app.repositories.user_repository import UserRepository
from app.repositories.word_repository import WordRepository
from app.services.learning_service import LearningService


def _make_user(db_session, *, telegram_id=1, level=CEFRLevel.B1, goal=LearningGoal.GENERAL, mode=LearningMode.STANDARD):
    user = UserRepository(db_session).create(
        telegram_id=telegram_id,
        username="learner",
        level=level,
        learning_goal=goal,
        daily_goal=3,
    )
    if mode != LearningMode.STANDARD:
        UserRepository(db_session).update(user, learning_mode=mode)
    return user


def _seed_words(db_session, n=5, level=CEFRLevel.B1, source=WordSource.OXFORD_3000):
    repo = WordRepository(db_session)
    return [
        repo.create(word=f"word{i}", meaning=f"meaning{i}", level=level, source=source)
        for i in range(n)
    ]


def test_get_new_words_prefers_matching_level_and_source(db_session):
    user = _make_user(db_session, level=CEFRLevel.B1)
    matching = _seed_words(db_session, n=3, level=CEFRLevel.B1, source=WordSource.OXFORD_3000)
    _seed_words(db_session, n=3, level=CEFRLevel.C1, source=WordSource.OXFORD_3000)

    service = LearningService(db_session)
    words = service.get_new_words(user, limit=3)

    assert {w.id for w in words} == {w.id for w in matching}


def test_get_new_words_falls_back_when_not_enough_matches(db_session):
    user = _make_user(db_session, level=CEFRLevel.B1)
    _seed_words(db_session, n=1, level=CEFRLevel.B1, source=WordSource.OXFORD_3000)
    _seed_words(db_session, n=5, level=CEFRLevel.C1, source=WordSource.OXFORD_3000)

    service = LearningService(db_session)
    words = service.get_new_words(user, limit=3)

    assert len(words) == 3  # backfilled from other levels


def test_get_new_words_excludes_already_enrolled(db_session):
    user = _make_user(db_session)
    words = _seed_words(db_session, n=2)
    service = LearningService(db_session)
    service.enroll_word(user.id, words[0].id)

    remaining = service.get_new_words(user, limit=5)
    assert words[0].id not in {w.id for w in remaining}
    assert words[1].id in {w.id for w in remaining}


def test_ielts_focus_mode_prefers_ielts_words(db_session):
    user = _make_user(db_session, mode=LearningMode.IELTS_FOCUS)
    ielts_words = _seed_words(db_session, n=2, source=WordSource.IELTS)
    _seed_words(db_session, n=2, source=WordSource.OXFORD_3000)

    service = LearningService(db_session)
    words = service.get_new_words(user, limit=2)

    assert {w.id for w in words} == {w.id for w in ielts_words}


def test_enroll_word_is_idempotent(db_session):
    user = _make_user(db_session)
    word = _seed_words(db_session, n=1)[0]
    service = LearningService(db_session)

    card1 = service.enroll_word(user.id, word.id)
    card2 = service.enroll_word(user.id, word.id)

    assert card1.id == card2.id
    assert card1.state == CardState.NEW


def test_add_custom_word_creates_and_enrolls(db_session):
    user = _make_user(db_session)
    service = LearningService(db_session)

    result = service.add_custom_word(
        user, word="serendipity", meaning="تصادف خوشایند", example="Finding this cafe was pure serendipity."
    )

    assert result.word.source == WordSource.CUSTOM
    assert result.card.user_id == user.id
    assert result.card.word_id == result.word.id


def test_add_custom_word_rejects_duplicate(db_session):
    user = _make_user(db_session)
    service = LearningService(db_session)
    service.add_custom_word(user, word="serendipity", meaning="x")

    with pytest.raises(DuplicateEntityError):
        service.add_custom_word(user, word="Serendipity", meaning="y")


def test_add_custom_word_rejects_blank_fields(db_session):
    user = _make_user(db_session)
    service = LearningService(db_session)

    with pytest.raises(ValueError):
        service.add_custom_word(user, word="   ", meaning="something")


def test_search_finds_by_word_or_meaning(db_session):
    WordRepository(db_session).create(
        word="accurate", meaning="دقیق", source=WordSource.OXFORD_3000
    )
    service = LearningService(db_session)

    assert len(service.search("accurate")) == 1
    assert len(service.search("دقیق")) == 1
    assert len(service.search("nonexistent")) == 0


def test_toggle_favorite_flips_state_and_rejects_other_users(db_session):
    owner = _make_user(db_session, telegram_id=1)
    intruder = _make_user(db_session, telegram_id=2)
    word = _seed_words(db_session, n=1)[0]
    service = LearningService(db_session)
    card = service.enroll_word(owner.id, word.id)

    updated = service.toggle_favorite(owner.id, card.id)
    assert updated.is_favorite is True
    updated_again = service.toggle_favorite(owner.id, card.id)
    assert updated_again.is_favorite is False

    with pytest.raises(CardNotFoundError):
        service.toggle_favorite(intruder.id, card.id)


def test_list_favorites_returns_only_favorited_cards(db_session):
    user = _make_user(db_session)
    words = _seed_words(db_session, n=3)
    service = LearningService(db_session)
    cards = [service.enroll_word(user.id, w.id) for w in words]
    service.toggle_favorite(user.id, cards[0].id)

    favorites = service.list_favorites(user.id)
    assert len(favorites) == 1
    assert favorites[0].word.id == words[0].id


def test_list_difficult_words_orders_by_difficulty_desc(db_session):
    user = _make_user(db_session)
    words = _seed_words(db_session, n=2)
    card_repo = CardRepository(db_session)
    service = LearningService(db_session)

    card_low = service.enroll_word(user.id, words[0].id)
    card_high = service.enroll_word(user.id, words[1].id)

    import datetime

    now = datetime.datetime.now(datetime.timezone.utc)
    card_repo.update_after_review(
        card_low, stability=5, difficulty=2.0, due_date=now, state=CardState.REVIEW, reviewed_at=now
    )
    card_repo.update_after_review(
        card_high, stability=5, difficulty=9.0, due_date=now, state=CardState.REVIEW, reviewed_at=now
    )

    difficult = service.list_difficult_words(user.id)
    assert difficult[0].word.id == words[1].id
