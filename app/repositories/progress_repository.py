"""Repository for the `progress` table (one denormalized row per user)."""

from __future__ import annotations

from datetime import date
from typing import Optional

from app.models.progress import Progress
from sqlalchemy.orm import Session


class ProgressRepository:
    """Read/write the per-user progress rollup."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int) -> Optional[Progress]:
        return self._session.get(Progress, user_id)

    def create(self, user_id: int) -> Progress:
        progress = Progress(user_id=user_id, total_words=0, learned_words=0, streak=0, xp=0)
        self._session.add(progress)
        self._session.flush()
        return progress

    def get_or_create(self, user_id: int) -> Progress:
        progress = self.get(user_id)
        if progress is None:
            progress = self.create(user_id)
        return progress

    def update(
        self,
        progress: Progress,
        *,
        total_words: Optional[int] = None,
        learned_words: Optional[int] = None,
        streak: Optional[int] = None,
        xp: Optional[int] = None,
        last_active_date: Optional[date] = None,
    ) -> Progress:
        if total_words is not None:
            progress.total_words = total_words
        if learned_words is not None:
            progress.learned_words = learned_words
        if streak is not None:
            progress.streak = streak
        if xp is not None:
            progress.xp = xp
        if last_active_date is not None:
            progress.last_active_date = last_active_date
        self._session.flush()
        return progress
