"""
Import words from a "4000 Essential Words"-style flashcard export into
`data/ielts.json`.

The source format (as exported by several flashcard apps for this book
series) looks like:

    {
      "flashcard": [
        {
          "en": "Unit 1",
          "wordlist": [
            {
              "en": "alleviate",
              "pron": "[əˈliːvieit] v.",
              "desc": "To alleviate pain or suffering means ...",
              "exam": "She needed something to <strong>alleviate</strong> ...",
              "vi": "",
              ...
            }
          ]
        }
      ]
    }

This script:
  1. Strips the `<strong>`/`<br />` HTML and decodes HTML entities
     (`&rsquo;` etc.) out of `desc`/`exam`.
  2. Maps each word to `data/ielts.json`'s schema: `word`, `pronunciation`,
     `meaning`, `example`, `band` (unknown - not in this source, left
     null), `topic` (the unit title, e.g. "Unit 1" - the closest
     grouping this source provides), `synonyms` (not in this source).
  3. Merges into the existing `data/ielts.json`, skipping any word
     already present (case-insensitive match on `word`) so re-running
     this after adding more book files is safe.

Usage:
    python -m scripts.import_4000_essential_words /path/to/export.json

Note: this book series ("4000 Essential Words") ships as six separate
books of ~600-700 words each (~4000 words total across all six) - one
export file is one book, not the full 4000. Run this once per book
file to build up the full set.
"""

from __future__ import annotations

import argparse
import html
import json
import logging
import re
import sys
from pathlib import Path

from app.core.config import get_settings
from app.core.logging_config import configure_logging

logger = logging.getLogger(__name__)

_TAG_PATTERN = re.compile(r"</?strong>")
_WHITESPACE_PATTERN = re.compile(r"\s+")


def _clean_text(text: str | None) -> str | None:
    """Strip this source's HTML markup/entities down to plain text."""
    if not text:
        return None
    text = _TAG_PATTERN.sub("", text)
    text = text.replace("<br />", " ")
    text = html.unescape(text)
    text = _WHITESPACE_PATTERN.sub(" ", text).strip()
    return text or None


def convert(source: dict, *, book_label: str | None = None) -> list[dict]:
    """Convert one flashcard export into a list of ielts.json-shaped dicts.

    `book_label` (e.g. "Book 1") is prefixed onto each unit's topic.
    This matters because every book in the "4000 Essential Words"
    series reuses the same "Unit 1".."Unit 31" names - without a
    book label, topic browsing would silently merge six unrelated
    "Unit 1"s from six different books into one bucket.
    """
    entries: list[dict] = []
    for unit in source.get("flashcard", []):
        wordlist = unit.get("wordlist")
        if not wordlist:  # e.g. the trailing "Index" section has no wordlist
            continue
        unit_title = (unit.get("en") or "").strip() or None
        topic = f"{book_label}: {unit_title}" if book_label and unit_title else unit_title

        for raw_word in wordlist:
            word = (raw_word.get("en") or "").strip()
            meaning = _clean_text(raw_word.get("desc"))
            if not word or not meaning:
                logger.warning("Skipping entry with missing word/meaning: %r", raw_word)
                continue

            entries.append(
                {
                    "word": word,
                    "pronunciation": (raw_word.get("pron") or "").strip() or None,
                    "meaning": meaning,
                    "example": _clean_text(raw_word.get("exam")),
                    "band": None,
                    "topic": topic,
                    "synonyms": None,
                }
            )
    return entries


def merge_into_ielts_json(new_entries: list[dict], ielts_path: Path) -> tuple[int, int]:
    """Merge `new_entries` into `ielts_path`, skipping words already present.

    Returns (added_count, skipped_duplicate_count).
    """
    existing: list[dict] = []
    if ielts_path.exists():
        with ielts_path.open("r", encoding="utf-8") as file:
            existing = json.load(file)

    existing_words = {entry["word"].strip().lower() for entry in existing}

    added = 0
    skipped = 0
    for entry in new_entries:
        key = entry["word"].strip().lower()
        if key in existing_words:
            skipped += 1
            continue
        existing.append(entry)
        existing_words.add(key)
        added += 1

    with ielts_path.open("w", encoding="utf-8") as file:
        json.dump(existing, file, ensure_ascii=False, indent=2)
        file.write("\n")

    return added, skipped


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_file", type=Path, help="Path to the flashcard export JSON")
    parser.add_argument(
        "--book-label",
        default=None,
        help='Prefix for this book\'s topics, e.g. "Book 1" (recommended - see convert() docstring)',
    )
    args = parser.parse_args()

    if not args.source_file.exists():
        logger.error("File not found: %s", args.source_file)
        sys.exit(1)

    with args.source_file.open("r", encoding="utf-8") as file:
        source = json.load(file)

    entries = convert(source, book_label=args.book_label)
    logger.info("Converted %d words from %s", len(entries), args.source_file)

    ielts_path = get_settings().ielts_path
    added, skipped = merge_into_ielts_json(entries, ielts_path)
    logger.info("Merged into %s: %d added, %d already present (skipped)", ielts_path, added, skipped)
    logger.info("Now run: python -m scripts.seed_vocabulary")


if __name__ == "__main__":
    main()
