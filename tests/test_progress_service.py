"""Tests for `ProgressService` - the dashboard that was still a
placeholder in the uploaded project despite Phases 4-7 being done.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.models.enums import CEFRLevel, LearningGoal, ReviewRating, WordSource
from app.repositories.card_repository import CardRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.word_repository import WordRepository
from app.services.onboarding_service import OnboardingSelections, OnboardingService
from app.services.progress_service import ProgressService


def _make_user(db_session, telegram_id: int = 1):
    onboarding = OnboardingService(db_session)
    return onboarding.complete_onboarding(
        telegram_id=telegram_id,
        username=None,
        selections=OnboardingSelections(
            level=CEFRLevel.B1, learning_goal=LearningGoal.GENERAL, daily_goal=10
        ),
    )


def test_dashboard_reflects_words_reviews_and_progress(db_session):
    user = _make_user(db_session)
    words = WordRepository(db_session)
    cards = CardRepository(db_session)
    reviews = ReviewRepository(db_session)

    word_a = words.create(word="abandon", meaning="x", source=WordSource.OXFORD_3000)
    word_b = words.create(word="maintain", meaning="y", source=WordSource.OXFORD_3000)

    now = datetime.now(timezone.utc)
    card_a = cards.create(user_id=user.id, word_id=word_a.id, due_date=now)
    cards.create(user_id=user.id, word_id=word_b.id, due_date=now)

    from app.models.enums import CardState

    cards.update_after_review(
        card_a,
        stability=2.0,
        difficulty=5.0,
        due_date=now,
        state=CardState.REVIEW,
        reviewed_at=now,
    )
    reviews.create(user_id=user.id, word_id=word_a.id, rating=ReviewRating.GOOD)
    reviews.create(user_id=user.id, word_id=word_a.id, rating=ReviewRating.AGAIN)

    dashboard = ProgressService(db_session).dashboard(user, now=now)

    assert dashboard.total_words == 2
    assert dashboard.learned_words == 1  # only card_a reached REVIEW state
    assert dashboard.reviewed_today == 2
    assert dashboard.daily_goal == 10
    assert dashboard.accuracy == 0.5  # 1 of 2 ratings was Good/Easy


def test_dashboard_handles_brand_new_user_with_no_activity(db_session):
    user = _make_user(db_session, telegram_id=2)

    dashboard = ProgressService(db_session).dashboard(user)

    assert dashboard.total_words == 0
    assert dashboard.learned_words == 0
    assert dashboard.reviewed_today == 0
    assert dashboard.streak == 0
    assert dashboard.accuracy == 0.0
    assert dashboard.xp == 0
