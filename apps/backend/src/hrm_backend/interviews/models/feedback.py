"""SQLAlchemy model for structured interviewer feedback rows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class InterviewFeedback(Base):
    """One interviewer's structured feedback for one interview schedule version."""

    __tablename__ = "interview_feedback"
    __table_args__ = (
        Index("ix_interview_feedback_interview_id", "interview_id"),
        Index("ix_interview_feedback_schedule_version", "schedule_version"),
        Index(
            "ux_interview_feedback_interviewer_version",
            "interview_id",
            "schedule_version",
            "interviewer_staff_id",
            unique=True,
        ),
    )

    feedback_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    interview_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("interviews.interview_id", ondelete="CASCADE"),
        nullable=False,
    )
    schedule_version: Mapped[int] = mapped_column(Integer, nullable=False)
    interviewer_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
    requirements_match_score: Mapped[int] = mapped_column(Integer, nullable=False)
    communication_score: Mapped[int] = mapped_column(Integer, nullable=False)
    problem_solving_score: Mapped[int] = mapped_column(Integer, nullable=False)
    collaboration_score: Mapped[int] = mapped_column(Integer, nullable=False)
    recommendation: Mapped[str] = mapped_column(String(32), nullable=False)
    strengths_note: Mapped[str] = mapped_column(Text, nullable=False)
    concerns_note: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_note: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
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
