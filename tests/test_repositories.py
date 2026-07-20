"""Tests for the Phase 2 repository layer.

These exercise real SQLAlchemy queries against an in-memory SQLite
DB (see conftest.py's `db_session` fixture) - not mocks - so they
also double as a smoke test that the ORM models and schema are
consistent with each other.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import ValidationError
from app.models.enums import CardState, CEFRLevel, LearningGoal, ReviewRating, WordSource
from app.repositories.card_repository import CardRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.user_repository import UserRepository
from app.repositories.word_repository import WordRepository
from app.vocabulary.oxford_loader import load_oxford3000


def test_create_and_fetch_user(db_session):
    repo = UserRepository(db_session)
    user = repo.create(
        telegram_id=123456,
        username="student1",
        level=CEFRLevel.B1,
        learning_goal=LearningGoal.IELTS,
        daily_goal=10,
    )

    fetched = repo.get_by_telegram_id(123456)
    assert fetched is not None
    assert fetched.id == user.id
    assert fetched.level == CEFRLevel.B1
    assert fetched.learning_mode.value == "standard"  # default applied


def test_update_user_settings(db_session):
    repo = UserRepository(db_session)
    user = repo.create(
        telegram_id=1,
        username=None,
        level=CEFRLevel.A2,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=5,
    )

    repo.update(user, daily_goal=20, reminder_time="08:30")

    assert user.daily_goal == 20
    assert user.reminder_time == "08:30"

    with pytest.raises(AttributeError):
        repo.update(user, not_a_real_field=1)


def test_word_search_matches_word_and_meaning(db_session):
    repo = WordRepository(db_session)
    repo.create(word="abandon", meaning="ترک کردن", source=WordSource.OXFORD_3000)
    repo.create(word="maintain", meaning="حفظ کردن", source=WordSource.OXFORD_3000)

    results = repo.search("abandon")
    assert len(results) == 1
    assert results[0].word == "abandon"


def test_bulk_create_and_count_by_source(db_session):
    repo = WordRepository(db_session)
    repo.bulk_create(
        [
            {"word": "abandon", "meaning": "x", "source": WordSource.OXFORD_3000},
            {"word": "maintain", "meaning": "y", "source": WordSource.OXFORD_3000},
            {"word": "sustainable", "meaning": "z", "source": WordSource.IELTS, "ielts_band": "8+"},
        ]
    )

    assert repo.count_by_source(WordSource.OXFORD_3000) == 2
    assert repo.count_by_source(WordSource.IELTS) == 1


def test_card_due_and_new_queues(db_session):
    user_repo = UserRepository(db_session)
    word_repo = WordRepository(db_session)
    card_repo = CardRepository(db_session)

    user = user_repo.create(
        telegram_id=42,
        username="learner",
        level=CEFRLevel.B1,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=10,
    )
    word = word_repo.create(word="accurate", meaning="دقیق", source=WordSource.OXFORD_3000)

    now = datetime.now(timezone.utc)
    new_card = card_repo.create(user_id=user.id, word_id=word.id, due_date=now)

    assert card_repo.list_new(user.id, limit=10) == [new_card]
    assert card_repo.list_due(user.id, as_of=now) == [new_card]

    card_repo.update_after_review(
        new_card,
        stability=2.5,
        difficulty=5.0,
        due_date=now + timedelta(days=2),
        state=CardState.REVIEW,
        reviewed_at=now,
    )

    assert new_card.repetitions == 1
    assert new_card.state == CardState.REVIEW
    # No longer "new" or currently due (due_date pushed into the future).
    assert card_repo.list_new(user.id, limit=10) == []
    assert card_repo.list_due(user.id, as_of=now) == []


def test_review_accuracy_calculation(db_session):
    user_repo = UserRepository(db_session)
    word_repo = WordRepository(db_session)
    review_repo = ReviewRepository(db_session)

    user = user_repo.create(
        telegram_id=7,
        username=None,
        level=CEFRLevel.A1,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=5,
    )
    word = word_repo.create(word="opportunity", meaning="فرصت", source=WordSource.OXFORD_3000)

    review_repo.create(user_id=user.id, word_id=word.id, rating=ReviewRating.GOOD)
    review_repo.create(user_id=user.id, word_id=word.id, rating=ReviewRating.AGAIN)
    review_repo.create(user_id=user.id, word_id=word.id, rating=ReviewRating.EASY)
    review_repo.create(user_id=user.id, word_id=word.id, rating=ReviewRating.HARD)

    # 2 of 4 ratings (Good, Easy) count as correct.
    assert review_repo.accuracy_for_user(user.id) == pytest.approx(0.5)


def test_progress_get_or_create_and_update(db_session):
    user_repo = UserRepository(db_session)
    progress_repo = ProgressRepository(db_session)

    user = user_repo.create(
        telegram_id=99,
        username=None,
        level=CEFRLevel.C1,
        learning_goal=LearningGoal.ACADEMIC,
        daily_goal=20,
    )

    progress = progress_repo.get_or_create(user.id)
    assert progress.streak == 0
    assert progress.xp == 0

    progress_repo.update(progress, streak=5, xp=120)
    reloaded = progress_repo.get(user.id)
    assert reloaded.streak == 5
    assert reloaded.xp == 120


def test_oxford_loader_rejects_blank_word(tmp_path):
    bad_file = tmp_path / "bad.json"
    bad_file.write_text('[{"word": "  ", "meaning": "x"}]', encoding="utf-8")

    with pytest.raises(ValidationError):
        load_oxford3000(bad_file)


def test_oxford_loader_loads_valid_file(tmp_path):
    good_file = tmp_path / "good.json"
    good_file.write_text(
        '[{"word": "abandon", "meaning": "ترک کردن", "level": "B2"}]', encoding="utf-8"
    )

    words = load_oxford3000(good_file)
    assert len(words) == 1
    assert words[0]["word"] == "abandon"
    assert words[0]["source"] == WordSource.OXFORD_3000
