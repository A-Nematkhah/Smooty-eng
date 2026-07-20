"""Message text builders for ⭐ My Vocabulary, `/addword`, and `/search`."""

from __future__ import annotations

from typing import Sequence

from app.models.word import Word

ADDWORD_USAGE = (
    "✏️ *Add a custom word*\n\n"
    "Usage:\n"
    "`/addword word | meaning | example`\n\n"
    "The example is optional. For instance:\n"
    "`/addword abandon | ترک کردن | He abandoned his old car.`"
)

SEARCH_USAGE = "🔍 Usage: `/search <word or meaning>` (also works as `/find`)."

NO_SEARCH_RESULTS = "No matching words found in your vocabulary database."


def addword_success(word: Word) -> str:
    example = f"\n💬 _{word.example}_" if word.example else ""
    return (
        f"✅ Added *{word.word}* to your custom vocabulary and review queue.\n\n"
        f"📖 {word.meaning}{example}"
    )


def search_results_header(query: str, count: int) -> str:
    return f"🔍 *Results for* “{query}” ({count})"


def search_result_line(word: Word) -> str:
    pronunciation = f" /{word.pronunciation}/" if word.pronunciation else ""
    return f"🔤 *{word.word}*{pronunciation}\n📖 {word.meaning}"


def vocabulary_overview(
    *,
    favorites: Sequence[tuple[Word, object]],
    difficult: Sequence[tuple[Word, object]],
    total_learning: int,
    total_learned: int,
) -> str:
    lines = [
        "⭐ *My Vocabulary*\n",
        f"📇 Words in your queue: {total_learning}",
        f"✅ Words learned (graduated): {total_learned}\n",
    ]

    lines.append("*⭐ Favorites*")
    if favorites:
        lines.extend(f"• {word.word} - {word.meaning}" for word, _card in favorites)
    else:
        lines.append("_None yet - use ⭐ in a review to mark favorites._")

    lines.append("\n*🧗 Most difficult*")
    if difficult:
        lines.extend(f"• {word.word} - {word.meaning}" for word, _card in difficult)
    else:
        lines.append("_Not enough review history yet._")

    lines.append(
        "\nAdd your own words with `/addword`, or look one up with `/search`."
    )
    return "\n".join(lines)
