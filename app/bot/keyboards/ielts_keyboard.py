"""Inline keyboards for 🎓 IELTS Mode."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_IELTS, build_callback


def ielts_dashboard_keyboard(*, new_words_count: int, due_review_count: int) -> InlineKeyboardMarkup:
    rows = []
    if new_words_count:
        rows.append(
            [
                InlineKeyboardButton(
                    f"📖 Learn IELTS words ({new_words_count})",
                    callback_data=build_callback(CB_IELTS, "learn"),
                )
            ]
        )
    if due_review_count:
        rows.append(
            [
                InlineKeyboardButton(
                    f"🔄 Review IELTS due ({due_review_count})",
                    callback_data=build_callback(CB_IELTS, "review"),
                )
            ]
        )
    rows.append(
        [InlineKeyboardButton("📚 Browse by topic", callback_data=build_callback(CB_IELTS, "topics"))]
    )
    rows.append([InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))])
    return InlineKeyboardMarkup(rows)


def ielts_topics_keyboard(topics: list[str]) -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(topic, callback_data=build_callback(CB_IELTS, "topic", topic))]
        for topic in topics
    ]
    rows.append([InlineKeyboardButton("⬅ Back", callback_data=build_callback(CB_IELTS, "back"))])
    return InlineKeyboardMarkup(rows)


def ielts_back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back", callback_data=build_callback(CB_IELTS, "back"))]]
    )
