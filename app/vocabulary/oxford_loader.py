"""Loads and validates the JSON vocabulary data files.

This module only reads/validates JSON into plain dicts shaped for
`WordRepository.bulk_create`. It never touches the database itself -
that's the seed script's job (`scripts/seed_vocabulary.py`) - which
keeps this module trivially unit-testable without a DB.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from app.core.exceptions import ValidationError
from app.models.enums import WordSource
from app.vocabulary.schemas import IeltsWordEntry, OxfordWordEntry

logger = logging.getLogger(__name__)


def load_oxford3000(path: Path) -> list[dict]:
    """Load and validate `data/oxford3000.json`.

    Returns a list of dicts ready for `WordRepository.bulk_create`.
    Raises `ValidationError` (with the offending entry's index) on
    the first malformed record, rather than silently skipping bad
    data.
    """
    raw_entries = _read_json_array(path)
    words: list[dict] = []

    for index, raw_entry in enumerate(raw_entries):
        try:
            entry = OxfordWordEntry.model_validate(raw_entry)
        except PydanticValidationError as exc:
            raise ValidationError(f"oxford3000.json entry #{index} is invalid: {exc}") from exc

        words.append(
            {
                "word": entry.word,
                "pronunciation": entry.pronunciation,
                "meaning": entry.meaning,
                "example": entry.example,
                "level": entry.level,
                "category": entry.category,
                "source": WordSource.OXFORD_3000,
            }
        )

    logger.info("Loaded %d words from %s", len(words), path)
    return words


def load_ielts(path: Path) -> list[dict]:
    """Load and validate `data/ielts.json`."""
    raw_entries = _read_json_array(path)
    words: list[dict] = []

    for index, raw_entry in enumerate(raw_entries):
        try:
            entry = IeltsWordEntry.model_validate(raw_entry)
        except PydanticValidationError as exc:
            raise ValidationError(f"ielts.json entry #{index} is invalid: {exc}") from exc

        words.append(
            {
                "word": entry.word,
                "pronunciation": entry.pronunciation,
                "meaning": entry.meaning,
                "example": entry.example,
                "level": None,
                "category": entry.topic,
                "source": WordSource.IELTS,
                "ielts_band": entry.band,
                "ielts_topic": entry.topic,
                "synonyms": ", ".join(entry.synonyms) if entry.synonyms else None,
            }
        )

    logger.info("Loaded %d words from %s", len(words), path)
    return words


def _read_json_array(path: Path) -> list[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Vocabulary data file not found: {path}")
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, list):
        raise ValidationError(f"{path} must contain a JSON array at the top level")
    return data
