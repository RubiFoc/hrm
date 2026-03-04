"""Persistence model for asynchronous CV parsing jobs."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class CVParsingJob(Base):
    """Asynchronous parsing job state for uploaded CV documents.

    Attributes:
        job_id: Unique parsing job identifier.
        candidate_id: Linked candidate profile identifier.
        document_id: Linked candidate document identifier.
        status: Lifecycle status (`queued`, `running`, `succeeded`, `failed`).
        attempt_count: Number of worker attempts performed.
        last_error: Last failure reason if status is `failed`.
        queued_at: Queue timestamp.
        started_at: Worker start timestamp.
        finished_at: Completion timestamp for terminal statuses.
        updated_at: Last status update timestamp.
    """

    __tablename__ = "cv_parsing_jobs"
    __table_args__ = (
        Index("ix_cv_parsing_jobs_status", "status"),
        Index("ix_cv_parsing_jobs_queued_at", "queued_at"),
        Index("ix_cv_parsing_jobs_candidate_id", "candidate_id"),
        Index("ix_cv_parsing_jobs_document_id", "document_id"),
    )

    job_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    attempt_count: Mapped[int] = mapped_column(nullable=False, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
