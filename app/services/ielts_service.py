"""🎓 IELTS Mode business logic (Phase 7).

IELTS words are just `Word` rows with `source=WordSource.IELTS` plus
their `ielts_band`/`ielts_topic` columns filled in (see the Phase 1
architecture note in `app/models/word.py`) - so this service is a
thin, source-scoped layer on top of `LearningService`/`ReviewService`
rather than a parallel vocabulary system. The one genuinely new
capability is topic browsing.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.models.enums import CardState, WordSource
from app.models.user import User
from app.models.word import Word
from app.repositories.card_repository import CardRepository
from app.repositories.word_repository import WordRepository
from app.services.learning_service import LearningService
from app.services.review_service import DueCard, ReviewService


@dataclass(frozen=True)
class IELTSStats:
    """Counts shown on the 🎓 IELTS Mode dashboard."""

    total_ielts_words: int
    enrolled: int
    learned: int
    due_for_review: int


class IELTSService:
    """Backs the 🎓 IELTS Mode dashboard, topic browser, and its
    dedicated learn/review entry points.
    """

    def __init__(self, session: Session) -> None:
        self._session = session
        self._words = WordRepository(session)
        self._cards = CardRepository(session)
        self._learning = LearningService(session)
        self._reviews = ReviewService(session)

    def stats(self, user: User) -> IELTSStats:
        return IELTSStats(
            total_ielts_words=self._words.count_by_source(WordSource.IELTS),
            enrolled=self._cards.count_by_source(user.id, WordSource.IELTS),
            learned=self._cards.count_by_source(user.id, WordSource.IELTS, state=CardState.REVIEW),
            due_for_review=self._reviews.count_due(user.id, source=WordSource.IELTS),
        )

    def list_topics(self) -> list[str]:
        return self._words.list_ielts_topics()

    def words_by_topic(self, topic: str, limit: int = 20) -> Sequence[Word]:
        return self._words.list_by_ielts_topic(topic, limit=limit)

    def get_new_words(self, user: User, limit: Optional[int] = None) -> list[Word]:
        """New IELTS words to learn, regardless of the user's normal
        learning-mode preference (tapping into 🎓 IELTS Mode always
        means "show me IELTS words").
        """
        return self._learning.get_new_words(user, limit=limit, source_override=WordSource.IELTS)

    def get_due_queue(self, user: User, *, limit: Optional[int] = None) -> list[DueCard]:
        return self._reviews.get_due_queue(user.id, limit=limit, source=WordSource.IELTS)
