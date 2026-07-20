"""Inline keyboard for the 🎯 Daily Lesson dashboard.

Reuses the existing 📚 Learn / 🔄 Review main-menu callback data
directly - tapping "Learn new words" from here is indistinguishable
from tapping it on the main menu, so no new routing is needed for
those two buttons; only the quiz mini-flow (Phase 6) is new.
"""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_MENU, CB_QUIZ, build_callback


def daily_lesson_keyboard(
    *, new_words_count: int, due_review_count: int, quiz_count: int
) -> InlineKeyboardMarkup:
    rows = []
    if new_words_count:
        rows.append(
            [
                InlineKeyboardButton(
                    f"📖 Learn new words ({new_words_count})",
                    callback_data=build_callback(CB_MENU, "learn"),
                )
            ]
        )
    if due_review_count:
        rows.append(
            [
                InlineKeyboardButton(
                    f"🔄 Review due ({due_review_count})",
                    callback_data=build_callback(CB_MENU, "review"),
                )
            ]
        )
    if quiz_count:
        rows.append(
            [
                InlineKeyboardButton(
                    f"📝 Take quiz ({quiz_count} questions)",
                    callback_data=build_callback(CB_QUIZ, "start"),
                )
            ]
        )
    rows.append([InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))])
    return InlineKeyboardMarkup(rows)
