"""Inline keyboards for ⭐ My Vocabulary and `/search` results."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_VOCAB, build_callback


def vocabulary_overview_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))]]
    )


def search_result_keyboard(word_id: int) -> InlineKeyboardMarkup:
    """One "add to my queue" button per search result message."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    "➕ Add to my queue",
                    callback_data=build_callback(CB_VOCAB, "enroll", str(word_id)),
                )
            ]
        ]
    )
