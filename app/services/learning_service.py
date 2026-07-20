"""Vocabulary/learning business logic (Phase 5).

Three responsibilities live here, all backed by the shared `words`
table (Oxford 3000 + IELTS + user-added custom words):

1. Picking a batch of *new* words for 📚 Learn English and enrolling
   them into FSRS via `CardRepository` once the user has seen them.
2. `/addword` - adding a personal custom word and immediately
   enrolling it (a custom word is only ever added because the user
   wants to learn it, so there's no separate "seen it, now add it"
   step like the Oxford/IELTS flow).
3. ⭐ My Vocabulary - favorites and "words giving you the most
   trouble" (highest FSRS difficulty among reviewed cards).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import CardNotFoundError, DuplicateEntityError
from app.models.card import Card
from app.models.enums import CardState, LearningGoal, LearningMode, WordSource
from app.models.user import User
from app.models.word import Word
from app.repositories.card_repository import CardRepository
from app.repositories.word_repository import WordRepository
from app.vocabulary.vocabulary_search import search_vocabulary


@dataclass(frozen=True)
class WordWithCard:
    """A word paired with its (possibly freshly-created) FSRS card."""

    word: Word
    card: Card


class LearningService:
    """Backs the 📚 Learn English and ⭐ My Vocabulary sections."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._words = WordRepository(session)
        self._cards = CardRepository(session)

    # --- 📚 Learn English --------------------------------------------------

    def get_new_words(
        self,
        user: User,
        limit: Optional[int] = None,
        *,
        source_override: Optional[WordSource] = None,
    ) -> list[Word]:
        """Next batch of words the user hasn't started learning yet.

        Prefers the word source that matches the user's current focus
        (IELTS if in IELTS-focus mode or that's their learning goal,
        Oxford 3000 otherwise) and their CEFR level, falling back in
        stages (drop the level filter, then drop the source filter)
        so a thin vocabulary table never returns an empty batch just
        because of an overly-specific match.

        `source_override` pins the source regardless of the user's
        normal preference - used by 🎓 IELTS Mode's own "learn" button,
        which always wants IELTS words even for a non-IELTS-focused user.
        """
        batch_size = limit or user.daily_goal
        preferred_source = source_override or self._preferred_source(user)

        words = self._words.list_unlearned(
            user.id, source=preferred_source, level=user.level, limit=batch_size
        )
        if len(words) < batch_size:
            more = self._words.list_unlearned(user.id, source=preferred_source, limit=batch_size)
            words = self._merge_unique(words, more, batch_size)
        if len(words) < batch_size:
            more = self._words.list_unlearned(user.id, limit=batch_size)
            words = self._merge_unique(words, more, batch_size)
        return words

    def enroll_word(self, user_id: int, word_id: int) -> Card:
        """Create (or fetch) the FSRS card for a word the user just
        learned - i.e. move it from "seen" into the review queue.
        """
        existing = self._cards.get(user_id, word_id)
        if existing is not None:
            return existing
        return self._cards.create(
            user_id=user_id,
            word_id=word_id,
            due_date=datetime.now(timezone.utc),
            state=CardState.NEW,
        )

    # --- /addword ------------------------------------------------------

    def add_custom_word(
        self, user: User, *, word: str, meaning: str, example: Optional[str] = None
    ) -> WordWithCard:
        """Add a personal word via `/addword` and enroll it right away."""
        word_text = word.strip()
        meaning_text = meaning.strip()
        if not word_text or not meaning_text:
            raise ValueError("word and meaning must not be blank")

        existing = self._words.get_by_text(word_text, source=WordSource.CUSTOM)
        if existing is not None:
            raise DuplicateEntityError(f"'{word_text}' is already in your custom vocabulary")

        new_word = self._words.create(
            word=word_text,
            meaning=meaning_text,
            example=example.strip() if example else None,
            source=WordSource.CUSTOM,
        )
        card = self.enroll_word(user.id, new_word.id)
        return WordWithCard(word=new_word, card=card)

    # --- /search, /find --------------------------------------------------

    def search(self, query: str, limit: int = 10) -> Sequence[Word]:
        return search_vocabulary(self._words, query, limit=limit)

    # --- ⭐ My Vocabulary --------------------------------------------------

    def toggle_favorite(self, user_id: int, card_id: int) -> Card:
        card = self._cards.get_by_id(card_id)
        if card is None or card.user_id != user_id:
            raise CardNotFoundError(f"card_id={card_id} not found for user_id={user_id}")
        return self._cards.set_favorite(card, not card.is_favorite)

    def list_favorites(self, user_id: int, limit: Optional[int] = None) -> list[WordWithCard]:
        cards = self._cards.list_favorites(user_id, limit=limit)
        return self._pair_with_words(cards)

    def list_difficult_words(self, user_id: int, limit: int = 10) -> list[WordWithCard]:
        cards = self._cards.list_most_difficult(user_id, limit=limit)
        return self._pair_with_words(cards)

    # --- internals -------------------------------------------------------

    def _pair_with_words(self, cards: Sequence[Card]) -> list[WordWithCard]:
        pairs = []
        for card in cards:
            word = self._words.get_by_id(card.word_id)
            if word is not None:  # pragma: no branch - FK guarantees this in practice
                pairs.append(WordWithCard(word=word, card=card))
        return pairs

    @staticmethod
    def _preferred_source(user: User) -> Optional[WordSource]:
        if user.learning_mode == LearningMode.IELTS_FOCUS:
            return WordSource.IELTS
        if user.learning_goal == LearningGoal.IELTS:
            return WordSource.IELTS
        return WordSource.OXFORD_3000

    @staticmethod
    def _merge_unique(base: list[Word], extra: Sequence[Word], limit: int) -> list[Word]:
        seen_ids = {word.id for word in base}
        merged = list(base)
        for word in extra:
            if len(merged) >= limit:
                break
            if word.id not in seen_ids:
                merged.append(word)
                seen_ids.add(word.id)
        return merged
