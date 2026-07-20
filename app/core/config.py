"""
Application configuration.

Centralizes all environment-driven configuration behind a single,
type-validated Settings object. Nothing else in the codebase should
call `os.environ` directly - import `get_settings()` instead so
config is validated once, at startup, rather than failing deep
inside a handler.
"""

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = english_bot/ (two levels up from this file: app/core/config.py)
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Strongly-typed application settings.

    Values are read from environment variables / a `.env` file at the
    project root. See `.env.example` for the full list of supported
    variables and their defaults.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Telegram ---
    telegram_bot_token: str = Field(
        ...,
        description="Bot token issued by @BotFather. Required.",
    )

    # --- Database ---
    database_url: str = Field(
        default=f"sqlite:///{PROJECT_ROOT / 'data' / 'english_bot.db'}",
        description="SQLAlchemy database URL. Defaults to a local SQLite file.",
    )
    sql_echo: bool = Field(
        default=False,
        description="If true, SQLAlchemy logs every executed statement (debug only).",
    )

    # --- Vocabulary data ---
    oxford3000_path: Path = Field(
        default=PROJECT_ROOT / "data" / "oxford3000.json",
    )
    ielts_path: Path = Field(
        default=PROJECT_ROOT / "data" / "ielts.json",
    )

    # --- Scheduler / reminders ---
    default_reminder_time: str = Field(
        default="09:00",
        description="HH:MM default reminder time for new users, in the server's local time.",
    )
    scheduler_timezone: str = Field(
        default="UTC",
        description="Timezone APScheduler uses to fire daily jobs.",
    )

    # --- Logging ---
    log_level: str = Field(default="INFO")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """
    Return the process-wide Settings singleton.

    Cached so `.env` is parsed and validated exactly once per process,
    while still being trivially mockable in tests via
    `get_settings.cache_clear()`.
    """
    return Settings()
