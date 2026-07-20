"""🎓 IELTS Mode section (Phase 7).

A dashboard + topic browser on top of the shared vocabulary table:
"Learn" and "Review" route into the same session mechanics as
📚 Learn English / 🔄 Review Words (Phases 4-5), just scoped to
`WordSource.IELTS` via `IELTSService`. Browsing by topic lists words
with an "add to my queue" button reusing the same `vocab:enroll`
callback `/search` results already use.
"""

from __future__ import annotations

from telegram import Update
from telegram.ext import ContextTypes

from app.bot.handlers.learn import on_ielts_learn_start
from app.bot.handlers.review import on_ielts_review_start
from app.bot.keyboards.ielts_keyboard import (
    ielts_back_keyboard,
    ielts_dashboard_keyboard,
    ielts_topics_keyboard,
)
from app.bot.keyboards.vocabulary_keyboard import search_result_keyboard
from app.bot.messages.ielts_texts import (
    NO_TOPICS_YET,
    NO_WORDS_FOR_TOPIC,
    ielts_dashboard_text,
    ielts_topic_header,
    ielts_topics_header,
    ielts_word_line,
)
from app.bot.states import parse_callback
from app.database.engine import session_scope
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.ielts_service import IELTSService


async def on_ielts_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, user: User) -> None:
    """Entry point from the main menu's "🎓 IELTS Mode" button."""
    query = update.callback_query
    assert query is not None
    await query.answer()
    await _render_dashboard(update, user)


async def on_ielts_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Dispatches the IELTS dashboard/topic-browser buttons."""
    query = update.callback_query
    telegram_user = update.effective_user
    assert query is not None and telegram_user is not None

    # maxsplit=2: an IELTS topic (parts[2]) can itself contain ':'
    # (e.g. "Book 2: Unit 18" from the book-import script), so it
    # must survive intact instead of being split further.
    parts = parse_callback(query.data, maxsplit=2)
    action = parts[1]

    with session_scope() as session:
        user = UserRepository(session).get_by_telegram_id(telegram_user.id)
    if user is None:  # pragma: no cover - defensive
        await query.answer("Please run /start first.", show_alert=True)
        return

    if action == "back":
        await query.answer()
        await _render_dashboard(update, user)
        return

    if action == "topics":
        await query.answer()
        await _render_topics(update)
        return

    if action == "topic":
        topic = parts[2]
        await query.answer()
        await _render_topic_words(update, context, topic)
        return

    if action == "learn":
        await on_ielts_learn_start(update, context, user)
        return

    if action == "review":
        await on_ielts_review_start(update, context, user)
        return

    await query.answer()  # pragma: no cover - defensive, keyboards never emit unknown actions


async def _render_dashboard(update: Update, user: User) -> None:
    query = update.callback_query
    assert query is not None

    with session_scope() as session:
        service = IELTSService(session)
        stats = service.stats(user)
        topics_count = len(service.list_topics())

    text = ielts_dashboard_text(stats, topics_count=topics_count)
    keyboard = ielts_dashboard_keyboard(
        new_words_count=max(stats.total_ielts_words - stats.enrolled, 0),
        due_review_count=stats.due_for_review,
    )
    await query.edit_message_text(text, reply_markup=keyboard, parse_mode="Markdown")


async def _render_topics(update: Update) -> None:
    query = update.callback_query
    assert query is not None

    with session_scope() as db_session:
        topics = IELTSService(db_session).list_topics()

    if not topics:
        await query.edit_message_text(NO_TOPICS_YET, reply_markup=ielts_back_keyboard())
        return

    await query.edit_message_text(
        ielts_topics_header(topics), reply_markup=ielts_topics_keyboard(topics), parse_mode="Markdown"
    )


async def _render_topic_words(update: Update, context: ContextTypes.DEFAULT_TYPE, topic: str) -> None:
    query = update.callback_query
    assert query is not None

    with session_scope() as session:
        words = list(IELTSService(session).words_by_topic(topic, limit=20))
        snapshots = [(w.id, w.word, w.meaning, w.ielts_band) for w in words]

    if not snapshots:
        await query.edit_message_text(NO_WORDS_FOR_TOPIC, reply_markup=ielts_back_keyboard())
        return

    await query.edit_message_text(
        ielts_topic_header(topic, len(snapshots)),
        reply_markup=ielts_back_keyboard(),
        parse_mode="Markdown",
    )

    chat_id = query.message.chat_id
    for word_id, word_text, meaning, band in snapshots:
        line = ielts_word_line(_WordLike(word_text, meaning, band))
        await context.bot.send_message(
            chat_id=chat_id,
            text=line,
            reply_markup=search_result_keyboard(word_id),
            parse_mode="Markdown",
        )


class _WordLike:
    """Small stand-in for `ielts_word_line`'s expected attribute surface,
    built from a plain tuple snapshot rather than a (possibly detached)
    ORM `Word` instance.
    """

    def __init__(self, word: str, meaning: str, ielts_band: str | None) -> None:
        self.word = word
        self.meaning = meaning
        self.ielts_band = ielts_band
