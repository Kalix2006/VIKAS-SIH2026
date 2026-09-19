"""SQLAlchemy declarative base for all ORM models.

All models should inherit from Base defined here.
Import this in models/ and in alembic/env.py for migration autogeneration.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass
