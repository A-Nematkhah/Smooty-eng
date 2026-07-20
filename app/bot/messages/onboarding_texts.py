"""Text shown during the /start onboarding conversation.

Kept as plain functions returning strings (not f-strings scattered
in handlers) so copywriting can be tweaked without touching
handler logic, and so the same text is reusable from tests.
"""

WELCOME = (
    "👋 *Welcome to your personal English coach!*\n\n"
    "I'll help you learn and remember English vocabulary using "
    "spaced repetition - the same technique behind Anki.\n\n"
    "Let's set a few things up. This takes less than a minute."
)

ASK_LEVEL = "📈 *What's your English level?*"

ASK_GOAL = "🎯 *What's your main learning goal?*"

ASK_DAILY_GOAL = "📅 *How many new words per day would you like to learn?*"


def onboarding_complete(level: str, learning_goal: str, daily_goal: int) -> str:
    return (
        "✅ *All set!*\n\n"
        f"Level: *{level}*\n"
        f"Goal: *{learning_goal}*\n"
        f"Daily target: *{daily_goal} words*\n\n"
        "You can change any of this later in ⚙ Settings.\n"
        "Here's your main menu 👇"
    )


WELCOME_BACK = "👋 *Welcome back!*"
