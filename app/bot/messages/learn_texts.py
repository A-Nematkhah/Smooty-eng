"""Message text builders for the 📚 Learn English session."""

from __future__ import annotations

from app.models.word import Word

NO_NEW_WORDS = (
    "🎉 *No new words left to learn right now.*\n\n"
    "You've started learning every word currently in your vocabulary "
    "database. Add your own with `/addword word | meaning | example`, "
    "or check 🔄 Review Words to keep practicing what you've already learned."
)


def learn_progress_label(position: int, total: int) -> str:
    return f"Word {position} of {total}"


def learn_card_front(word: Word, *, position: int, total: int) -> str:
    pronunciation = f" _/{word.pronunciation}/_" if word.pronunciation else ""
    level = f" · {word.level.value}" if word.level else ""
    return (
        f"{learn_progress_label(position, total)}{level}\n\n"
        f"🔤 *{word.word}*{pronunciation}\n\n"
        "Try to guess the meaning, then tap below to check."
    )


def learn_card_back(word: Word, *, position: int, total: int) -> str:
    pronunciation = f" _/{word.pronunciation}/_" if word.pronunciation else ""
    lines = [
        f"{learn_progress_label(position, total)}\n",
        f"🔤 *{word.word}*{pronunciation}",
        f"📖 {word.meaning}",
    ]
    if word.example:
        lines.append(f"💬 _{word.example}_")
    if word.synonyms:
        lines.append(f"🔁 Synonyms: {word.synonyms}")
    lines.append("\nAdd it to your review queue to start practicing it with spaced repetition.")
    return "\n".join(lines)


def learn_session_complete(*, learned: int) -> str:
    return (
        "🏁 *Learning session complete!*\n\n"
        f"New words added to your review queue: {learned}\n\n"
        "They'll show up in 🔄 Review Words as they come due."
    )
