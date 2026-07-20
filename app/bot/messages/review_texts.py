"""Message text builders for the 🔄 Review Words session.

Kept as pure string-building functions (no Telegram objects) so
they're easy to unit test and reuse - same pattern as
`settings_texts.py` / `main_menu_texts.py` from Phase 3.
"""

from __future__ import annotations

from app.models.word import Word

NO_DUE_WORDS = (
    "🎉 *Nothing to review right now.*\n\n"
    "You're all caught up - come back later, or head to 📚 Learn English "
    "to add new words to your queue."
)


def review_progress_label(position: int, total: int) -> str:
    return f"Card {position} of {total}"


def review_card_front(word: Word, *, position: int, total: int) -> str:
    pronunciation = f" _/{word.pronunciation}/_" if word.pronunciation else ""
    return (
        f"{review_progress_label(position, total)}\n\n"
        f"🔤 *{word.word}*{pronunciation}\n\n"
        "What does this word mean? Tap below when you're ready to check."
    )


def review_card_back(word: Word, *, position: int, total: int) -> str:
    pronunciation = f" _/{word.pronunciation}/_" if word.pronunciation else ""
    lines = [
        f"{review_progress_label(position, total)}\n",
        f"🔤 *{word.word}*{pronunciation}",
        f"📖 {word.meaning}",
    ]
    if word.example:
        lines.append(f"💬 _{word.example}_")
    lines.append("\nHow well did you remember it?")
    return "\n".join(lines)


def review_session_complete(*, reviewed: int, xp_awarded: int, streak: int) -> str:
    return (
        "🏁 *Review session complete!*\n\n"
        f"Words reviewed: {reviewed}\n"
        f"XP earned: +{xp_awarded}\n"
        f"🔥 Streak: {streak} day(s)\n\n"
        "Nice work - see you at the next session."
    )
