"""The persistent 📚 main menu keyboard.

Every section button routes to `menu:<section>` and is handled by
a single CallbackQueryHandler (see handlers/main_menu.py) that
dispatches to the right section handler and edits the message in
place - keeping the chat from filling up with a new message per tap.
"""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_MENU, build_callback

_SECTIONS = (
    ("learn", "📚 Learn English"),
    ("review", "🔄 Review Words"),
    ("daily_lesson", "🎯 Daily Lesson"),
    ("ielts", "🎓 IELTS Mode"),
    ("progress", "📊 Progress"),
    ("vocabulary", "⭐ My Vocabulary"),
    ("settings", "⚙ Settings"),
)


def main_menu_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=build_callback(CB_MENU, section))]
        for section, label in _SECTIONS
    ]
    return InlineKeyboardMarkup(rows)


def back_to_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Single "back" button used by every stub/placeholder section screen."""
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback(CB_MENU, "main"))]]
    )
