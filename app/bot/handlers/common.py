"""Helpers shared across handler modules.

Kept here (rather than duplicated in start.py / main_menu.py) since
both the onboarding flow and every "back to menu" button need to
render the same main-menu message.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.main_menu import back_to_main_menu_keyboard, main_menu_keyboard
from app.bot.messages.main_menu_texts import PLACEHOLDER_COMING_SOON, main_menu_with_stats
from app.models.user import User


async def show_placeholder(update: Update, title: str) -> None:
    """Shown for main-menu sections not yet implemented (Phases 4-7).

    Every button in the UI should always respond to a tap, even
    before its real logic exists - this keeps that promise without
    each stub handler duplicating the same edit_message_text call.
    """
    query = update.callback_query
    assert query is not None
    await query.answer()
    await query.edit_message_text(
        f"{title}\n\n{PLACEHOLDER_COMING_SOON}", reply_markup=back_to_main_menu_keyboard()
    )


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Render the main menu, editing the existing message if this came
    from a button tap, or sending a new one if this came from a command.
    """
    text = main_menu_with_stats(user)
    keyboard = main_menu_keyboard()

    query = update.callback_query
    if query is not None:
        await query.answer()
        await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")
    else:
        await update.effective_chat.send_message(text, reply_markup=keyboard, parse_mode="Markdown")
