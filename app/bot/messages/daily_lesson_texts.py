"""Message text builder for the 🎯 Daily Lesson dashboard."""

from __future__ import annotations

from app.services.daily_lesson_service import DailyLessonPlan


def daily_lesson_overview(plan: DailyLessonPlan, *, day_number: int) -> str:
    lines = [f"🎯 *Daily Lesson - Day {day_number}*\n"]

    if plan.new_words:
        lines.append(f"📖 New words ready to learn: {len(plan.new_words)}")
    else:
        lines.append("📖 New words: none left in your vocabulary database right now")

    lines.append(f"🔄 Reviews due: {plan.due_review_count}")
    lines.append(f"📝 Quiz questions ready: {len(plan.quiz_questions)}")
    lines.append(f"\n✅ Reviews completed today: {plan.reviews_done_today}/{plan.daily_goal}")

    if not plan.new_words and not plan.due_review_count and not plan.quiz_questions:
        lines.append(
            "\n🎉 You're all caught up! Add more words with `/addword` or check back later."
        )
    else:
        lines.append("\nPick where you'd like to start:")

    return "\n".join(lines)
