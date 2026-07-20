"""Settings business logic.

One method per editable setting, each validating its input before
writing through `UserRepository.update`. Keeping validation here
(not in the handler) means Phase 3's Settings menu and any future
surface (e.g. a future admin script) share the same rules.
"""

from __future__ import annotations

import re

from sqlalchemy.orm import Session

from app.core.exceptions import ValidationError
from app.models.enums import CEFRLevel, LearningGoal, LearningMode
from app.models.user import User
from app.repositories.user_repository import UserRepository

_TIME_PATTERN = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class SettingsService:
    """Reads and updates a user's editable preferences."""

    def __init__(self, session: Session) -> None:
        self._users = UserRepository(session)

    def update_level(self, user: User, level: CEFRLevel) -> User:
        return self._users.update(user, level=level)

    def update_learning_goal(self, user: User, learning_goal: LearningGoal) -> User:
        return self._users.update(user, learning_goal=learning_goal)

    def update_daily_goal(self, user: User, daily_goal: int) -> User:
        if daily_goal <= 0:
            raise ValidationError("daily_goal must be a positive number of words")
        return self._users.update(user, daily_goal=daily_goal)

    def update_reminder_time(self, user: User, reminder_time: str) -> User:
        if not _TIME_PATTERN.match(reminder_time):
            raise ValidationError(f"'{reminder_time}' is not a valid HH:MM 24h time")
        return self._users.update(user, reminder_time=reminder_time)

    def update_learning_mode(self, user: User, learning_mode: LearningMode) -> User:
        return self._users.update(user, learning_mode=learning_mode)
