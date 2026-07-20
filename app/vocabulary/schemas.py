"""Pydantic schemas for the raw vocabulary JSON files.

Validating `data/oxford3000.json` / `data/ielts.json` at load time
(rather than trusting the JSON blindly) catches data-entry mistakes
before they become confusing bugs three layers away in the quiz
engine.
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.models.enums import CEFRLevel


class OxfordWordEntry(BaseModel):
    """One entry in `data/oxford3000.json`."""

    word: str
    pronunciation: Optional[str] = None
    meaning: str
    example: Optional[str] = None
    level: Optional[CEFRLevel] = None
    category: Optional[str] = None

    @field_validator("word", "meaning")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()


class IeltsWordEntry(BaseModel):
    """One entry in `data/ielts.json`."""

    word: str
    pronunciation: Optional[str] = None
    meaning: str
    example: Optional[str] = None
    band: Optional[str] = Field(default=None, description='e.g. "8+"')
    topic: Optional[str] = None
    synonyms: Optional[list[str]] = None

    @field_validator("word", "meaning")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("must not be blank")
        return value.strip()
