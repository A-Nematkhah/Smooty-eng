"""Message text builders for the 📝 quiz mini-flow."""

from __future__ import annotations

from app.quizzes.multiple_choice import QuizQuestion

NO_QUIZ_AVAILABLE = (
    "📝 Not enough words in your vocabulary yet to build a quiz.\n"
    "Learn a few words first, then come back!"
)

_OPTION_LETTERS = ("A", "B", "C", "D")


def quiz_question_text(question: QuizQuestion, *, position: int, total: int) -> str:
    lines = [f"📝 Question {position} of {total}\n", f"What does *{question.word_text}* mean?\n"]
    lines.extend(
        f"{_OPTION_LETTERS[i]}) {option}" for i, option in enumerate(question.options)
    )
    return "\n".join(lines)


def quiz_feedback_text(question: QuizQuestion, *, chosen_index: int) -> str:
    correct_letter = _OPTION_LETTERS[question.correct_index]
    correct_meaning = question.options[question.correct_index]

    if chosen_index == question.correct_index:
        return f"✅ *Correct!* {question.word_text} = {correct_meaning}"
    chosen_meaning = question.options[chosen_index]
    return (
        f"❌ *Not quite.* You picked: {chosen_meaning}\n"
        f"The correct answer was {correct_letter}) *{correct_meaning}*"
    )


def quiz_complete_text(*, score: int, total: int, xp_awarded: int) -> str:
    accuracy = round(100 * score / total) if total else 0
    return (
        "🏁 *Quiz complete!*\n\n"
        f"Score: {score}/{total} ({accuracy}%)\n"
        f"XP earned: +{xp_awarded}\n\n"
        "Nice work - see you at the next Daily Lesson."
    )
