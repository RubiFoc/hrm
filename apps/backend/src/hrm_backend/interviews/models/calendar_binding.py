"""Persistence model for per-interviewer calendar event bindings."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class InterviewCalendarBinding(Base):
    """Calendar event binding for one interviewer-specific shared calendar."""

    __tablename__ = "interview_calendar_bindings"
    __table_args__ = (
        Index("ix_interview_calendar_bindings_interview_id", "interview_id"),
        Index(
            "ux_interview_calendar_bindings_interviewer",
            "interview_id",
            "interviewer_staff_id",
            unique=True,
        ),
    )

    binding_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    interview_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interviews.interview_id", ondelete="CASCADE"),
        nullable=False,
    )
    interviewer_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
    calendar_id: Mapped[str] = mapped_column(String(512), nullable=False)
    calendar_event_id: Mapped[str] = mapped_column(String(512), nullable=False)
    schedule_version: Mapped[int] = mapped_column(Integer, nullable=False)
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
