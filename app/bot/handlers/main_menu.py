"""Dispatches taps on the main menu's inline buttons (`menu:<section>`).

`main` and `settings` are fully implemented in Phase 3. Every other
section routes to its own handler module (learn.py, review.py,
etc.) - those currently just show a placeholder screen, but the
routing itself won't need to change once Phases 4-7 fill them in.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.handlers.common import show_main_menu
from app.bot.handlers.daily_lesson import on_daily_lesson_selected
from app.bot.handlers.ielts import on_ielts_selected
from app.bot.handlers.learn import on_learn_selected
from app.bot.handlers.progress import on_progress_selected
from app.bot.handlers.review import on_review_selected
from app.bot.handlers.settings import show_settings_overview
from app.bot.handlers.vocabulary import on_vocabulary_selected
from app.bot.states import parse_callback
from app.core.exceptions import UserNotFoundError
from app.database.engine import session_scope
from app.models.user import User
from app.repositories.user_repository import UserRepository

_SECTION_HANDLERS = {
    "learn": on_learn_selected,
    "review": on_review_selected,
    "daily_lesson": on_daily_lesson_selected,
    "ielts": on_ielts_selected,
    "progress": on_progress_selected,
    "vocabulary": on_vocabulary_selected,
}


async def on_menu_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    assert query is not None

    _, section = parse_callback(query.data)
    telegram_user = update.effective_user
    assert telegram_user is not None

    with session_scope() as session:
        user: User | None = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:
            await query.answer()
            raise UserNotFoundError(
                f"telegram_id={telegram_user.id} pressed a menu button with no user row - "
                "should not happen, since the main menu is only ever shown post-onboarding"
            )

        if section == "main":
            await show_main_menu(update, context, user)
            return

        if section == "settings":
            await query.answer()
            await show_settings_overview(update, context, user)
            return

        handler = _SECTION_HANDLERS.get(section)
        if handler is None:
            await query.answer("Unknown menu option.", show_alert=True)
            return

        await handler(update, context, user)
