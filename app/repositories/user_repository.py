"""Repository for the `users` table.

Repositories are the *only* place raw SQLAlchemy queries are
written. Services depend on this class, never on `Session` or
`User` model queries directly - that boundary is what makes
services unit-testable with a fake/mock repository.
"""

from __future__ import annotations

from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import CEFRLevel, LearningGoal, LearningMode
from app.models.user import User


class UserRepository:
    """CRUD operations for `User`."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, user_id: int) -> Optional[User]:
        return self._session.get(User, user_id)

    def get_by_telegram_id(self, telegram_id: int) -> Optional[User]:
        stmt = select(User).where(User.telegram_id == telegram_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def create(
        self,
        *,
        telegram_id: int,
        username: Optional[str],
        level: CEFRLevel,
        learning_goal: LearningGoal,
        daily_goal: int,
        reminder_time: Optional[str] = None,
        learning_mode: LearningMode = LearningMode.STANDARD,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            level=level,
            learning_goal=learning_goal,
            daily_goal=daily_goal,
            reminder_time=reminder_time,
            learning_mode=learning_mode,
        )
        self._session.add(user)
        self._session.flush()  # populate user.id without ending the transaction
        return user

    def update(self, user: User, **fields) -> User:
        """Update arbitrary allowed fields on an existing user.

        Example: `user_repository.update(user, daily_goal=20, reminder_time="08:30")`
        """
        for field, value in fields.items():
            if not hasattr(user, field):
                raise AttributeError(f"User has no field '{field}'")
            setattr(user, field, value)
        self._session.flush()
        return user

    def list_all(self) -> list[User]:
        """Mainly useful for the scheduler ("which users need a reminder now")."""
        return list(self._session.execute(select(User)).scalars().all())

    def delete(self, user: User) -> None:
        self._session.delete(user)
        self._session.flush()
