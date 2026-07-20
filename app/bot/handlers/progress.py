"""📊 Progress section.

Was left as a placeholder through Phases 4-7 even though every
number it needs (`Progress` rollup, review accuracy, learned-word
counts) was already being written by `ReviewService.grade_card` -
this just assembles and renders it via `ProgressService`.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.progress_keyboard import progress_keyboard
from app.bot.messages.progress_texts import progress_overview
from app.database.engine import session_scope
from app.models.user import User
from app.services.progress_service import ProgressService


async def on_progress_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    with session_scope() as session:
        dashboard = ProgressService(session).dashboard(user)

    await query.edit_message_text(
        progress_overview(dashboard), reply_markup=progress_keyboard(), parse_mode="Markdown"
    )
