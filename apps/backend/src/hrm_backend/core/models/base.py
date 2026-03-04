"""Shared SQLAlchemy declarative base for backend domain models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class to be reused by all domain model packages."""
