"""Thin convenience layer over WordRepository search.

Exists as its own module (rather than inlining into handlers) so
search ranking/behavior (e.g. prioritizing exact matches over
substring matches) can evolve independently of the DB query.
"""

from __future__ import annotations

from typing import Sequence

from app.models.word import Word
from app.repositories.word_repository import WordRepository


def search_vocabulary(word_repository: WordRepository, query: str, limit: int = 20) -> Sequence[Word]:
    """Search words by text or meaning, exact matches first."""
    results = list(word_repository.search(query, limit=limit))
    query_lower = query.strip().lower()
    results.sort(key=lambda w: (w.word.lower() != query_lower, w.word.lower()))
    return results
