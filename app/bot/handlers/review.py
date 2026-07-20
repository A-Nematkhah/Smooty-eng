"""🔄 Review Words section (Phase 4).

Pulls the due-card queue via `ReviewService.get_due_queue` and runs a
show-front / reveal-back / grade loop, one card at a time, using the
FSRS scheduler under the hood. Session state (the queue + current
position + running XP/streak) lives in `context.user_data` for the
duration of the session - it's per-chat, single-user data that never
needs to survive a bot restart, so `user_data` (not the DB) is the
right place for it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.review_keyboard import (
    review_rating_keyboard,
    review_reveal_keyboard,
    review_session_end_keyboard,
)
from app.bot.messages.review_texts import (
    NO_DUE_WORDS,
    review_card_back,
    review_card_front,
    review_session_complete,
)
from app.bot.states import parse_callback
from app.core.exceptions import CardNotFoundError
from app.database.engine import session_scope
from app.models.enums import ReviewRating
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.review_service import ReviewService

logger = logging.getLogger(__name__)

_MAX_SESSION_SIZE = 20
_USER_DATA_KEY = "review_session"


@dataclass(frozen=True)
class _QueueItem:
    """Plain snapshot of one due card - detached from the DB session
    that produced it, so it's safe to hold in `context.user_data`
    across multiple Telegram updates.
    """

    card_id: int
    word: str
    pronunciation: str | None
    meaning: str
    example: str | None


@dataclass
class _SessionState:
    queue: list[_QueueItem]
    position: int = 0
    reviewed: int = 0
    xp_awarded: int = 0
    streak: int = 0


async def on_review_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from the main menu's "🔄 Review Words" button."""
    query = update.callback_query
    assert query is not None
    await query.answer()

    with session_scope() as session:
        due_cards = ReviewService(session).get_due_queue(user.id, limit=_MAX_SESSION_SIZE)
        queue = _build_queue(due_cards)

    await _start_review_session(update, context, queue)


async def on_ielts_review_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from 🎓 IELTS Mode's "🔄 Review IELTS due" button -
    same session mechanics, restricted to IELTS-sourced cards.
    """
    from app.services.ielts_service import IELTSService

    query = update.callback_query
    assert query is not None
    await query.answer()

    with session_scope() as session:
        due_cards = IELTSService(session).get_due_queue(user, limit=_MAX_SESSION_SIZE)
        queue = _build_queue(due_cards)

    await _start_review_session(update, context, queue)


def _build_queue(due_cards) -> list["_QueueItem"]:
    """Snapshot due cards + words into plain `_QueueItem`s while the
    session that produced them is still open (see the matching note
    in `app/bot/handlers/learn.py`).
    """
    return [
        _QueueItem(
            card_id=due.card.id,
            word=due.word.word,
            pronunciation=due.word.pronunciation,
            meaning=due.word.meaning,
            example=due.word.example,
        )
        for due in due_cards
    ]


async def _start_review_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE, queue: list["_QueueItem"]
) -> None:
    query = update.callback_query
    assert query is not None

    if not queue:
        await query.edit_message_text(
            NO_DUE_WORDS, reply_markup=review_session_end_keyboard(), parse_mode="Markdown"
        )
        return

    context.user_data[_USER_DATA_KEY] = _SessionState(queue=queue)
    await _show_front(update, context)


async def on_review_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles both "👁 Show meaning" and the four rating buttons."""
    query = update.callback_query
    assert query is not None

    parts = parse_callback(query.data)  # ["review", "reveal"|"rate", card_id, rating?]
    action = parts[1]
    card_id = int(parts[2])

    state: _SessionState | None = context.user_data.get(_USER_DATA_KEY)
    if (
        state is None
        or state.position >= len(state.queue)
        or state.queue[state.position].card_id != card_id
    ):
        # Stale button (old session, or double-tap after the session moved
        # on) - answer politely instead of crashing on a mismatched state.
        await query.answer("This review session has ended.", show_alert=True)
        return

    if action == "reveal":
        await query.answer()
        await _show_back(update, context, state)
        return

    if action == "rate":
        rating = ReviewRating(parts[3])
        await query.answer()
        await _grade_and_advance(update, context, state, card_id=card_id, rating=rating)
        return

    await query.answer()  # pragma: no cover - defensive, keyboards never emit unknown actions


async def _show_front(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state: _SessionState = context.user_data[_USER_DATA_KEY]
    item = state.queue[state.position]
    text = review_card_front(
        _as_word_like(item), position=state.position + 1, total=len(state.queue)
    )
    await _edit(update, text, review_reveal_keyboard(item.card_id))


async def _show_back(update: Update, context: ContextTypes.DEFAULT_TYPE, state: _SessionState) -> None:
    item = state.queue[state.position]
    text = review_card_back(
        _as_word_like(item), position=state.position + 1, total=len(state.queue)
    )
    await _edit(update, text, review_rating_keyboard(item.card_id))


async def _grade_and_advance(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    state: _SessionState,
    *,
    card_id: int,
    rating: ReviewRating,
) -> None:
    telegram_user = update.effective_user
    assert telegram_user is not None

    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:  # pragma: no cover - defensive, session pre-checked by caller flow
            logger.warning("Review callback from unknown telegram_id=%s", telegram_user.id)
            return

        try:
            result = ReviewService(session).grade_card(
                user_id=user.id, card_id=card_id, rating=rating
            )
        except CardNotFoundError:
            logger.warning("Graded a card_id=%s that no longer exists", card_id)
            state.position += 1
        else:
            state.reviewed += 1
            state.xp_awarded += result.xp_awarded
            state.streak = result.streak
            state.position += 1

    if state.position >= len(state.queue):
        text = review_session_complete(
            reviewed=state.reviewed, xp_awarded=state.xp_awarded, streak=state.streak
        )
        await _edit(update, text, review_session_end_keyboard())
        context.user_data.pop(_USER_DATA_KEY, None)
        return

    await _show_front(update, context)


async def _edit(update: Update, text: str, keyboard) -> None:
    query = update.callback_query
    assert query is not None
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


def _as_word_like(item: _QueueItem):
    """Adapts a `_QueueItem` to the small attribute surface `review_texts`
    expects from a `Word` ORM instance, without importing SQLAlchemy here.
    """

    class _WordLike:
        word = item.word
        pronunciation = item.pronunciation
        meaning = item.meaning
        example = item.example

    return _WordLike()
