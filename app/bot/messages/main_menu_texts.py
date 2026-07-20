"""Text shown for the persistent main menu message."""

from app.models.user import User

MAIN_MENU_TITLE = "📚 *Main Menu*\nWhat would you like to do?"


def main_menu_with_stats(user: User) -> str:
    """Slightly richer main-menu header once a user exists.

    Real numbers (words due, streak, etc.) are wired in once the
    progress/card services exist (Phase 4-6); for now this just
    reflects the user's saved profile so the menu doesn't feel static.
    """
    return (
        f"📚 *Main Menu*\n"
        f"Level: {user.level.value} · Daily goal: {user.daily_goal} words\n\n"
        "What would you like to do?"
    )


PLACEHOLDER_COMING_SOON = (
    "🚧 This section isn't built yet - it arrives in an upcoming phase.\n"
    "Use the button below to go back to the main menu."
)
