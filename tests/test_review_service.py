"""Tests for `ReviewService` (Phase 4) - the FSRS scheduler wired to
the real repository layer against an in-memory DB.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.core.exceptions import CardNotFoundError
from app.models.enums import CardState, CEFRLevel, LearningGoal, ReviewRating, WordSource
from app.repositories.card_repository import CardRepository
from app.repositories.user_repository import UserRepository
from app.repositories.word_repository import WordRepository
from app.services.review_service import ReviewService


def _make_user_and_word(db_session, *, telegram_id: int = 1):
    user = UserRepository(db_session).create(
        telegram_id=telegram_id,
        username="learner",
        level=CEFRLevel.B1,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=10,
    )
    word = WordRepository(db_session).create(
        word="accurate", meaning="دقیق", source=WordSource.OXFORD_3000
    )
    return user, word


def test_get_or_create_card_is_idempotent(db_session):
    user, word = _make_user_and_word(db_session)
    service = ReviewService(db_session)

    card1 = service.get_or_create_card(user.id, word.id)
    card2 = service.get_or_create_card(user.id, word.id)

    assert card1.id == card2.id
    assert card1.state == CardState.NEW


def test_due_queue_only_returns_cards_due_now(db_session):
    user, word = _make_user_and_word(db_session)
    service = ReviewService(db_session)
    card = service.get_or_create_card(user.id, word.id)

    now = datetime.now(timezone.utc)
    assert len(service.get_due_queue(user.id, as_of=now)) == 1

    # Push it into the future - should no longer be due.
    CardRepository(db_session).update_after_review(
        card,
        stability=5.0,
        difficulty=5.0,
        due_date=now + timedelta(days=3),
        state=CardState.REVIEW,
        reviewed_at=now,
    )
    assert service.get_due_queue(user.id, as_of=now) == []


def test_grade_card_updates_scheduling_logs_review_and_awards_xp(db_session):
    user, word = _make_user_and_word(db_session)
    service = ReviewService(db_session)
    card = service.get_or_create_card(user.id, word.id)

    result = service.grade_card(user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD)

    assert result.card.state == CardState.REVIEW
    assert result.card.repetitions == 1
    assert result.xp_awarded == 5
    assert result.streak == 1
    assert result.card.due_date > datetime.now(timezone.utc)

    from app.repositories.review_repository import ReviewRepository
    from app.repositories.progress_repository import ProgressRepository

    reviews = ReviewRepository(db_session).list_for_user(user.id)
    assert len(reviews) == 1
    assert reviews[0].rating == ReviewRating.GOOD

    progress = ProgressRepository(db_session).get(user.id)
    assert progress.xp == 5
    assert progress.streak == 1


def test_grade_card_unknown_card_raises(db_session):
    user, _word = _make_user_and_word(db_session)
    service = ReviewService(db_session)

    with pytest.raises(CardNotFoundError):
        service.grade_card(user_id=user.id, card_id=99999, rating=ReviewRating.GOOD)


def test_grade_card_rejects_another_users_card(db_session):
    owner, word = _make_user_and_word(db_session, telegram_id=1)
    intruder, _ = _make_user_and_word(db_session, telegram_id=2)
    service = ReviewService(db_session)

    card = service.get_or_create_card(owner.id, word.id)

    with pytest.raises(CardNotFoundError):
        service.grade_card(user_id=intruder.id, card_id=card.id, rating=ReviewRating.GOOD)


def test_streak_increments_once_per_day_and_resets_after_a_gap(db_session):
    user, word = _make_user_and_word(db_session)
    service = ReviewService(db_session)
    card = service.get_or_create_card(user.id, word.id)

    day1 = datetime(2026, 1, 1, 9, tzinfo=timezone.utc)
    result1 = service.grade_card(
        user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD, now=day1
    )
    assert result1.streak == 1

    # Second review same day - streak should not double-increment.
    result_same_day = service.grade_card(
        user_id=user.id,
        card_id=card.id,
        rating=ReviewRating.GOOD,
        now=day1 + timedelta(hours=2),
    )
    assert result_same_day.streak == 1

    # Reviewed again the very next day - streak advances.
    day2 = day1 + timedelta(days=1)
    result2 = service.grade_card(
        user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD, now=day2
    )
    assert result2.streak == 2

    # A gap of several days resets the streak back to 1.
    day10 = day1 + timedelta(days=10)
    result3 = service.grade_card(
        user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD, now=day10
    )
    assert result3.streak == 1
