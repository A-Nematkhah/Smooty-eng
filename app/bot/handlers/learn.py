"""📚 Learn English section (Phase 5).

Shows a batch of new words (sized to the user's daily goal) one at a
time: word → reveal meaning/example → "Got it, add to reviews", which
calls `LearningService.enroll_word` to create the FSRS card. Once a
word is enrolled it will show up in 🔄 Review Words as it comes due -
Learn and Review share the same `cards` table, just different entry
points into it.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.keyboards.learn_keyboard import (
    learn_enroll_keyboard,
    learn_reveal_keyboard,
    learn_session_end_keyboard,
)
from app.bot.messages.learn_texts import (
    NO_NEW_WORDS,
    learn_card_back,
    learn_card_front,
    learn_session_complete,
)
from app.bot.states import parse_callback
from app.database.engine import session_scope
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.learning_service import LearningService

logger = logging.getLogger(__name__)

_USER_DATA_KEY = "learn_session"


@dataclass(frozen=True)
class _QueueItem:
    """Plain snapshot of one word to learn - safe to hold in
    `context.user_data` across multiple Telegram updates.
    """

    word_id: int
    word: str
    pronunciation: str | None
    level: str | None
    meaning: str
    example: str | None
    synonyms: str | None


@dataclass
class _SessionState:
    queue: list[_QueueItem]
    position: int = 0
    learned: int = 0


async def on_learn_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from the main menu's "📚 Learn English" button."""
    with session_scope() as session:
        words = LearningService(session).get_new_words(user)
        queue = _build_queue(words)
    await _start_learn_session(update, context, queue)


async def on_ielts_learn_start(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from 🎓 IELTS Mode's "📖 Learn IELTS words" button -
    same session mechanics, just an IELTS-only word pool.
    """
    from app.services.ielts_service import IELTSService

    with session_scope() as session:
        words = IELTSService(session).get_new_words(user)
        queue = _build_queue(words)
    await _start_learn_session(update, context, queue)


def _build_queue(words: list) -> list[_QueueItem]:
    """Snapshot ORM `Word` rows into plain `_QueueItem`s *while the
    session that produced them is still open* - the values then stay
    safely readable in `context.user_data` even after the session
    (and its objects) are closed/expired at the end of the `with` block.
    """
    return [
        _QueueItem(
            word_id=word.id,
            word=word.word,
            pronunciation=word.pronunciation,
            level=word.level.value if word.level else None,
            meaning=word.meaning,
            example=word.example,
            synonyms=word.synonyms,
        )
        for word in words
    ]


async def _start_learn_session(
    update: Update, context: ContextTypes.DEFAULT_TYPE, queue: list[_QueueItem]
) -> None:
    query = update.callback_query
    assert query is not None
    await query.answer()

    if not queue:
        await query.edit_message_text(
            NO_NEW_WORDS, reply_markup=learn_session_end_keyboard(), parse_mode="Markdown"
        )
        return

    context.user_data[_USER_DATA_KEY] = _SessionState(queue=queue)
    await _show_front(update, context)


async def on_learn_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles both "👁 Show meaning" and "➕ Got it - add to reviews"."""
    query = update.callback_query
    assert query is not None

    parts = parse_callback(query.data)  # ["learn", "reveal"|"enroll", word_id]
    action = parts[1]
    word_id = int(parts[2])

    state: _SessionState | None = context.user_data.get(_USER_DATA_KEY)
    if (
        state is None
        or state.position >= len(state.queue)
        or state.queue[state.position].word_id != word_id
    ):
        await query.answer("This learning session has ended.", show_alert=True)
        return

    if action == "reveal":
        await query.answer()
        await _show_back(update, context, state)
        return

    if action == "enroll":
        await query.answer()
        await _enroll_and_advance(update, context, state, word_id=word_id)
        return

    await query.answer()  # pragma: no cover - defensive, keyboards never emit unknown actions


async def _show_front(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    state: _SessionState = context.user_data[_USER_DATA_KEY]
    item = state.queue[state.position]
    text = learn_card_front(_as_word_like(item), position=state.position + 1, total=len(state.queue))
    await _edit(update, text, learn_reveal_keyboard(item.word_id))


async def _show_back(update: Update, context: ContextTypes.DEFAULT_TYPE, state: _SessionState) -> None:
    item = state.queue[state.position]
    text = learn_card_back(_as_word_like(item), position=state.position + 1, total=len(state.queue))
    await _edit(update, text, learn_enroll_keyboard(item.word_id))


async def _enroll_and_advance(
    update: Update, context: ContextTypes.DEFAULT_TYPE, state: _SessionState, *, word_id: int
) -> None:
    telegram_user = update.effective_user
    assert telegram_user is not None

    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
        if user is None:  # pragma: no cover - defensive
            logger.warning("Learn callback from unknown telegram_id=%s", telegram_user.id)
            return
        LearningService(session).enroll_word(user.id, word_id)

    state.learned += 1
    state.position += 1

    if state.position >= len(state.queue):
        text = learn_session_complete(learned=state.learned)
        await _edit(update, text, learn_session_end_keyboard())
        context.user_data.pop(_USER_DATA_KEY, None)
        return

    await _show_front(update, context)


async def _edit(update: Update, text: str, keyboard) -> None:
    query = update.callback_query
    assert query is not None
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


def _as_word_like(item: _QueueItem):
    """Adapts a `_QueueItem` to the small attribute surface `learn_texts`
    expects from a `Word` ORM instance, without importing SQLAlchemy here.
    """

    class _Level:
        value = item.level

    class _WordLike:
        word = item.word
        pronunciation = item.pronunciation
        meaning = item.meaning
        example = item.example
        synonyms = item.synonyms
        level = _Level() if item.level else None

    return _WordLike()
