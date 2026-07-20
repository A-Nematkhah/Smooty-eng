"""Repository for the append-only `reviews` table."""

from __future__ import annotations

from datetime import datetime
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.enums import ReviewRating
from app.models.review import Review


class ReviewRepository:
    """Write and query the review history log."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def create(self, *, user_id: int, word_id: int, rating: ReviewRating) -> Review:
        review = Review(user_id=user_id, word_id=word_id, rating=rating)
        self._session.add(review)
        self._session.flush()
        return review

    def list_for_user(
        self, user_id: int, since: datetime | None = None, limit: int | None = None
    ) -> Sequence[Review]:
        stmt = select(Review).where(Review.user_id == user_id).order_by(Review.review_date.desc())
        if since is not None:
            stmt = stmt.where(Review.review_date >= since)
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()

    def count_for_day(self, user_id: int, day_start: datetime, day_end: datetime) -> int:
        """Used by daily_lesson_service / progress_service to check today's goal."""
        stmt = select(func.count(Review.id)).where(
            Review.user_id == user_id,
            Review.review_date >= day_start,
            Review.review_date < day_end,
        )
        return self._session.execute(stmt).scalar_one()

    def accuracy_for_user(self, user_id: int, since: datetime | None = None) -> float:
        """Fraction of reviews rated Good/Easy (treated as "correct recall").

        Returns 0.0 if the user has no reviews yet, to keep the
        progress dashboard simple rather than needing None-handling
        everywhere it's displayed.
        """
        stmt = select(Review.rating).where(Review.user_id == user_id)
        if since is not None:
            stmt = stmt.where(Review.review_date >= since)
        ratings = self._session.execute(stmt).scalars().all()
        if not ratings:
            return 0.0
        correct = sum(1 for r in ratings if r in (ReviewRating.GOOD, ReviewRating.EASY))
        return correct / len(ratings)
