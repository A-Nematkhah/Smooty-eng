"""📊 Progress dashboard business logic.

This section was still a placeholder when Phases 4-7 finished (the
`progress` table and its repository existed since Phase 2, and
`ReviewService` already bumps XP/streak on every review, but nothing
had assembled those numbers into the dashboard the spec describes).
This service is that missing assembly layer - it doesn't own any new
state, it just reads what `ReviewService.grade_card` already wrote.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.enums import CardState, WordSource
from app.models.user import User
from app.repositories.card_repository import CardRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.word_repository import WordRepository


@dataclass(frozen=True)
class ProgressDashboard:
    """Everything the 📊 Progress screen needs to render itself."""

    total_words: int
    learned_words: int
    reviewed_today: int
    daily_goal: int
    streak: int
    accuracy: float  # 0.0-1.0, fraction of Good/Easy ratings
    xp: int


class ProgressService:
    """Backs the 📊 Progress dashboard."""

    def __init__(self, session: Session) -> None:
        self._progress = ProgressRepository(session)
        self._reviews = ReviewRepository(session)
        self._cards = CardRepository(session)
        self._words = WordRepository(session)

    def dashboard(self, user: User, *, now: datetime | None = None) -> ProgressDashboard:
        now = now or datetime.now(timezone.utc)
        progress = self._progress.get_or_create(user.id)

        total_words = (
            self._words.count_by_source(WordSource.OXFORD_3000)
            + self._words.count_by_source(WordSource.IELTS)
            + self._words.count_by_source(WordSource.CUSTOM)
        )
        learned_words = self._cards.count_by_state(user.id, CardState.REVIEW)

        day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        day_end = day_start + timedelta(days=1)
        reviewed_today = self._reviews.count_for_day(user.id, day_start, day_end)

        accuracy = self._reviews.accuracy_for_user(user.id)

        return ProgressDashboard(
            total_words=total_words,
            learned_words=learned_words,
            reviewed_today=reviewed_today,
            daily_goal=user.daily_goal,
            streak=progress.streak,
            accuracy=accuracy,
            xp=progress.xp,
        )
