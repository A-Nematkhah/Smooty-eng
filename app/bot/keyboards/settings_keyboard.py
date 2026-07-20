"""Inline keyboards for the ⚙ Settings menu and its sub-screens."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_SETTINGS, build_callback
from app.models.enums import LearningMode

_REMINDER_TIME_OPTIONS = ("07:00", "08:00", "09:00", "18:00", "20:00")

_MODE_LABELS = {
    LearningMode.STANDARD: "Standard",
    LearningMode.IELTS_FOCUS: "IELTS Focus",
}

_DAILY_GOAL_OPTIONS = (5, 10, 20)


def settings_overview_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton("📈 Level", callback_data=build_callback(CB_SETTINGS, "level"))],
        [InlineKeyboardButton("🎯 Learning goal", callback_data=build_callback(CB_SETTINGS, "goal"))],
        [InlineKeyboardButton("📅 Daily goal", callback_data=build_callback(CB_SETTINGS, "daily_goal"))],
        [InlineKeyboardButton("⏰ Reminder time", callback_data=build_callback(CB_SETTINGS, "reminder_time"))],
        [InlineKeyboardButton("🔀 Learning mode", callback_data=build_callback(CB_SETTINGS, "mode"))],
        [InlineKeyboardButton("⬅ Back to menu", callback_data=build_callback("menu", "main"))],
    ]
    return InlineKeyboardMarkup(rows)


def settings_level_keyboard() -> InlineKeyboardMarkup:
    from app.models.enums import CEFRLevel

    buttons = [
        InlineKeyboardButton(
            level.value, callback_data=build_callback(CB_SETTINGS, "level", level.value)
        )
        for level in CEFRLevel
    ]
    return InlineKeyboardMarkup([buttons[:3], buttons[3:], _back_row()])


def settings_goal_keyboard() -> InlineKeyboardMarkup:
    from app.models.enums import LearningGoal

    labels = {
        LearningGoal.GENERAL: "General English",
        LearningGoal.IELTS: "IELTS",
        LearningGoal.ACADEMIC: "Academic English",
        LearningGoal.BUSINESS: "Business English",
    }
    rows = [
        [InlineKeyboardButton(label, callback_data=build_callback(CB_SETTINGS, "goal", goal.value))]
        for goal, label in labels.items()
    ]
    rows.append(_back_row())
    return InlineKeyboardMarkup(rows)


def settings_daily_goal_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(
            f"{count} words", callback_data=build_callback(CB_SETTINGS, "daily_goal", str(count))
        )
        for count in _DAILY_GOAL_OPTIONS
    ]
    return InlineKeyboardMarkup([row, _back_row()])


def settings_reminder_time_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(time, callback_data=build_callback(CB_SETTINGS, "reminder_time", time))
        for time in _REMINDER_TIME_OPTIONS
    ]
    # Split into two rows of ~3 for readability.
    return InlineKeyboardMarkup([row[:3], row[3:], _back_row()])


def settings_mode_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=build_callback(CB_SETTINGS, "mode", mode.value))]
        for mode, label in _MODE_LABELS.items()
    ]
    rows.append(_back_row())
    return InlineKeyboardMarkup(rows)


def _back_row() -> list[InlineKeyboardButton]:
    return [InlineKeyboardButton("⬅ Back to settings", callback_data=build_callback(CB_SETTINGS, "back"))]
