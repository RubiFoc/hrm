"""Department persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class Department(Base):
    """Department reference entity.

    Attributes:
        department_id: Unique department identifier.
        name: Human-readable department name.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "departments"
    __table_args__ = (Index("ix_departments_name", "name", unique=True),)

    department_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
