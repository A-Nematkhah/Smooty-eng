"""Handles the ⚙ Settings menu: showing the overview and editing
each individual field (level, goal, daily goal, reminder time, mode).
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.settings_keyboard import (
    settings_daily_goal_keyboard,
    settings_goal_keyboard,
    settings_level_keyboard,
    settings_mode_keyboard,
    settings_overview_keyboard,
    settings_reminder_time_keyboard,
)
from app.bot.messages.settings_texts import (
    ASK_NEW_DAILY_GOAL,
    ASK_NEW_GOAL,
    ASK_NEW_LEVEL,
    ASK_NEW_MODE,
    ASK_NEW_REMINDER_TIME,
    settings_overview,
)
from app.bot.states import parse_callback
from app.core.exceptions import ValidationError
from app.database.engine import session_scope
from app.models.enums import CEFRLevel, LearningGoal, LearningMode
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.settings_service import SettingsService

logger = logging.getLogger(__name__)

_SUB_SCREENS = {
    "level": (ASK_NEW_LEVEL, settings_level_keyboard),
    "goal": (ASK_NEW_GOAL, settings_goal_keyboard),
    "daily_goal": (ASK_NEW_DAILY_GOAL, settings_daily_goal_keyboard),
    "reminder_time": (ASK_NEW_REMINDER_TIME, settings_reminder_time_keyboard),
    "mode": (ASK_NEW_MODE, settings_mode_keyboard),
}


async def show_settings_overview(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    query = update.callback_query
    assert query is not None
    await query.edit_message_text(
        settings_overview(user), reply_markup=settings_overview_keyboard(), parse_mode="Markdown"
    )


async def on_settings_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    # maxsplit=2: "value" can itself contain ':' (a "HH:MM" reminder
    # time), so it must survive intact as parts[2] instead of being
    # split further.
    parts = parse_callback(query.data, maxsplit=2)  # ["settings", field] or ["settings", field, value]
    field = parts[1]
    value = parts[2] if len(parts) > 2 else None

    telegram_user = update.effective_user
    assert telegram_user is not None

    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:
            logger.warning("Settings callback from unknown telegram_id=%s", telegram_user.id)
            return

        if field == "back":
            await show_settings_overview(update, context, user)
            return

        if value is None:
            # First tap on a field: show the sub-screen with choices.
            prompt, keyboard_fn = _SUB_SCREENS[field]
            await query.edit_message_text(prompt, reply_markup=keyboard_fn(), parse_mode="Markdown")
            return

        # Second tap: a value was chosen - validate, persist, go back to overview.
        service = SettingsService(session)
        try:
            _apply_setting(service, user, field, value)
        except ValidationError as exc:
            logger.warning("Invalid settings value field=%s value=%s: %s", field, value, exc)
            await query.edit_message_text(f"⚠ {exc}\n\nPlease try again from ⚙ Settings.")
            return

        await show_settings_overview(update, context, user)


def _apply_setting(service: SettingsService, user: User, field: str, value: str) -> None:
    if field == "level":
        service.update_level(user, CEFRLevel(value))
    elif field == "goal":
        service.update_learning_goal(user, LearningGoal(value))
    elif field == "daily_goal":
        service.update_daily_goal(user, int(value))
    elif field == "reminder_time":
        service.update_reminder_time(user, value)
    elif field == "mode":
        service.update_learning_mode(user, LearningMode(value))
    else:  # pragma: no cover - defensive, keyboards never emit unknown fields
        raise ValidationError(f"Unknown settings field: {field}")
