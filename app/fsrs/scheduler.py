"""FSRS (Free Spaced Repetition Scheduler) core algorithm.

Deliberately framework-agnostic: this module knows nothing about
SQLAlchemy, Telegram, or sessions. It takes plain values in (current
stability/difficulty/state, a rating, "now") and returns plain values
out (new stability/difficulty/state/due_date). `app/services/review_service.py`
is the only place that talks to `CardRepository`/`ReviewRepository`
and feeds this module's output into the database.

Formulas follow the published FSRS v4/v5 algorithm (the same family
of formulas used by modern Anki's "FSRS" scheduler): difficulty/
stability are updated per review using the 19-weight parameter
vector, and the next interval is solved from the exponential-ish
forgetting curve so that predicted recall probability at the next
review equals the configured `request_retention`. Note: FSRS-5's
same-day/short-term-stability adjustment (weights w[17]/w[18]) is
not implemented - a reasonable simplification for a personal tool
that isn't optimized around multiple same-day reviews of one card.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import exp

from app.fsrs.parameters import (
    DEFAULT_MAXIMUM_INTERVAL,
    DEFAULT_REQUEST_RETENTION,
    DEFAULT_WEIGHTS,
    LEARNING_STEPS_MINUTES,
    MAX_DIFFICULTY,
    MIN_DIFFICULTY,
    MIN_STABILITY,
    RELEARNING_STEPS_MINUTES,
)
from app.models.enums import CardState, ReviewRating

_RATING_GRADE = {
    ReviewRating.AGAIN: 1,
    ReviewRating.HARD: 2,
    ReviewRating.GOOD: 3,
    ReviewRating.EASY: 4,
}


@dataclass(frozen=True)
class CardSnapshot:
    """The FSRS-relevant subset of a `Card` row, before this review."""

    stability: float
    difficulty: float
    state: CardState
    repetitions: int
    last_review: datetime | None


@dataclass(frozen=True)
class ReviewOutcome:
    """What the scheduler computed - ready to hand to `CardRepository.update_after_review`."""

    stability: float
    difficulty: float
    state: CardState
    due_date: datetime
    interval_days: float


def _clamp_difficulty(value: float) -> float:
    return max(MIN_DIFFICULTY, min(MAX_DIFFICULTY, value))


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


class FSRSScheduler:
    """Computes next stability/difficulty/due-date for one review event."""

    def __init__(
        self,
        weights: tuple[float, ...] = DEFAULT_WEIGHTS,
        request_retention: float = DEFAULT_REQUEST_RETENTION,
        maximum_interval: int = DEFAULT_MAXIMUM_INTERVAL,
    ) -> None:
        self._w = weights
        self._request_retention = request_retention
        self._maximum_interval = maximum_interval

    # --- public API -----------------------------------------------------

    def review_card(
        self,
        card: CardSnapshot,
        rating: ReviewRating,
        now: datetime | None = None,
    ) -> ReviewOutcome:
        """Apply one rating to a card and return its new scheduling state."""
        now = now or _now_utc()

        if card.repetitions == 0 or card.last_review is None:
            return self._review_new_card(rating, now)
        return self._review_existing_card(card, rating, now)

    def retrievability(self, elapsed_days: float, stability: float) -> float:
        """Predicted probability of recall, given how long it's been."""
        stability = max(stability, MIN_STABILITY)
        return (1 + elapsed_days / (9 * stability)) ** -1

    # --- internals --------------------------------------------------------

    def _review_new_card(self, rating: ReviewRating, now: datetime) -> ReviewOutcome:
        grade = _RATING_GRADE[rating]
        stability = max(self._w[grade - 1], MIN_STABILITY)
        difficulty = _clamp_difficulty(self._w[4] - (grade - 3) * self._w[5])

        if rating == ReviewRating.AGAIN:
            due = now + timedelta(minutes=LEARNING_STEPS_MINUTES[0])
            return ReviewOutcome(stability, difficulty, CardState.LEARNING, due, 0.0)

        interval_days = self._next_interval_days(stability)
        due = now + timedelta(days=interval_days)
        return ReviewOutcome(stability, difficulty, CardState.REVIEW, due, interval_days)

    def _review_existing_card(
        self, card: CardSnapshot, rating: ReviewRating, now: datetime
    ) -> ReviewOutcome:
        grade = _RATING_GRADE[rating]
        elapsed_days = max((now - card.last_review).total_seconds() / 86400.0, 0.0)
        retrievability = self.retrievability(elapsed_days, card.stability)

        new_difficulty = self._next_difficulty(card.difficulty, grade)

        if rating == ReviewRating.AGAIN:
            new_stability = self._next_forget_stability(
                new_difficulty, card.stability, retrievability
            )
            step_minutes = (
                RELEARNING_STEPS_MINUTES[0]
                if card.state in (CardState.REVIEW, CardState.RELEARNING)
                else LEARNING_STEPS_MINUTES[-1]
            )
            due = now + timedelta(minutes=step_minutes)
            next_state = (
                CardState.RELEARNING if card.state == CardState.REVIEW else CardState.LEARNING
            )
            return ReviewOutcome(new_stability, new_difficulty, next_state, due, 0.0)

        # Still in the (re)learning ladder and not yet graduated: a
        # non-Again rating on a LEARNING/RELEARNING card graduates it
        # straight to REVIEW with a fresh day-scale interval.
        new_stability = self._next_recall_stability(
            new_difficulty, card.stability, retrievability, grade
        )
        interval_days = self._next_interval_days(new_stability)
        due = now + timedelta(days=interval_days)
        return ReviewOutcome(new_stability, new_difficulty, CardState.REVIEW, due, interval_days)

    def _next_difficulty(self, difficulty: float, grade: int) -> float:
        initial_easy_difficulty = _clamp_difficulty(self._w[4] - (4 - 3) * self._w[5])
        shifted = difficulty - self._w[6] * (grade - 3)
        reverted = self._w[7] * initial_easy_difficulty + (1 - self._w[7]) * shifted
        return _clamp_difficulty(reverted)

    def _next_recall_stability(
        self, difficulty: float, stability: float, retrievability: float, grade: int
    ) -> float:
        hard_penalty = self._w[15] if grade == 2 else 1.0
        easy_bonus = self._w[16] if grade == 4 else 1.0
        growth = (
            exp(self._w[8])
            * (11 - difficulty)
            * (stability ** -self._w[9])
            * (exp((1 - retrievability) * self._w[10]) - 1)
            * hard_penalty
            * easy_bonus
        )
        return max(stability * (1 + growth), MIN_STABILITY)

    def _next_forget_stability(
        self, difficulty: float, stability: float, retrievability: float
    ) -> float:
        value = (
            self._w[11]
            * (difficulty ** -self._w[12])
            * (((stability + 1) ** self._w[13]) - 1)
            * exp((1 - retrievability) * self._w[14])
        )
        return max(min(value, stability), MIN_STABILITY)

    def _next_interval_days(self, stability: float) -> float:
        raw = 9 * stability * (1 / self._request_retention - 1)
        return max(1.0, min(raw, float(self._maximum_interval)))


# Module-level default instance - stateless aside from its (fixed)
# parameters, so sharing one instance across requests is safe and
# avoids re-allocating the weights tuple on every review.
default_scheduler = FSRSScheduler()
