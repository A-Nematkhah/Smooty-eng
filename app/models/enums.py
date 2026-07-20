"""Shared enums for ORM models and services.

Kept as plain `str` Enums (not SQLAlchemy Enum types tied to a
specific dialect) so they serialize cleanly to JSON/Pydantic too,
and stay portable if we migrate from SQLite to Postgres.
"""

from enum import Enum


class CEFRLevel(str, Enum):
    A1 = "A1"
    A2 = "A2"
    B1 = "B1"
    B2 = "B2"
    C1 = "C1"


class LearningGoal(str, Enum):
    GENERAL = "general"
    IELTS = "ielts"
    ACADEMIC = "academic"
    BUSINESS = "business"


class LearningMode(str, Enum):
    """User-facing mode toggle, distinct from LearningGoal (set at onboarding).

    Lets a user temporarily switch focus (e.g. cram IELTS vocab for a
    week) without redoing onboarding.
    """

    STANDARD = "standard"
    IELTS_FOCUS = "ielts_focus"


class WordSource(str, Enum):
    OXFORD_3000 = "oxford3000"
    IELTS = "ielts"
    CUSTOM = "custom"


class CardState(str, Enum):
    """FSRS card lifecycle state."""

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class ReviewRating(str, Enum):
    """The four FSRS grading buttons shown to the user after each card."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"
