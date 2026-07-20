"""Inline keyboards for the 🔄 Review Words session."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_REVIEW, CB_VOCAB, build_callback
from app.models.enums import ReviewRating

_RATING_LABELS = {
    ReviewRating.AGAIN: "❌ Again",
    ReviewRating.HARD: "😐 Hard",
    ReviewRating.GOOD: "✅ Good",
    ReviewRating.EASY: "⭐ Easy",
}


def review_reveal_keyboard(card_id: int) -> InlineKeyboardMarkup:
    """Shown on the "front" of a card - reveal the meaning before rating."""
    rows = [
        [
            InlineKeyboardButton(
                "👁 Show meaning", callback_data=build_callback(CB_REVIEW, "reveal", str(card_id))
            )
        ],
        [InlineKeyboardButton("⬅ End session", callback_data=build_callback("menu", "main"))],
    ]
    return InlineKeyboardMarkup(rows)


def review_rating_keyboard(card_id: int) -> InlineKeyboardMarkup:
    """Shown on the "back" of a card - the four FSRS grading buttons,
    plus a favorite toggle so a user can star a word mid-review
    without leaving the session. The toggle's current state is
    confirmed via a toast (see `on_vocabulary_callback`) rather than
    changing this button's label, so the review keyboard never needs
    to be rebuilt just to reflect a favorite flip.
    """
    rating_row = [
        InlineKeyboardButton(
            label, callback_data=build_callback(CB_REVIEW, "rate", str(card_id), rating.value)
        )
        for rating, label in _RATING_LABELS.items()
    ]
    favorite_row = [
        InlineKeyboardButton(
            "⭐ Toggle favorite", callback_data=build_callback(CB_VOCAB, "fav", str(card_id))
        )
    ]
    return InlineKeyboardMarkup([rating_row, favorite_row])


def review_session_end_keyboard() -> InlineKeyboardMarkup:
    """Shown after the last due card or when there's nothing to review."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))]]
    )
