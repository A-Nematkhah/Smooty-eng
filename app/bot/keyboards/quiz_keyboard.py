"""Inline keyboards for the 📝 quiz mini-flow (part of 🎯 Daily Lesson)."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_QUIZ, build_callback

_OPTION_LETTERS = ("A", "B", "C", "D")


def quiz_start_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("📝 Start quiz", callback_data=build_callback(CB_QUIZ, "start"))],
            [InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))],
        ]
    )


def quiz_question_keyboard(position: int, options: tuple[str, ...]) -> InlineKeyboardMarkup:
    rows = [
        [
            InlineKeyboardButton(
                f"{_OPTION_LETTERS[i]}) {option}",
                callback_data=build_callback(CB_QUIZ, "answer", str(position), str(i)),
            )
        ]
        for i, option in enumerate(options)
    ]
    return InlineKeyboardMarkup(rows)


def quiz_next_keyboard(position: int, *, is_last: bool) -> InlineKeyboardMarkup:
    label = "🏁 Finish" if is_last else "▶ Next question"
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton(label, callback_data=build_callback(CB_QUIZ, "next", str(position)))]]
    )


def quiz_complete_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))]]
    )
