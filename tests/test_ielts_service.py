"""Tests for `IELTSService` (Phase 7)."""

from __future__ import annotations

from app.models.enums import CEFRLevel, LearningGoal, ReviewRating, WordSource
from app.repositories.user_repository import UserRepository
from app.repositories.word_repository import WordRepository
from app.services.ielts_service import IELTSService
from app.services.learning_service import LearningService
from app.services.review_service import ReviewService


def _make_user(db_session, telegram_id=1, daily_goal=5):
    return UserRepository(db_session).create(
        telegram_id=telegram_id,
        username="learner",
        level=CEFRLevel.B1,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=daily_goal,
    )


def _seed_ielts_words(db_session, specs):
    repo = WordRepository(db_session)
    return [
        repo.create(
            word=word,
            meaning=meaning,
            source=WordSource.IELTS,
            ielts_topic=topic,
            ielts_band=band,
        )
        for word, meaning, topic, band in specs
    ]


def test_list_topics_returns_distinct_sorted_topics(db_session):
    _seed_ielts_words(
        db_session,
        [
            ("sustainable", "پایدار", "Environment", "8+"),
            ("pollution", "آلودگی", "Environment", "7+"),
            ("curriculum", "برنامه درسی", "Education", "7+"),
        ],
    )

    topics = IELTSService(db_session).list_topics()
    assert topics == ["Education", "Environment"]


def test_words_by_topic_filters_correctly(db_session):
    _seed_ielts_words(
        db_session,
        [
            ("sustainable", "پایدار", "Environment", "8+"),
            ("curriculum", "برنامه درسی", "Education", "7+"),
        ],
    )

    words = IELTSService(db_session).words_by_topic("Environment")
    assert [w.word for w in words] == ["sustainable"]


def test_stats_report_zero_for_a_fresh_user(db_session):
    user = _make_user(db_session)
    _seed_ielts_words(db_session, [("sustainable", "پایدار", "Environment", "8+")])

    stats = IELTSService(db_session).stats(user)

    assert stats.total_ielts_words == 1
    assert stats.enrolled == 0
    assert stats.learned == 0
    assert stats.due_for_review == 0


def test_stats_track_enrollment_and_review_progress(db_session):
    user = _make_user(db_session)
    words = _seed_ielts_words(
        db_session,
        [
            ("sustainable", "پایدار", "Environment", "8+"),
            ("curriculum", "برنامه درسی", "Education", "7+"),
        ],
    )
    learning = LearningService(db_session)
    reviewer = ReviewService(db_session)

    card = learning.enroll_word(user.id, words[0].id)
    learning.enroll_word(user.id, words[1].id)
    reviewer.grade_card(user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD)

    stats = IELTSService(db_session).stats(user)

    assert stats.enrolled == 2
    assert stats.learned == 1  # only the graded one graduated to REVIEW


def test_get_new_words_only_returns_ielts_words_even_for_general_goal_user(db_session):
    user = _make_user(db_session)  # learning_goal=GENERAL, not IELTS-focused
    ielts_words = _seed_ielts_words(db_session, [("sustainable", "پایدار", "Environment", "8+")])
    WordRepository(db_session).create(word="cat", meaning="گربه", source=WordSource.OXFORD_3000)

    # Request exactly as many as are available from IELTS, so the
    # "pad with any source" fallback never has to kick in.
    words = IELTSService(db_session).get_new_words(user, limit=len(ielts_words))

    assert {w.id for w in words} == {w.id for w in ielts_words}


def test_get_due_queue_only_includes_ielts_cards(db_session):
    user = _make_user(db_session)
    ielts_words = _seed_ielts_words(db_session, [("sustainable", "پایدار", "Environment", "8+")])
    oxford_word = WordRepository(db_session).create(
        word="cat", meaning="گربه", source=WordSource.OXFORD_3000
    )

    learning = LearningService(db_session)
    learning.enroll_word(user.id, ielts_words[0].id)
    learning.enroll_word(user.id, oxford_word.id)

    due = IELTSService(db_session).get_due_queue(user)

    assert len(due) == 1
    assert due[0].word.id == ielts_words[0].id
