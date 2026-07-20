"""Tests for `DailyLessonService` (Phase 6)."""

from __future__ import annotations

from app.models.enums import CEFRLevel, LearningGoal, ReviewRating, WordSource
from app.repositories.user_repository import UserRepository
from app.repositories.word_repository import WordRepository
from app.services.daily_lesson_service import DailyLessonService
from app.services.learning_service import LearningService
from app.services.review_service import ReviewService


def _make_user(db_session, telegram_id=1, daily_goal=3):
    return UserRepository(db_session).create(
        telegram_id=telegram_id,
        username="learner",
        level=CEFRLevel.B1,
        learning_goal=LearningGoal.GENERAL,
        daily_goal=daily_goal,
    )


def _seed_words(db_session, n, level=CEFRLevel.B1):
    repo = WordRepository(db_session)
    return [
        repo.create(word=f"word{i}", meaning=f"meaning{i}", level=level, source=WordSource.OXFORD_3000)
        for i in range(n)
    ]


def test_build_plan_reports_new_words_and_due_reviews(db_session):
    user = _make_user(db_session, daily_goal=3)
    _seed_words(db_session, 10)

    service = DailyLessonService(db_session)
    plan = service.build_plan(user)

    assert len(plan.new_words) == 3  # capped at daily_goal
    assert plan.due_review_count == 0  # nothing enrolled yet
    assert plan.daily_goal == 3
    assert plan.reviews_done_today == 0


def test_build_plan_counts_due_reviews_after_enrolling(db_session):
    user = _make_user(db_session)
    words = _seed_words(db_session, 5)
    learning = LearningService(db_session)
    for w in words[:2]:
        learning.enroll_word(user.id, w.id)

    service = DailyLessonService(db_session)
    plan = service.build_plan(user)

    assert plan.due_review_count == 2  # freshly enrolled NEW cards are due immediately


def test_build_plan_counts_reviews_done_today(db_session):
    user = _make_user(db_session)
    words = _seed_words(db_session, 2)
    review_service = ReviewService(db_session)
    card = review_service.get_or_create_card(user.id, words[0].id)
    review_service.grade_card(user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD)

    plan = DailyLessonService(db_session).build_plan(user)

    assert plan.reviews_done_today == 1


def test_build_quiz_falls_back_to_new_words_for_fresh_user(db_session):
    user = _make_user(db_session)
    _seed_words(db_session, 5)

    questions = DailyLessonService(db_session).build_quiz(user, size=3)

    assert len(questions) == 3
    assert len({q.word_id for q in questions}) == 3  # no duplicate questions


def test_build_quiz_prefers_already_learned_words(db_session):
    user = _make_user(db_session)
    words = _seed_words(db_session, 10)
    learning = LearningService(db_session)
    review_service = ReviewService(db_session)

    learned = words[:2]
    for w in learned:
        card = learning.enroll_word(user.id, w.id)
        review_service.grade_card(user_id=user.id, card_id=card.id, rating=ReviewRating.GOOD)

    questions = DailyLessonService(db_session).build_quiz(user, size=2)

    assert {q.word_id for q in questions} == {w.id for w in learned}


def test_build_quiz_returns_empty_when_no_words_exist(db_session):
    user = _make_user(db_session)

    questions = DailyLessonService(db_session).build_quiz(user, size=5)

    assert questions == []
