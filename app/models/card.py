"""Card model - the FSRS scheduling state for one (user, word) pair.

This is what the FSRS scheduler (`app/fsrs/`) reads and writes on
every review. `reviews` (see review.py) is the append-only history
that produced this state; `cards` is the current/derived state,
kept denormalized for fast "what's due today" queries.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, sa_enum
from app.models.enums import CardState

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.word import Word


class Card(Base):
    """FSRS scheduling state for a single user/word pair."""

    __tablename__ = "cards"
    __table_args__ = (UniqueConstraint("user_id", "word_id", name="uq_card_user_word"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False)

    stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    due_date: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    last_review: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    repetitions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    state: Mapped[CardState] = mapped_column(sa_enum(CardState), nullable=False, default=CardState.NEW)
    is_favorite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    # --- relationships ---
    user: Mapped["User"] = relationship(back_populates="cards")
    word: Mapped["Word"] = relationship(back_populates="cards")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Card user_id={self.user_id} word_id={self.word_id} state={self.state} due={self.due_date}>"
