"""Text shown in the ⚙ Settings menu and its sub-screens."""

from app.models.user import User


def settings_overview(user: User) -> str:
    return (
        "⚙ *Settings*\n\n"
        f"Level: *{user.level.value}*\n"
        f"Learning goal: *{user.learning_goal.value}*\n"
        f"Daily goal: *{user.daily_goal} words*\n"
        f"Reminder time: *{user.reminder_time or 'not set'}*\n"
        f"Learning mode: *{user.learning_mode.value}*\n\n"
        "What would you like to change?"
    )


ASK_NEW_LEVEL = "📈 *Choose your new level:*"
ASK_NEW_GOAL = "🎯 *Choose your new learning goal:*"
ASK_NEW_DAILY_GOAL = "📅 *Choose your new daily word target:*"
ASK_NEW_REMINDER_TIME = "⏰ *Choose a daily reminder time:*"
ASK_NEW_MODE = "🔀 *Choose a learning mode:*"

SETTING_SAVED = "✅ Saved."
