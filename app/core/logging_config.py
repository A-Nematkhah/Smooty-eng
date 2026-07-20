"""Logging setup for the whole application.

Call `configure_logging()` once, at process startup (in the bot's
entrypoint), before any other module logs anything.
"""

import logging
import sys

from app.core.config import get_settings


def configure_logging() -> None:
    """Configure root logging handlers and level from Settings.log_level."""
    settings = get_settings()

    logging.basicConfig(
        level=getattr(logging, settings.log_level.upper(), logging.INFO),
        format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )

    # Quiet down noisy third-party loggers unless we're debugging.
    if settings.log_level.upper() != "DEBUG":
        logging.getLogger("httpx").setLevel(logging.WARNING)
        logging.getLogger("apscheduler").setLevel(logging.WARNING)
        logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
