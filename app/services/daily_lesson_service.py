"""Daily Lesson orchestration (Phase 6).

Per the master spec, a daily lesson bundles three things:
new words to learn, words due for review, and a quiz. Rather than
reinventing "show new words" and "review due cards" (Phases 4-5
already do exactly that), `DailyLessonService` only computes *how
much* of each is on today's plate and builds the quiz; the bot
handler then routes "Learn"/"Review" taps straight into the existing
Learn/Review flows and adds its own quiz mini-flow for the third part.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, time, timedelta, timezone

from sqlalchemy.orm import Session

from app.models.user import User
from app.models.word import Word
from app.quizzes.multiple_choice import QuizQuestion, build_multiple_choice_question
from app.repositories.card_repository import CardRepository
from app.repositories.review_repository import ReviewRepository
from app.repositories.word_repository import WordRepository
from app.services.learning_service import LearningService
from app.services.review_service import ReviewService

_DEFAULT_QUIZ_SIZE = 10
_DISTRACTOR_POOL_SIZE = 6


@dataclass(frozen=True)
class DailyLessonPlan:
    """Everything the 🎯 Daily Lesson dashboard needs to render itself."""

    new_words: list[Word]
    due_review_count: int
    quiz_questions: list[QuizQuestion]
    reviews_done_today: int
    daily_goal: int


class DailyLessonService:
    """Backs the 🎯 Daily Lesson section."""

    def __init__(self, session: Session) -> None:
        self._session = session
        self._learning = LearningService(session)
        self._reviews = ReviewService(session)
        self._review_repo = ReviewRepository(session)
        self._cards = CardRepository(session)
        self._words = WordRepository(session)

    def build_plan(
        self, user: User, *, quiz_size: int = _DEFAULT_QUIZ_SIZE, now: datetime | None = None
    ) -> DailyLessonPlan:
        now = now or datetime.now(timezone.utc)

        new_words = self._learning.get_new_words(user, limit=user.daily_goal)
        due_review_count = self._reviews.count_due(user.id, as_of=now)
        quiz_questions = self.build_quiz(user, size=quiz_size)
        reviews_done_today = self._reviews_done_today(user.id, now)

        return DailyLessonPlan(
            new_words=new_words,
            due_review_count=due_review_count,
            quiz_questions=quiz_questions,
            reviews_done_today=reviews_done_today,
            daily_goal=user.daily_goal,
        )

    def build_quiz(
        self, user: User, *, size: int = _DEFAULT_QUIZ_SIZE, rng: random.Random | None = None
    ) -> list[QuizQuestion]:
        """Multiple-choice quiz drawn from words the user is already
        learning (best for testing retention); if there aren't enough
        of those yet (a brand-new user), it's padded with words from
        today's new-word batch so the quiz never comes up empty.
        """
        rng = rng or random.Random()

        target_words = self._quiz_candidate_words(user, size)
        if not target_words:
            return []

        target_ids = {word.id for word in target_words}
        questions: list[QuizQuestion] = []
        for word in target_words:
            distractors = self._words.list_random_excluding(
                exclude_ids=list(target_ids), limit=_DISTRACTOR_POOL_SIZE, level=word.level
            )
            if len(distractors) < 3:
                # Thin same-level pool - broaden to any level rather than
                # shipping a two-option question.
                distractors = self._words.list_random_excluding(
                    exclude_ids=list(target_ids), limit=_DISTRACTOR_POOL_SIZE
                )
            questions.append(build_multiple_choice_question(word, distractors, rng=rng))
        return questions

    # --- internals -------------------------------------------------------

    def _quiz_candidate_words(self, user: User, size: int) -> list[Word]:
        """Words the user already has a card for, regardless of state,
        preferring ones seen more than once (REVIEW/RELEARNING) since
        those are the words retention-testing is actually useful for.
        """
        from app.models.enums import CardState

        seen_word_ids: list[int] = []
        for state in (CardState.REVIEW, CardState.RELEARNING, CardState.LEARNING):
            for card in self._cards.list_by_state_sample(user.id, state, limit=size):
                if card.word_id not in seen_word_ids:
                    seen_word_ids.append(card.word_id)
            if len(seen_word_ids) >= size:
                break

        words = [self._words.get_by_id(word_id) for word_id in seen_word_ids[:size]]
        words = [w for w in words if w is not None]

        if len(words) < size:
            fallback = self._learning.get_new_words(user, limit=size - len(words))
            existing_ids = {w.id for w in words}
            words.extend(w for w in fallback if w.id not in existing_ids)

        return words[:size]

    def _reviews_done_today(self, user_id: int, now: datetime) -> int:
        day_start = datetime.combine(now.date(), time.min, tzinfo=now.tzinfo)
        day_end = day_start + timedelta(days=1)
        return self._review_repo.count_for_day(user_id, day_start, day_end)
