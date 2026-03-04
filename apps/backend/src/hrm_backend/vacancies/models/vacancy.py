"""Vacancy persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class Vacancy(Base):
    """Recruitment vacancy entity.

    Attributes:
        vacancy_id: Unique vacancy identifier.
        title: Vacancy title.
        description: Vacancy description.
        department: Department name.
        status: Vacancy lifecycle status.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "vacancies"
    __table_args__ = (
        Index("ix_vacancies_status", "status"),
        Index("ix_vacancies_created_at", "created_at"),
    )

    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    department: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="open")
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
