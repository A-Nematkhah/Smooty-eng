"""Tests for the Phase 3 service layer.

These test `OnboardingService` and `SettingsService` directly
against the in-memory DB fixture - no Telegram objects involved,
since python-telegram-bot isn't testable in this sandbox (no
network to install it). Handler wiring itself should be smoke
tested manually against a real bot token before relying on it.
"""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.models.enums import CEFRLevel, LearningGoal, LearningMode
from app.services.onboarding_service import OnboardingSelections, OnboardingService
from app.services.settings_service import SettingsService


def test_onboarding_creates_user_and_progress_row(db_session):
    service = OnboardingService(db_session)

    assert service.get_existing_user(555) is None

    user = service.complete_onboarding(
        telegram_id=555,
        username="learner1",
        selections=OnboardingSelections(
            level=CEFRLevel.B1, learning_goal=LearningGoal.IELTS, daily_goal=10
        ),
    )

    assert service.get_existing_user(555) is user
    assert user.level == CEFRLevel.B1
    assert user.learning_goal == LearningGoal.IELTS
    assert user.daily_goal == 10

    from app.repositories.progress_repository import ProgressRepository

    progress = ProgressRepository(db_session).get(user.id)
    assert progress is not None
    assert progress.xp == 0


def test_settings_service_updates_valid_fields(db_session):
    onboarding = OnboardingService(db_session)
    user = onboarding.complete_onboarding(
        telegram_id=1,
        username=None,
        selections=OnboardingSelections(
            level=CEFRLevel.A1, learning_goal=LearningGoal.GENERAL, daily_goal=5
        ),
    )

    settings = SettingsService(db_session)
    settings.update_level(user, CEFRLevel.B2)
    settings.update_daily_goal(user, 20)
    settings.update_reminder_time(user, "08:30")
    settings.update_learning_mode(user, LearningMode.IELTS_FOCUS)

    assert user.level == CEFRLevel.B2
    assert user.daily_goal == 20
    assert user.reminder_time == "08:30"
    assert user.learning_mode == LearningMode.IELTS_FOCUS


def test_settings_service_rejects_invalid_daily_goal(db_session):
    onboarding = OnboardingService(db_session)
    user = onboarding.complete_onboarding(
        telegram_id=2,
        username=None,
        selections=OnboardingSelections(
            level=CEFRLevel.A1, learning_goal=LearningGoal.GENERAL, daily_goal=5
        ),
    )

    settings = SettingsService(db_session)
    with pytest.raises(ValidationError):
        settings.update_daily_goal(user, 0)


def test_settings_service_rejects_invalid_reminder_time(db_session):
    onboarding = OnboardingService(db_session)
    user = onboarding.complete_onboarding(
        telegram_id=3,
        username=None,
        selections=OnboardingSelections(
            level=CEFRLevel.A1, learning_goal=LearningGoal.GENERAL, daily_goal=5
        ),
    )

    settings = SettingsService(db_session)
    with pytest.raises(ValidationError):
        settings.update_reminder_time(user, "25:99")
    with pytest.raises(ValidationError):
        settings.update_reminder_time(user, "9:30")  # must be zero-padded HH:MM
