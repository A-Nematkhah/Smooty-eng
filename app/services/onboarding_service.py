"""Onboarding business logic.

Handlers call this instead of touching `UserRepository` or
`ProgressRepository` directly, so the "what happens when a new user
finishes onboarding" rule (create user + create their progress row)
lives in exactly one place.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models.enums import CEFRLevel, LearningGoal
from app.models.user import User
from app.repositories.progress_repository import ProgressRepository
from app.repositories.user_repository import UserRepository


@dataclass(frozen=True)
class OnboardingSelections:
    """Collected answers from the /start conversation, before the user is saved."""

    level: CEFRLevel
    learning_goal: LearningGoal
    daily_goal: int


class OnboardingService:
    """Coordinates user creation for the onboarding conversation."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._users = UserRepository(session)
        self._progress = ProgressRepository(session)

    def get_existing_user(self, telegram_id: int) -> Optional[User]:
        """Used by /start to decide: show onboarding, or go straight to the main menu."""
        return self._users.get_by_telegram_id(telegram_id)

    def complete_onboarding(
        self,
        *,
        telegram_id: int,
        username: Optional[str],
        selections: OnboardingSelections,
    ) -> User:
        """Create the user record and their initial (zeroed) progress row.

        `reminder_time` is seeded from `Settings.default_reminder_time`
        rather than left null, so the reminder system (app/scheduler/)
        works immediately without a required trip to ⚙ Settings first.
        """
        user = self._users.create(
            telegram_id=telegram_id,
            username=username,
            level=selections.level,
            learning_goal=selections.learning_goal,
            daily_goal=selections.daily_goal,
            reminder_time=get_settings().default_reminder_time,
        )
        self._progress.get_or_create(user.id)
        return user
