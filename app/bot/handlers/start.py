"""Handles `/start` - either onboards a brand-new user, or greets a
returning one and shows the main menu.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from app.bot.handlers.common import show_main_menu
from app.bot.keyboards.onboarding import daily_goal_keyboard, goal_keyboard, level_keyboard
from app.bot.messages.onboarding_texts import (
    ASK_DAILY_GOAL,
    ASK_GOAL,
    ASK_LEVEL,
    WELCOME,
    WELCOME_BACK,
    onboarding_complete,
)
from app.bot.states import (
    CB_ONBOARDING_DAILY_GOAL,
    CB_ONBOARDING_GOAL,
    CB_ONBOARDING_LEVEL,
    OnboardingState,
    parse_callback,
)
from app.core.exceptions import ValidationError
from app.database.engine import session_scope
from app.models.enums import CEFRLevel, LearningGoal
from app.services.onboarding_service import OnboardingSelections, OnboardingService

logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point for `/start`. Branches: new user -> onboarding, existing user -> main menu."""
    telegram_user = update.effective_user
    assert telegram_user is not None

    with session_scope() as session:
        service = OnboardingService(session)
        existing_user = service.get_existing_user(telegram_user.id)

        if existing_user is not None:
            await update.effective_chat.send_message(WELCOME_BACK, parse_mode="Markdown")
            await show_main_menu(update, context, existing_user)
            return ConversationHandler.END

    # New user: start the onboarding conversation.
    context.user_data.clear()
    await update.effective_chat.send_message(WELCOME, parse_mode="Markdown")
    await update.effective_chat.send_message(ASK_LEVEL, reply_markup=level_keyboard(), parse_mode="Markdown")
    return OnboardingState.CHOOSING_LEVEL


async def on_level_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    assert query is not None
    await query.answer()

    _, _, raw_level = parse_callback(query.data)
    context.user_data["level"] = CEFRLevel(raw_level)

    await query.edit_message_text(ASK_GOAL, reply_markup=goal_keyboard(), parse_mode="Markdown")
    return OnboardingState.CHOOSING_GOAL


async def on_goal_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    assert query is not None
    await query.answer()

    _, _, raw_goal = parse_callback(query.data)
    context.user_data["learning_goal"] = LearningGoal(raw_goal)

    await query.edit_message_text(
        ASK_DAILY_GOAL, reply_markup=daily_goal_keyboard(), parse_mode="Markdown"
    )
    return OnboardingState.CHOOSING_DAILY_GOAL


async def on_daily_goal_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    assert query is not None
    await query.answer()

    _, _, raw_daily_goal = parse_callback(query.data)
    daily_goal = int(raw_daily_goal)

    telegram_user = update.effective_user
    assert telegram_user is not None

    selections = OnboardingSelections(
        level=context.user_data["level"],
        learning_goal=context.user_data["learning_goal"],
        daily_goal=daily_goal,
    )

    with session_scope() as session:
        service = OnboardingService(session)
        try:
            user = service.complete_onboarding(
                telegram_id=telegram_user.id,
                username=telegram_user.username,
                selections=selections,
            )
        except ValidationError as exc:
            logger.warning("Onboarding validation error for %s: %s", telegram_user.id, exc)
            await query.edit_message_text(
                "Something went wrong saving your preferences. Please try /start again."
            )
            return ConversationHandler.END

        await query.edit_message_text(
            onboarding_complete(user.level.value, user.learning_goal.value, user.daily_goal),
            parse_mode="Markdown",
        )
        await show_main_menu(update, context, user)

    context.user_data.clear()
    return ConversationHandler.END


async def cancel_onboarding(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data.clear()
    await update.effective_chat.send_message("Onboarding cancelled. Send /start to try again.")
    return ConversationHandler.END
