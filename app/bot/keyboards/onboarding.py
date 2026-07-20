"""Inline keyboards for the /start onboarding conversation."""

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from app.bot.states import CB_ONBOARDING_DAILY_GOAL, CB_ONBOARDING_GOAL, CB_ONBOARDING_LEVEL, build_callback
from app.models.enums import CEFRLevel, LearningGoal

_GOAL_LABELS = {
    LearningGoal.GENERAL: "General English",
    LearningGoal.IELTS: "IELTS",
    LearningGoal.ACADEMIC: "Academic English",
    LearningGoal.BUSINESS: "Business English",
}

_DAILY_GOAL_OPTIONS = (5, 10, 20)


def level_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        InlineKeyboardButton(level.value, callback_data=build_callback(CB_ONBOARDING_LEVEL, level.value))
        for level in CEFRLevel
    ]
    # 5 levels -> put 3 on the first row, 2 on the second, for a tidy layout.
    rows = [buttons[:3], buttons[3:]]
    return InlineKeyboardMarkup(rows)


def goal_keyboard() -> InlineKeyboardMarkup:
    rows = [
        [InlineKeyboardButton(label, callback_data=build_callback(CB_ONBOARDING_GOAL, goal.value))]
        for goal, label in _GOAL_LABELS.items()
    ]
    return InlineKeyboardMarkup(rows)


def daily_goal_keyboard() -> InlineKeyboardMarkup:
    row = [
        InlineKeyboardButton(
            f"{count} words", callback_data=build_callback(CB_ONBOARDING_DAILY_GOAL, str(count))
        )
        for count in _DAILY_GOAL_OPTIONS
    ]
    return InlineKeyboardMarkup([row])
