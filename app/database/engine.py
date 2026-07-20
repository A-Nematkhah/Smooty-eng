"""
Engine and session management.

This is the *only* place `create_engine` is called. Everything else
(repositories, services, seed scripts) asks for a session via
`session_scope()` or the injected `Session` factory - never imports
`engine` directly - so swapping SQLite for Postgres later is a
one-line change to `Settings.database_url`.
"""

from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.database.base import Base


def _make_engine() -> Engine:
    settings = get_settings()
    connect_args = {}
    if settings.database_url.startswith("sqlite"):
        # Needed because python-telegram-bot's async handlers may touch
        # the same connection from different asyncio tasks on one thread.
        connect_args["check_same_thread"] = False

    return create_engine(
        settings.database_url,
        echo=settings.sql_echo,
        connect_args=connect_args,
        future=True,
    )


# Module-level singletons - created once, reused for the process lifetime.
engine: Engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """Create all tables that don't exist yet.

    Safe to call on every startup - `create_all` is a no-op for
    tables that already exist. For real schema changes later,
    switch to Alembic migrations instead of relying on this.
    """
    # Import models so they're registered on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope() -> Iterator[Session]:
    """Provide a transactional session as a context manager.

    Commits on success, rolls back on any exception, always closes.
    Usage:
        with session_scope() as session:
            repo = UserRepository(session)
            repo.create(...)
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
