"""Shared SQLAlchemy declarative base.

Every ORM model in `app/models/` inherits from `Base`. Keeping this
in its own module (rather than defining it inside a model file)
avoids circular imports between models.
"""

from enum import Enum as PyEnum
from typing import Type

from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all ORM models."""


def sa_enum(enum_cls: Type[PyEnum]) -> SAEnum:
    """Build a SQLAlchemy Enum column type that stores `.value`, not `.name`.

    SQLAlchemy's Enum type stores each member's `.name` by default
    (e.g. "OXFORD_3000"), which would silently diverge from the
    lowercase `.value` strings ("oxford3000") documented in the
    Phase 1 schema and used throughout services/tests. This keeps
    raw DB rows human-readable and consistent with that schema.
    """
    return SAEnum(enum_cls, values_callable=lambda cls: [member.value for member in cls])
