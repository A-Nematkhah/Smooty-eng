"""Builds and configures the python-telegram-bot Application.

This is the only module that wires handlers together. Handlers
themselves stay independent of *how* they're registered (command vs
callback vs conversation state), so registration can be reorganized
here without touching handler logic.
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
)

from app.bot.handlers.main_menu import on_menu_selected
from app.bot.handlers.ielts import on_ielts_callback
from app.bot.handlers.learn import on_learn_callback
from app.bot.handlers.quiz import on_quiz_callback
from app.bot.handlers.review import on_review_callback
from app.bot.handlers.settings import on_settings_selected
from app.bot.handlers.start import (
    cancel_onboarding,
    on_daily_goal_chosen,
    on_goal_chosen,
    on_level_chosen,
    start_command,
)
from app.bot.handlers.vocabulary import addword_command, on_vocabulary_callback, search_command
from app.bot.states import (
    CB_IELTS,
    CB_LEARN,
    CB_MENU,
    CB_ONBOARDING_DAILY_GOAL,
    CB_ONBOARDING_GOAL,
    CB_ONBOARDING_LEVEL,
    CB_QUIZ,
    CB_REVIEW,
    CB_SETTINGS,
    CB_VOCAB,
    OnboardingState,
)
from app.core.config import get_settings

logger = logging.getLogger(__name__)

_HELP_TEXT = (
    "🤖 *Personal English Coach*\n\n"
    "/start - begin onboarding or open the main menu\n"
    "/help - show this message\n"
    "/cancel - cancel an in-progress onboarding\n"
    "/addword word | meaning | example - add a custom word\n"
    "/search <query> (or /find) - look up a word\n\n"
    "Once you're set up, everything else is driven by the menu buttons."
)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.effective_chat.send_message(_HELP_TEXT, parse_mode="Markdown")


def build_application() -> Application:
    """Construct the Application with every Phase 3 handler registered."""
    settings = get_settings()
    application = Application.builder().token(settings.telegram_bot_token).build()

    onboarding_conversation = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            OnboardingState.CHOOSING_LEVEL: [
                CallbackQueryHandler(on_level_chosen, pattern=f"^{CB_ONBOARDING_LEVEL}:")
            ],
            OnboardingState.CHOOSING_GOAL: [
                CallbackQueryHandler(on_goal_chosen, pattern=f"^{CB_ONBOARDING_GOAL}:")
            ],
            OnboardingState.CHOOSING_DAILY_GOAL: [
                CallbackQueryHandler(on_daily_goal_chosen, pattern=f"^{CB_ONBOARDING_DAILY_GOAL}:")
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel_onboarding)],
        name="onboarding_conversation",
        # Returning users are handled inside start_command itself (it ends the
        # conversation immediately), so no persistent conversation state needs
        # to survive a restart for this flow.
        persistent=False,
    )

    application.add_handler(onboarding_conversation)
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("addword", addword_command))
    application.add_handler(CommandHandler(["search", "find"], search_command))
    application.add_handler(CallbackQueryHandler(on_menu_selected, pattern=f"^{CB_MENU}:"))
    application.add_handler(CallbackQueryHandler(on_settings_selected, pattern=f"^{CB_SETTINGS}:"))
    application.add_handler(CallbackQueryHandler(on_review_callback, pattern=f"^{CB_REVIEW}:"))
    application.add_handler(CallbackQueryHandler(on_learn_callback, pattern=f"^{CB_LEARN}:"))
    application.add_handler(CallbackQueryHandler(on_vocabulary_callback, pattern=f"^{CB_VOCAB}:"))
    application.add_handler(CallbackQueryHandler(on_quiz_callback, pattern=f"^{CB_QUIZ}:"))
    application.add_handler(CallbackQueryHandler(on_ielts_callback, pattern=f"^{CB_IELTS}:"))

    return application
