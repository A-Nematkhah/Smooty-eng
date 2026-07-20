"""Domain-specific exceptions.

Repositories and services raise these instead of leaking raw
SQLAlchemy or Telegram exceptions up into handler code, so handlers
can catch one predictable exception hierarchy.
"""


class EnglishBotError(Exception):
    """Base class for all application-specific errors."""


class NotFoundError(EnglishBotError):
    """Raised when a requested entity does not exist."""


class UserNotFoundError(NotFoundError):
    """Raised when a user lookup (usually by telegram_id) fails."""


class WordNotFoundError(NotFoundError):
    """Raised when a word lookup fails."""


class CardNotFoundError(NotFoundError):
    """Raised when a scheduling card lookup fails."""


class DuplicateEntityError(EnglishBotError):
    """Raised when attempting to create an entity that already exists."""


class ValidationError(EnglishBotError):
    """Raised when input data fails a domain validation rule."""
