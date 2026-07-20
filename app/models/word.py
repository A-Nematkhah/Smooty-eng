"""Word model - shared vocabulary table for Oxford 3000, IELTS, and
user-added custom words.

Per the Phase 1 architecture decision, IELTS-specific fields
(band, topic, synonyms) are added as nullable columns here rather
than a separate `ielts_words` table, so Learn/Review/Quiz flows only
ever need one query path regardless of word source.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, sa_enum
from app.models.enums import CEFRLevel, WordSource

if TYPE_CHECKING:
    from app.models.card import Card


class Word(Base):
    """A single vocabulary entry."""

    __tablename__ = "words"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)

    word: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    pronunciation: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, comment="IPA")
    meaning: Mapped[str] = mapped_column(Text, nullable=False)
    example: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    level: Mapped[Optional[CEFRLevel]] = mapped_column(sa_enum(CEFRLevel), nullable=True)
    category: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source: Mapped[WordSource] = mapped_column(sa_enum(WordSource), nullable=False)

    # --- IELTS-specific, nullable for non-IELTS words ---
    ielts_band: Mapped[Optional[str]] = mapped_column(
        String(8), nullable=True, comment='e.g. "8+"'
    )
    ielts_topic: Mapped[Optional[str]] = mapped_column(
        String(64), nullable=True, comment="Environment / Technology / Education / ..."
    )
    synonyms: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, comment="Comma-separated synonyms"
    )

    # --- relationships ---
    cards: Mapped[List["Card"]] = relationship(back_populates="word")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Word id={self.id} word={self.word!r} source={self.source}>"
