"""📝 Quiz mini-flow (Phase 6), reached from 🎯 Daily Lesson.

One multiple-choice question at a time: pick an option → immediate
feedback (correct/incorrect + the right answer) → "Next question" →
repeat → score summary with XP. Quiz correctness isn't logged to the
FSRS `reviews` table (that's reserved for the Again/Hard/Good/Easy
grading scale in `ReviewService`) - it's a lighter-weight retention
check, so its XP/score bookkeeping stays local to this session.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.quiz_keyboard import (
    quiz_complete_keyboard,
    quiz_next_keyboard,
    quiz_question_keyboard,
)
from app.bot.messages.quiz_texts import (
    NO_QUIZ_AVAILABLE,
    quiz_complete_text,
    quiz_feedback_text,
    quiz_question_text,
)
from app.bot.states import parse_callback
from app.database.engine import session_scope
from app.models.user import User
from app.quizzes.multiple_choice import QuizQuestion
from app.repositories.progress_repository import ProgressRepository
from app.repositories.user_repository import UserRepository
from app.services.daily_lesson_service import DailyLessonService

logger = logging.getLogger(__name__)

_USER_DATA_KEY = "quiz_session"
_QUIZ_SIZE = 10
_XP_PER_CORRECT_ANSWER = 2


@dataclass
class _QuizState:
    questions: list[QuizQuestion]
    position: int = 0
    score: int = 0
    awaiting_next: bool = False


async def on_quiz_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from the 🎯 Daily Lesson dashboard's "📝 Start quiz" button."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    with session_scope() as session:
        questions = DailyLessonService(session).build_quiz(user, size=_QUIZ_SIZE)

    if not questions:
        await query.edit_message_text(
            NO_QUIZ_AVAILABLE, reply_markup=quiz_complete_keyboard(), parse_mode="Markdown"
        )
        return

    context.user_data[_USER_DATA_KEY] = _QuizState(questions=questions)
    await _show_question(update, context)


async def on_quiz_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatches `quiz:start`, `quiz:answer:<pos>:<opt>`, and `quiz:next:<pos>`."""
    query = update.callback_query
    assert query is not None

    parts = parse_callback(query.data)
    action = parts[1]

    if action == "start":
        telegram_user = update.effective_user
        assert telegram_user is not None
        with session_scope() as session:
            user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:  # pragma: no cover - defensive
            await query.answer("Please run /start first.", show_alert=True)
            return
        await on_quiz_start(update, context, user)
        return

    state: _QuizState | None = context.user_data.get(_USER_DATA_KEY)
    position = int(parts[2])

    if state is None or position != state.position:
        await query.answer("This quiz session has ended.", show_alert=True)
        return

    if action == "answer" and not state.awaiting_next:
        option_index = int(parts[3])
        await query.answer()
        await _grade_answer(update, context, state, option_index=option_index)
        return

    if action == "next" and state.awaiting_next:
        await query.answer()
        await _advance(update, context, state)
        return

    await query.answer()  # pragma: no cover - stale/duplicate tap on an already-handled step


async def _show_question(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state: _QuizState = context.user_data[_USER_DATA_KEY]
    question = state.questions[state.position]
    text = quiz_question_text(question, position=state.position + 1, total=len(state.questions))
    await _edit(update, text, quiz_question_keyboard(state.position, question.options))


async def _grade_answer(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: _QuizState, *, option_index: int
) -> None:
    question = state.questions[state.position]
    if option_index == question.correct_index:
        state.score += 1

    state.awaiting_next = True
    text = quiz_feedback_text(question, chosen_index=option_index)
    is_last = state.position == len(state.questions) - 1
    await _edit(update, text, quiz_next_keyboard(state.position, is_last=is_last))


async def _advance(update: Update, context: ContextTypes.DEFAULT_TYPE, state: _QuizState) -> None:
    state.position += 1
    state.awaiting_next = False

    if state.position >= len(state.questions):
        await _finish_quiz(update, context, state)
        return

    await _show_question(update, context)


async def _finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, state: _QuizState) -> None:
    telegram_user = update.effective_user
    assert telegram_user is not None

    xp_awarded = state.score * _XP_PER_CORRECT_ANSWER
    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is not None:
            progress_repo = ProgressRepository(session)
            progress = progress_repo.get_or_create(user.id)
            progress_repo.update(progress, xp=progress.xp + xp_awarded)

    text = quiz_complete_text(score=state.score, total=len(state.questions), xp_awarded=xp_awarded)
    await _edit(update, text, quiz_complete_keyboard())
    context.user_data.pop(_USER_DATA_KEY, None)


async def _edit(update: Update, text: str, keyboard) -> None:
    query = update.callback_query
    assert query is not None
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
