"""Tests for `app/quizzes/multiple_choice.py` - pure logic, no DB."""

from __future__ import annotations

import random

from app.models.enums import CEFRLevel, WordSource
from app.models.word import Word
from app.quizzes.multiple_choice import build_multiple_choice_question


def _word(id_, word, meaning, level=CEFRLevel.B1):
    return Word(
        id=id_, word=word, meaning=meaning, level=level, source=WordSource.OXFORD_3000
    )


def test_question_has_correct_answer_among_options():
    target = _word(1, "accurate", "دقیق")
    distractors = [_word(i, f"word{i}", f"meaning{i}") for i in range(2, 6)]

    question = build_multiple_choice_question(target, distractors, rng=random.Random(0))

    assert question.word_id == 1
    assert question.word_text == "accurate"
    assert question.options[question.correct_index] == "دقیق"
    assert len(question.options) == 4
    assert len(set(question.options)) == len(question.options)  # no duplicate options


def test_question_degrades_gracefully_with_few_distractors():
    target = _word(1, "accurate", "دقیق")
    distractors = [_word(2, "word2", "meaning2")]

    question = build_multiple_choice_question(target, distractors, rng=random.Random(0))

    assert len(question.options) == 2
    assert question.options[question.correct_index] == "دقیق"


def test_question_with_no_distractors_still_has_the_correct_answer():
    target = _word(1, "accurate", "دقیق")

    question = build_multiple_choice_question(target, [], rng=random.Random(0))

    assert question.options == ("دقیق",)
    assert question.correct_index == 0


def test_distractors_sharing_the_target_meaning_are_excluded():
    target = _word(1, "big", "بزرگ")
    distractors = [_word(2, "large", "بزرگ"), _word(3, "small", "کوچک")]

    question = build_multiple_choice_question(target, distractors, rng=random.Random(0))

    assert question.options.count("بزرگ") == 1
