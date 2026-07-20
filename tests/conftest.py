"""Shared pytest fixtures.

Tests run against an in-memory SQLite database, created fresh per
test function, so repository tests never touch the real
`data/english_bot.db` file and are fully isolated from each other.
"""

from __future__ import annotations

import os
from typing import Iterator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Point Settings at an in-memory DB and a dummy token *before* app modules
# that read settings at import time are imported.
os.environ.setdefault("TELEGRAM_BOT_TOKEN", "test-token")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from app.database.base import Base  # noqa: E402
from app import models  # noqa: E402,F401  (registers models on Base.metadata)


@pytest.fixture()
def db_session() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    session = session_factory()
    try:
        yield session
    finally:
        session.close()
