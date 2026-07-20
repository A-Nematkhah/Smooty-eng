"""
Entrypoint for running the bot.

Usage:
    python main.py

Requires TELEGRAM_BOT_TOKEN to be set (in `.env` or the environment).
Run `python -m scripts.seed_vocabulary` at least once beforehand so
the `words` table isn't empty when Learn/Review/Daily Lesson/IELTS
start reading from it.
"""

from __future__ import annotations

import logging

from app.bot.bot_app import build_application
from app.core.logging_config import configure_logging
from app.database.engine import init_db
from app.scheduler.scheduler_setup import register_jobs

logger = logging.getLogger(__name__)


def main() -> None:
    configure_logging()
    logger.info("Ensuring database tables exist...")
    init_db()

    logger.info("Building Telegram application...")
    application = build_application()

    logger.info("Registering scheduled jobs (reminders)...")
    register_jobs(application)

    logger.info("Starting polling...")
    application.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
