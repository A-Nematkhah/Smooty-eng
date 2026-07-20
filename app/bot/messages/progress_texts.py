"""Text shown on the 📊 Progress dashboard."""

from __future__ import annotations

from app.services.progress_service import ProgressDashboard


def progress_overview(dashboard: ProgressDashboard) -> str:
    return (
        "📊 *Progress*\n\n"
        f"Total words: *{dashboard.total_words}*\n"
        f"Learned: *{dashboard.learned_words}*\n"
        f"Today: *{dashboard.reviewed_today}/{dashboard.daily_goal}*\n"
        f"Streak: *{dashboard.streak} days*\n"
        f"Accuracy: *{round(dashboard.accuracy * 100)}%*\n"
        f"XP: *{dashboard.xp}*"
    )
