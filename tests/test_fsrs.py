"""Tests for `app/fsrs/scheduler.py` - pure math, no database involved."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from app.fsrs.scheduler import CardSnapshot, FSRSScheduler
from app.models.enums import CardState, ReviewRating

NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _new_card() -> CardSnapshot:
    return CardSnapshot(
        stability=0.0, difficulty=0.0, state=CardState.NEW, repetitions=0, last_review=None
    )


@pytest.mark.parametrize(
    "rating", [ReviewRating.HARD, ReviewRating.GOOD, ReviewRating.EASY]
)
def test_first_review_non_again_graduates_to_review_state(rating):
    scheduler = FSRSScheduler()
    outcome = scheduler.review_card(_new_card(), rating, now=NOW)

    assert outcome.state == CardState.REVIEW
    assert outcome.stability > 0
    assert 1.0 <= outcome.difficulty <= 10.0
    assert outcome.due_date > NOW
    assert outcome.interval_days >= 1.0


def test_first_review_again_stays_in_learning_with_short_delay():
    scheduler = FSRSScheduler()
    outcome = scheduler.review_card(_new_card(), ReviewRating.AGAIN, now=NOW)

    assert outcome.state == CardState.LEARNING
    assert NOW < outcome.due_date <= NOW + timedelta(minutes=15)


def test_easy_produces_longer_interval_than_hard_from_scratch():
    scheduler = FSRSScheduler()
    easy = scheduler.review_card(_new_card(), ReviewRating.EASY, now=NOW)
    hard = scheduler.review_card(_new_card(), ReviewRating.HARD, now=NOW)

    assert easy.stability > hard.stability
    assert easy.interval_days >= hard.interval_days


def test_repeated_good_reviews_increase_stability_and_interval():
    scheduler = FSRSScheduler()
    card = _new_card()
    now = NOW

    outcome = scheduler.review_card(card, ReviewRating.GOOD, now=now)
    intervals = [outcome.interval_days]

    for _ in range(4):
        now = outcome.due_date
        snapshot = CardSnapshot(
            stability=outcome.stability,
            difficulty=outcome.difficulty,
            state=outcome.state,
            repetitions=1,
            last_review=now - timedelta(days=outcome.interval_days),
        )
        outcome = scheduler.review_card(snapshot, ReviewRating.GOOD, now=now)
        intervals.append(outcome.interval_days)

    # A well-remembered card should be reviewed less and less often over time.
    assert intervals == sorted(intervals)
    assert intervals[-1] > intervals[0]


def test_again_on_a_review_card_drops_stability_and_enters_relearning():
    scheduler = FSRSScheduler()
    reviewed_card = CardSnapshot(
        stability=20.0,
        difficulty=5.0,
        state=CardState.REVIEW,
        repetitions=3,
        last_review=NOW - timedelta(days=15),
    )

    outcome = scheduler.review_card(reviewed_card, ReviewRating.AGAIN, now=NOW)

    assert outcome.state == CardState.RELEARNING
    assert outcome.stability < reviewed_card.stability
    assert NOW < outcome.due_date <= NOW + timedelta(minutes=15)


def test_retrievability_decreases_as_elapsed_time_grows():
    scheduler = FSRSScheduler()
    r_soon = scheduler.retrievability(elapsed_days=1, stability=10)
    r_later = scheduler.retrievability(elapsed_days=30, stability=10)

    assert 0.0 < r_later < r_soon <= 1.0


def test_maximum_interval_is_respected():
    scheduler = FSRSScheduler(maximum_interval=30)
    huge_stability_card = CardSnapshot(
        stability=10_000.0,
        difficulty=1.0,
        state=CardState.REVIEW,
        repetitions=10,
        last_review=NOW - timedelta(days=1),
    )

    outcome = scheduler.review_card(huge_stability_card, ReviewRating.EASY, now=NOW)

    assert outcome.interval_days <= 30
