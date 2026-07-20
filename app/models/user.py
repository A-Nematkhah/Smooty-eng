"""User model - one row per Telegram user."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import BigInteger, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, sa_enum
from app.models.enums import CEFRLevel, LearningGoal, LearningMode

if TYPE_CHECKING:
    from app.models.card import Card
    from app.models.progress import Progress
    from app.models.review import Review


class User(Base):
    """A single learner. Onboarding writes level/goal/daily_goal here.

    `reminder_time` and `learning_mode` also live directly on this
    table rather than a separate `user_settings` table - this is a
    personal tool with a strict 1:1 user-to-settings relationship,
    so a separate table would only add a join for no benefit.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, index=True, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    level: Mapped[CEFRLevel] = mapped_column(sa_enum(CEFRLevel), nullable=False)
    learning_goal: Mapped[LearningGoal] = mapped_column(sa_enum(LearningGoal), nullable=False)
    daily_goal: Mapped[int] = mapped_column(Integer, nullable=False, default=10)

    reminder_time: Mapped[Optional[str]] = mapped_column(
        String(5), nullable=True, comment="HH:MM, 24h local time"
    )
    learning_mode: Mapped[LearningMode] = mapped_column(
        sa_enum(LearningMode), nullable=False, default=LearningMode.STANDARD
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    # --- relationships ---
    cards: Mapped[List["Card"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    reviews: Mapped[List["Review"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    progress: Mapped[Optional["Progress"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:  # pragma: no cover - debug convenience only
        return f"<User id={self.id} telegram_id={self.telegram_id} level={self.level}>"
