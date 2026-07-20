"""Message text builders for 🎓 IELTS Mode."""

from __future__ import annotations

from app.models.word import Word
from app.services.ielts_service import IELTSStats

NO_TOPICS_YET = "No IELTS topics available yet - the IELTS vocabulary set is empty."
NO_WORDS_FOR_TOPIC = "No words found for that topic."


def ielts_dashboard_text(stats: IELTSStats, *, topics_count: int) -> str:
    return (
        "🎓 *IELTS Mode*\n\n"
        f"📇 IELTS words available: {stats.total_ielts_words}\n"
        f"📥 In your queue: {stats.enrolled}\n"
        f"✅ Learned: {stats.learned}\n"
        f"🔄 Due for review: {stats.due_for_review}\n"
        f"🗂 Topics: {topics_count}\n\n"
        "Pick where you'd like to start:"
    )


def ielts_topics_header(topics: list[str]) -> str:
    return "📚 *IELTS topics*\n\n" + "\n".join(f"• {topic}" for topic in topics)


def ielts_word_line(word: Word) -> str:
    band = f" · Band {word.ielts_band}" if word.ielts_band else ""
    return f"🔤 *{word.word}*{band}\n📖 {word.meaning}"


def ielts_topic_header(topic: str, count: int) -> str:
    return f"📚 *{topic}* ({count} words)"
