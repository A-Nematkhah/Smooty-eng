"""Inline keyboard for the 📊 Progress dashboard."""

from __future__ import annotations

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import build_callback


def progress_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))]]
    )
