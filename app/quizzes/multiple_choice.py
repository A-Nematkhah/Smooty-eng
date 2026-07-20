"""Multiple-choice quiz question generation (Phase 6).

Only the "multiple choice" quiz type from the master spec is
implemented for now - meaning-matching/fill-the-blank/translation
variants are natural follow-ups but multiple choice alone already
covers the Daily Lesson's quiz requirement end-to-end.

Kept framework-agnostic (plain dataclasses in, plain dataclasses
out) so it's trivial to unit test - `DailyLessonService` is the only
caller and is the one that talks to `WordRepository`.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Sequence

from app.models.word import Word

_NUM_OPTIONS = 4


@dataclass(frozen=True)
class QuizQuestion:
    """One "What does X mean?" multiple-choice question."""

    word_id: int
    word_text: str
    options: tuple[str, ...]  # meanings, in display order
    correct_index: int


def build_multiple_choice_question(
    target_word: Word, distractor_pool: Sequence[Word], rng: random.Random | None = None
) -> QuizQuestion:
    """Build one question asking for `target_word`'s meaning.

    `distractor_pool` should already exclude `target_word` itself;
    if it has fewer than `_NUM_OPTIONS - 1` entries, the question
    simply ships with fewer wrong options rather than failing - a
    thin personal vocabulary table shouldn't crash the quiz.
    """
    rng = rng or random.Random()

    distractor_meanings = [w.meaning for w in distractor_pool if w.meaning != target_word.meaning]
    rng.shuffle(distractor_meanings)
    wrong_options = distractor_meanings[: _NUM_OPTIONS - 1]

    options = [target_word.meaning, *wrong_options]
    rng.shuffle(options)
    correct_index = options.index(target_word.meaning)

    return QuizQuestion(
        word_id=target_word.id,
        word_text=target_word.word,
        options=tuple(options),
        correct_index=correct_index,
    )
