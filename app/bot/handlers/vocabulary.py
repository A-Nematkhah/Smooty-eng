"""⭐ My Vocabulary section + `/addword`, `/search`, `/find` commands (Phase 5).

The menu section shows favorites and "most difficult" words; the
commands manage the shared vocabulary table directly, independent of
the main menu's callback flow (a user can type `/addword` any time,
not just while the vocabulary screen is open).
"""

from __future__ import annotations

import logging

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.vocabulary_keyboard import (
    search_result_keyboard,
    vocabulary_overview_keyboard,
)
from app.bot.messages.vocabulary_texts import (
    ADDWORD_USAGE,
    NO_SEARCH_RESULTS,
    SEARCH_USAGE,
    addword_success,
    search_result_line,
    search_results_header,
    vocabulary_overview,
)
from app.bot.states import parse_callback
from app.core.exceptions import CardNotFoundError, DuplicateEntityError
from app.database.engine import session_scope
from app.models.enums import CardState
from app.models.user import User
from app.repositories.card_repository import CardRepository
from app.repositories.user_repository import UserRepository
from app.services.learning_service import LearningService

logger = logging.getLogger(__name__)

_NOT_ONBOARDED = "Please run /start first to set up your profile."
_MAX_SEARCH_RESULTS_SHOWN = 5

_ALL_CARD_STATES = (
    CardState.NEW,
    CardState.LEARNING,
    CardState.REVIEW,
    CardState.RELEARNING,
)


async def on_vocabulary_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from the main menu's "⭐ My Vocabulary" button."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    with session_scope() as session:
        service = LearningService(session)
        cards = CardRepository(session)

        favorites = [(pair.word, pair.card) for pair in service.list_favorites(user.id, limit=5)]
        difficult = [(pair.word, pair.card) for pair in service.list_difficult_words(user.id, limit=5)]
        total_learning = _count_all_cards(cards, user.id)
        total_learned = cards.count_by_state(user.id, CardState.REVIEW)

    text = vocabulary_overview(
        favorites=favorites,
        difficult=difficult,
        total_learning=total_learning,
        total_learned=total_learned,
    )
    await query.edit_message_text(
        text, reply_markup=vocabulary_overview_keyboard(), parse_mode="Markdown"
    )


async def addword_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/addword word | meaning | example` - add + immediately enroll a custom word."""
    message = update.effective_message
    telegram_user = update.effective_user
    assert message is not None and telegram_user is not None

    raw_args = message.text.split(maxsplit=1)[1] if message.text and " " in message.text else ""
    parts = [part.strip() for part in raw_args.split("|")]

    if len(parts) < 2 or not parts[0] or not parts[1]:
        await message.reply_text(ADDWORD_USAGE, parse_mode="Markdown")
        return

    word_text, meaning_text = parts[0], parts[1]
    example_text = parts[2] if len(parts) > 2 and parts[2] else None

    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:
            await message.reply_text(_NOT_ONBOARDED)
            return

        try:
            result = LearningService(session).add_custom_word(
                user, word=word_text, meaning=meaning_text, example=example_text
            )
        except DuplicateEntityError as exc:
            await message.reply_text(f"⚠️ {exc}")
            return
        except ValueError:
            await message.reply_text(ADDWORD_USAGE, parse_mode="Markdown")
            return

        text = addword_success(result.word)

    await message.reply_text(text, parse_mode="Markdown")


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """`/search <query>` (aliased as `/find`) - look up words by text or meaning."""
    message = update.effective_message
    assert message is not None

    query_text = (
        message.text.split(maxsplit=1)[1].strip() if message.text and " " in message.text else ""
    )
    if not query_text:
        await message.reply_text(SEARCH_USAGE, parse_mode="Markdown")
        return

    with session_scope() as session:
        results = LearningService(session).search(query_text, limit=_MAX_SEARCH_RESULTS_SHOWN)
        if not results:
            await message.reply_text(NO_SEARCH_RESULTS)
            return

        await message.reply_text(
            search_results_header(query_text, len(results)), parse_mode="Markdown"
        )
        for word in results:
            await message.reply_text(
                search_result_line(word),
                reply_markup=search_result_keyboard(word.id),
                parse_mode="Markdown",
            )


async def on_vocabulary_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the "➕ Add to my queue" button under a `/search` result,
    and the "⭐ Toggle favorite" button shown during a review session.
    """
    query = update.callback_query
    telegram_user = update.effective_user
    assert query is not None and telegram_user is not None

    parts = parse_callback(query.data)  # ["vocab", "enroll"|"fav", id]
    action, raw_id = parts[1], parts[2]

    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:
            await query.answer(_NOT_ONBOARDED, show_alert=True)
            return

        if action == "enroll":
            LearningService(session).enroll_word(user.id, int(raw_id))
            await query.answer("Added to your review queue ✅")
            return

        if action == "fav":
            try:
                card = LearningService(session).toggle_favorite(user.id, int(raw_id))
            except CardNotFoundError:
                await query.answer("Couldn't find that card.", show_alert=True)
                return
            toast = "⭐ Added to favorites" if card.is_favorite else "💔 Removed from favorites"
            await query.answer(toast)
            return

        await query.answer()  # pragma: no cover - defensive


def _count_all_cards(cards: CardRepository, user_id: int) -> int:
    return sum(cards.count_by_state(user_id, state) for state in _ALL_CARD_STATES)
