"""Repository for the `cards` table (FSRS scheduling state)."""

from __future__ import annotations

from datetime import datetime
from typing import Optional, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.card import Card
from app.models.enums import CardState, WordSource


class CardRepository:
    """Read/write access to per-user FSRS card state."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get(self, user_id: int, word_id: int) -> Optional[Card]:
        stmt = select(Card).where(Card.user_id == user_id, Card.word_id == word_id)
        return self._session.execute(stmt).scalar_one_or_none()

    def get_by_id(self, card_id: int) -> Optional[Card]:
        return self._session.get(Card, card_id)

    def create(
        self,
        *,
        user_id: int,
        word_id: int,
        stability: float = 0.0,
        difficulty: float = 0.0,
        due_date: datetime,
        state: CardState = CardState.NEW,
    ) -> Card:
        card = Card(
            user_id=user_id,
            word_id=word_id,
            stability=stability,
            difficulty=difficulty,
            due_date=due_date,
            state=state,
        )
        self._session.add(card)
        self._session.flush()
        return card

    def list_due(self, user_id: int, as_of: datetime, limit: Optional[int] = None) -> Sequence[Card]:
        """Cards whose due_date has passed - the "Review Words" queue."""
        stmt = (
            select(Card)
            .where(Card.user_id == user_id, Card.due_date <= as_of)
            .order_by(Card.due_date)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()

    def list_due_by_source(
        self, user_id: int, source: WordSource, as_of: datetime, limit: Optional[int] = None
    ) -> Sequence[Card]:
        """Same as `list_due`, restricted to words from one source - powers
        🎓 IELTS Mode's own review queue, separate from the general one.
        """
        from app.models.word import Word

        stmt = (
            select(Card)
            .join(Word, Word.id == Card.word_id)
            .where(Card.user_id == user_id, Card.due_date <= as_of, Word.source == source)
            .order_by(Card.due_date)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()

    def count_by_source(
        self, user_id: int, source: WordSource, state: Optional[CardState] = None
    ) -> int:
        from app.models.word import Word

        stmt = (
            select(Card)
            .join(Word, Word.id == Card.word_id)
            .where(Card.user_id == user_id, Word.source == source)
        )
        if state is not None:
            stmt = stmt.where(Card.state == state)
        return len(self._session.execute(stmt).scalars().all())

    def list_new(self, user_id: int, limit: int) -> Sequence[Card]:
        """Cards never reviewed yet - used to compose new-word batches."""
        stmt = (
            select(Card)
            .where(Card.user_id == user_id, Card.state == CardState.NEW)
            .order_by(Card.id)
            .limit(limit)
        )
        return self._session.execute(stmt).scalars().all()

    def list_by_state_sample(self, user_id: int, state: CardState, limit: int) -> Sequence[Card]:
        """Random sample of a user's cards in a given state - used to pick
        quiz candidates without always quizzing the same first N words.
        """
        stmt = (
            select(Card)
            .where(Card.user_id == user_id, Card.state == state)
            .order_by(func.random())
            .limit(limit)
        )
        return self._session.execute(stmt).scalars().all()

    def count_by_state(self, user_id: int, state: CardState) -> int:
        stmt = select(Card).where(Card.user_id == user_id, Card.state == state)
        return len(self._session.execute(stmt).scalars().all())

    def set_favorite(self, card: Card, is_favorite: bool) -> Card:
        card.is_favorite = is_favorite
        self._session.flush()
        return card

    def list_favorites(self, user_id: int, limit: Optional[int] = None) -> Sequence[Card]:
        stmt = (
            select(Card)
            .where(Card.user_id == user_id, Card.is_favorite.is_(True))
            .order_by(Card.id)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()

    def list_most_difficult(self, user_id: int, limit: int = 10) -> Sequence[Card]:
        """Cards that have been reviewed at least once, hardest first.

        Powers the "difficult words" list in ⭐ My Vocabulary - a quick
        way to see what's actually giving the user trouble, distinct
        from the raw due-for-review queue.
        """
        stmt = (
            select(Card)
            .where(Card.user_id == user_id, Card.repetitions > 0)
            .order_by(Card.difficulty.desc())
            .limit(limit)
        )
        return self._session.execute(stmt).scalars().all()

    def update_after_review(
        self,
        card: Card,
        *,
        stability: float,
        difficulty: float,
        due_date: datetime,
        state: CardState,
        reviewed_at: datetime,
    ) -> Card:
        """Persist the FSRS scheduler's output for one review event."""
        card.stability = stability
        card.difficulty = difficulty
        card.due_date = due_date
        card.state = state
        card.last_review = reviewed_at
        card.repetitions += 1
        self._session.flush()
        return card
