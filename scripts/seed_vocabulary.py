"""
Idempotent database seed script.

Run this once after cloning the project (and again any time
`data/oxford3000.json` or `data/ielts.json` changes):

    python -m scripts.seed_vocabulary

It:
  1. Creates all tables if they don't exist yet (`init_db`).
  2. Loads + validates the JSON vocabulary files.
  3. Inserts any word not already present (matched by word text + source),
     so re-running after adding new entries to the JSON files only
     inserts the new ones instead of duplicating existing rows.
"""

from __future__ import annotations

import logging

from app.core.config import get_settings
from app.core.logging_config import configure_logging
from app.database.engine import init_db, session_scope
from app.repositories.word_repository import WordRepository
from app.vocabulary.oxford_loader import load_ielts, load_oxford3000

logger = logging.getLogger(__name__)


def seed() -> None:
    configure_logging()
    settings = get_settings()

    logger.info("Ensuring database tables exist...")
    init_db()

    oxford_words = load_oxford3000(settings.oxford3000_path)
    ielts_words = load_ielts(settings.ielts_path)
    all_words = oxford_words + ielts_words

    with session_scope() as session:
        repository = WordRepository(session)

        # Build a set of (word_text, source) already in the DB, per source
        # present in the incoming data, so re-running this script is safe.
        existing_keys: set[tuple[str, str]] = set()
        for source in {entry["source"] for entry in all_words}:
            for word in repository.list_by_source(source):
                existing_keys.add((word.word.lower(), word.source))

        new_words = [
            entry for entry in all_words if (entry["word"].lower(), entry["source"]) not in existing_keys
        ]

        if not new_words:
            logger.info("No new words to insert - vocabulary is already up to date.")
            return

        repository.bulk_create(new_words)
        logger.info(
            "Inserted %d new words (%d already existed).",
            len(new_words),
            len(all_words) - len(new_words),
        )


if __name__ == "__main__":
    seed()
