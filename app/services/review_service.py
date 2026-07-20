"""Review session business logic (Phase 4).

Handlers call this instead of touching `CardRepository`/`ReviewRepository`
directly, so the rule "one review = update card scheduling state +
append to review history + bump today's progress/XP/streak" lives in
exactly one place. The FSRS math itself lives in `app/fsrs/` and is
intentionally kept out of this file - this class is just the
orchestration/persistence layer around it.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Optional, Sequence

from sqlalchemy.orm import Session

from app.core.exceptions import CardNotFoundError, WordNotFoundError
from app.fsrs.scheduler import CardSnapshot, FSRSScheduler, default_scheduler
from app.models.card import Card
from app.models.enums import CardState, ReviewRating, WordSource
from app.models.word import Word
from app.repositories.card_repository import CardRepository
from app.repositories.progress_repository import ProgressRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.word_repository import WordRepository

# XP awarded per review, by rating - rewards honest "Again" taps too
# (a little), so users aren't incentivized to inflate ratings just to
# see a bigger number.
_XP_BY_RATING = {
    ReviewRating.AGAIN: 1,
    ReviewRating.HARD: 3,
    ReviewRating.GOOD: 5,
    ReviewRating.EASY: 8,
}


@dataclass(frozen=True)
class DueCard:
    """One card + its word, ready to be shown in a review session."""

    card: Card
    word: Word


@dataclass(frozen=True)
class ReviewResult:
    """What changed after grading one card - handed back to the bot handler."""

    card: Card
    interval_days: float
    xp_awarded: int
    streak: int


class ReviewService:
    """Coordinates the 🔄 Review Words flow: due-card queue + grading."""

    def __init__(self, session: Session, scheduler: FSRSScheduler = default_scheduler) -> None:
        self._session = session
        self._scheduler = scheduler
        self._cards = CardRepository(session)
        self._reviews = ReviewRepository(session)
        self._words = WordRepository(session)
        self._progress = ProgressRepository(session)

    def get_due_queue(
        self,
        user_id: int,
        *,
        limit: Optional[int] = None,
        as_of: Optional[datetime] = None,
        source: Optional[WordSource] = None,
    ) -> list[DueCard]:
        """Cards due for review right now, each paired with its word.

        `source` restricts the queue to one word source (e.g.
        `WordSource.IELTS`) - used by 🎓 IELTS Mode's own review queue,
        which is separate from the general 🔄 Review Words queue.
        """
        as_of = as_of or datetime.now(timezone.utc)
        if source is not None:
            due_cards = self._cards.list_due_by_source(user_id, source, as_of=as_of, limit=limit)
        else:
            due_cards = self._cards.list_due(user_id, as_of=as_of, limit=limit)
        return [self._with_word(card) for card in due_cards]

    def count_due(
        self,
        user_id: int,
        *,
        as_of: Optional[datetime] = None,
        source: Optional[WordSource] = None,
    ) -> int:
        as_of = as_of or datetime.now(timezone.utc)
        if source is not None:
            return len(self._cards.list_due_by_source(user_id, source, as_of=as_of))
        return len(self._cards.list_due(user_id, as_of=as_of))

    def get_or_create_card(self, user_id: int, word_id: int) -> Card:
        """Used by Learn/Daily Lesson (Phases 5-6) to enroll a new word into FSRS."""
        card = self._cards.get(user_id, word_id)
        if card is not None:
            return card
        return self._cards.create(
            user_id=user_id,
            word_id=word_id,
            due_date=datetime.now(timezone.utc),
            state=CardState.NEW,
        )

    def grade_card(
        self,
        *,
        user_id: int,
        card_id: int,
        rating: ReviewRating,
        now: Optional[datetime] = None,
    ) -> ReviewResult:
        """Apply one rating: run FSRS, persist the new card state, log the
        review, and update the user's daily progress/streak/XP.
        """
        now = now or datetime.now(timezone.utc)

        card = self._cards.get_by_id(card_id)
        if card is None or card.user_id != user_id:
            raise CardNotFoundError(f"card_id={card_id} not found for user_id={user_id}")

        snapshot = CardSnapshot(
            stability=card.stability,
            difficulty=card.difficulty,
            state=card.state,
            repetitions=card.repetitions,
            last_review=card.last_review,
        )
        outcome = self._scheduler.review_card(snapshot, rating, now=now)

        updated_card = self._cards.update_after_review(
            card,
            stability=outcome.stability,
            difficulty=outcome.difficulty,
            due_date=outcome.due_date,
            state=outcome.state,
            reviewed_at=now,
        )

        self._reviews.create(user_id=user_id, word_id=card.word_id, rating=rating)

        streak = self._bump_progress_after_review(user_id, rating=rating, today=now.date())

        return ReviewResult(
            card=updated_card,
            interval_days=outcome.interval_days,
            xp_awarded=_XP_BY_RATING[rating],
            streak=streak,
        )

    # --- internals -------------------------------------------------------

    def _with_word(self, card: Card) -> DueCard:
        word = self._words.get_by_id(card.word_id)
        if word is None:  # pragma: no cover - defensive, FK guarantees this in practice
            raise WordNotFoundError(f"word_id={card.word_id} referenced by card_id={card.id} is missing")
        return DueCard(card=card, word=word)

    def _bump_progress_after_review(
        self, user_id: int, *, rating: ReviewRating, today: date
    ) -> int:
        """Award XP for this review and advance the daily streak once per day.

        Streak rule (per `Progress` model docstring): increment at most
        once per calendar day, on the first review of that day; reset
        to 1 instead of incrementing if a day was missed entirely.
        """
        progress = self._progress.get_or_create(user_id)
        new_xp = progress.xp + _XP_BY_RATING[rating]

        if progress.last_active_date == today:
            streak = progress.streak
        elif progress.last_active_date is not None and (today - progress.last_active_date).days == 1:
            streak = progress.streak + 1
        else:
            streak = 1

        learned_words = progress.learned_words
        if rating in (ReviewRating.GOOD, ReviewRating.EASY):
            # A rough "learned" signal: count distinct REVIEW-state cards
            # rather than every Good/Easy tap, recomputed cheaply here.
            learned_words = self._cards.count_by_state(user_id, CardState.REVIEW)

        self._progress.update(
            progress,
            xp=new_xp,
            streak=streak,
            learned_words=learned_words,
            last_active_date=today,
        )
        return streak
