"""Repository for the `words` table."""

from __future__ import annotations

from typing import Optional, Sequence

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.enums import CEFRLevel, WordSource
from app.models.word import Word


class WordRepository:
    """Read/write access to the shared vocabulary table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def get_by_id(self, word_id: int) -> Optional[Word]:
        return self._session.get(Word, word_id)

    def get_by_text(self, word_text: str, source: Optional[WordSource] = None) -> Optional[Word]:
        stmt = select(Word).where(Word.word.ilike(word_text))
        if source is not None:
            stmt = stmt.where(Word.source == source)
        return self._session.execute(stmt).scalars().first()

    def search(self, query: str, limit: int = 20) -> Sequence[Word]:
        """Case-insensitive search across word text and meaning.

        Powers the /search and /find commands.
        """
        like_pattern = f"%{query}%"
        stmt = (
            select(Word)
            .where(or_(Word.word.ilike(like_pattern), Word.meaning.ilike(like_pattern)))
            .order_by(Word.word)
            .limit(limit)
        )
        return self._session.execute(stmt).scalars().all()

    def list_by_source(
        self,
        source: WordSource,
        level: Optional[CEFRLevel] = None,
        category: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> Sequence[Word]:
        stmt = select(Word).where(Word.source == source)
        if level is not None:
            stmt = stmt.where(Word.level == level)
        if category is not None:
            stmt = stmt.where(Word.category == category)
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()

    def create(self, **fields) -> Word:
        word = Word(**fields)
        self._session.add(word)
        self._session.flush()
        return word

    def bulk_create(self, words: list[dict]) -> list[Word]:
        """Used by the vocabulary seed script for fast initial import."""
        objects = [Word(**data) for data in words]
        self._session.add_all(objects)
        self._session.flush()
        return objects

    def count_by_source(self, source: WordSource) -> int:
        stmt = select(Word).where(Word.source == source)
        return len(self._session.execute(stmt).scalars().all())

    def list_unlearned(
        self,
        user_id: int,
        *,
        source: Optional[WordSource] = None,
        level: Optional[CEFRLevel] = None,
        limit: Optional[int] = None,
    ) -> Sequence[Word]:
        """Words that don't have a `Card` yet for this user - the pool
        📚 Learn English draws new words from.

        Imports `Card` locally (rather than at module level) to keep
        this the one place `WordRepository` needs to know cards exist,
        without creating a module-level import cycle with `card.py`.
        """
        from app.models.card import Card

        already_learning = select(Card.word_id).where(Card.user_id == user_id)
        stmt = select(Word).where(~Word.id.in_(already_learning))
        if source is not None:
            stmt = stmt.where(Word.source == source)
        if level is not None:
            stmt = stmt.where(Word.level == level)
        stmt = stmt.order_by(Word.id)
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()

    def list_random_excluding(
        self, exclude_ids: Sequence[int], limit: int, level: Optional[CEFRLevel] = None
    ) -> Sequence[Word]:
        """Random words, excluding a given set - used to build multiple-choice
        quiz distractors that aren't the question's own correct answer.
        """
        stmt = select(Word)
        if exclude_ids:
            stmt = stmt.where(~Word.id.in_(exclude_ids))
        if level is not None:
            stmt = stmt.where(Word.level == level)
        stmt = stmt.order_by(func.random()).limit(limit)
        return self._session.execute(stmt).scalars().all()

    def list_ielts_topics(self) -> list[str]:
        """Distinct, non-null IELTS topics currently in the vocabulary
        table - powers the 🎓 IELTS Mode "browse by topic" menu.
        """
        stmt = (
            select(Word.ielts_topic)
            .where(Word.source == WordSource.IELTS, Word.ielts_topic.is_not(None))
            .distinct()
            .order_by(Word.ielts_topic)
        )
        return [topic for (topic,) in self._session.execute(stmt).all()]

    def list_by_ielts_topic(self, topic: str, limit: Optional[int] = None) -> Sequence[Word]:
        stmt = (
            select(Word)
            .where(Word.source == WordSource.IELTS, Word.ielts_topic == topic)
            .order_by(Word.word)
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        return self._session.execute(stmt).scalars().all()
