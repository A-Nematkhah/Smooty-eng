"""Progress model - one denormalized rollup row per user.

Kept denormalized (rather than always computing from `reviews`) so
the 📊 Progress dashboard is a single indexed row read, not an
aggregate query over the full review history every time the user
taps the menu.

Streak rule (per Phase 1 decision): if a user misses a full day
without meeting `daily_goal`, `streak` resets to 0 - no freeze/grace
mechanic. `progress_service` is responsible for detecting a gap via
`last_active_date` and resetting the streak before incrementing it.
"""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

if TYPE_CHECKING:
    from app.models.user import User


class Progress(Base):
    """Denormalized progress/XP/streak rollup for one user."""

    __tablename__ = "progress"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    total_words: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    learned_words: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    streak: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    xp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_active_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # --- relationships ---
    user: Mapped["User"] = relationship(back_populates="progress")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Progress user_id={self.user_id} streak={self.streak} xp={self.xp}>"
