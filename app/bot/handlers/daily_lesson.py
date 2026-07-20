"""🎯 Daily Lesson section (Phase 6).

A dashboard, not its own session: it shows how many new words are
ready, how many reviews are due, and how big today's quiz is, then
routes into the existing 📚 Learn / 🔄 Review flows (Phases 4-5) or
the new 📝 quiz mini-flow depending on which button the user taps.
"""

from __future__ import annotations

from datetime import datetime, timezone

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.daily_lesson_keyboard import daily_lesson_keyboard
from app.bot.messages.daily_lesson_texts import daily_lesson_overview
from app.database.engine import session_scope
from app.models.user import User
from app.services.daily_lesson_service import DailyLessonService


async def on_daily_lesson_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from the main menu's "🎯 Daily Lesson" button."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    with session_scope() as session:
        plan = DailyLessonService(session).build_plan(user)

    day_number = _day_number(user)
    text = daily_lesson_overview(plan, day_number=day_number)
    keyboard = daily_lesson_keyboard(
        new_words_count=len(plan.new_words),
        due_review_count=plan.due_review_count,
        quiz_count=len(plan.quiz_questions),
    )
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


def _day_number(user: User) -> int:
    created = user.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    return (datetime.now(timezone.utc).date() - created.date()).days + 1
