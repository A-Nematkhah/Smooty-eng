"""Reminder System business logic.

Per the master spec: a daily reminder ("Your English lesson is
ready") and a review reminder ("You have N words waiting"), fired
at each user's configured `reminder_time` (⚙ Settings already lets
them change this). This module is framework-agnostic - the actual
scheduling and message-sending lives in `app/scheduler/`, which
calls `users_due_now()` and `build_reminder_text()` from a Telegram
JobQueue callback.
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.card_repository import CardRepository
from app.repositories.user_repository import UserRepository


class ReminderService:
    """Finds users due for a reminder and composes their message."""

    def __init__(self, session: Session) -> None:
        self._users = UserRepository(session)
        self._cards = CardRepository(session)

    def users_due_now(self, current_time_hhmm: str) -> list[User]:
        """Users whose `reminder_time` matches the given HH:MM exactly.

        Called once per minute by the scheduler job, so an exact
        string match is enough to fire each user's reminder once a
        day without needing a separate "already sent today" flag -
        the job simply won't see that same HH:MM again until
        tomorrow.
        """
        return [
            user
            for user in self._users.list_all()
            if user.reminder_time == current_time_hhmm
        ]

    def build_reminder_text(self, user: User, *, now: datetime | None = None) -> str:
        now = now or datetime.now(timezone.utc)
        due_count = len(self._cards.list_due(user.id, as_of=now))

        if due_count > 0:
            return (
                "⏰ *Reminder*\n\n"
                f"You have *{due_count} word{'s' if due_count != 1 else ''}* waiting for review.\n"
                "Open 🔄 Review Words or 🎯 Daily Lesson whenever you're ready."
            )
        return (
            "⏰ *Reminder*\n\n"
            "Your English lesson is ready. Open 🎯 Daily Lesson to keep your streak going!"
        )
