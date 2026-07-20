"""Review model - append-only log of every rating a user has given.

Never updated or deleted in normal operation. This is the source
of truth for accuracy statistics and can be replayed to rebuild
`cards` state if the FSRS algorithm parameters ever change.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, sa_enum
from app.models.enums import ReviewRating

if TYPE_CHECKING:
    from app.models.user import User


class Review(Base):
    """A single review event: user rated one word at one point in time."""

    __tablename__ = "reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    word_id: Mapped[int] = mapped_column(ForeignKey("words.id", ondelete="CASCADE"), nullable=False)

    rating: Mapped[ReviewRating] = mapped_column(sa_enum(ReviewRating), nullable=False)
    review_date: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True
    )

    # --- relationships ---
    user: Mapped["User"] = relationship(back_populates="reviews")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Review user_id={self.user_id} word_id={self.word_id} rating={self.rating}>"
