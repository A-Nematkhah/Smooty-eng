"""Inline keyboards for the 📚 Learn English session."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_LEARN, build_callback


def learn_reveal_keyboard(word_id: int) -> InlineKeyboardMarkup:
    """Shown on the "front" of a new word - reveal its meaning."""
    rows = [
        [
            InlineKeyboardButton(
                "👁 Show meaning", callback_data=build_callback(CB_LEARN, "reveal", str(word_id))
            )
        ],
        [InlineKeyboardButton("⬅ End session", callback_data=build_callback("menu", "main"))],
    ]
    return InlineKeyboardMarkup(rows)


def learn_enroll_keyboard(word_id: int) -> InlineKeyboardMarkup:
    """Shown on the "back" - add the word to the FSRS review queue and move on."""
    rows = [
        [
            InlineKeyboardButton(
                "➕ Got it - add to reviews",
                callback_data=build_callback(CB_LEARN, "enroll", str(word_id)),
            )
        ],
        [InlineKeyboardButton("⬅ End session", callback_data=build_callback("menu", "main"))],
    ]
    return InlineKeyboardMarkup(rows)


def learn_session_end_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))]]
    )
