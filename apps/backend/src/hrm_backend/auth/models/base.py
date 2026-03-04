"""SQLAlchemy declarative base for auth domain models.

This metadata root is used by Alembic bootstrap in the backend package.
"""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for auth database models."""
