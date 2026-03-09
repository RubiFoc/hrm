"""Persistence model for interviews and public registration tokens."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class Interview(Base):
    """Interview lifecycle row keyed to one vacancy-candidate pair."""

    __tablename__ = "interviews"
    __table_args__ = (
        Index("ix_interviews_vacancy_id", "vacancy_id"),
        Index("ix_interviews_candidate_id", "candidate_id"),
        Index("ix_interviews_status", "status"),
        Index("ix_interviews_calendar_sync_status", "calendar_sync_status"),
        Index("ix_interviews_candidate_token_hash", "candidate_token_hash"),
        Index(
            "ux_interviews_one_active_per_pair",
            "vacancy_id",
            "candidate_id",
            unique=True,
            sqlite_where=text("status != 'cancelled'"),
            postgresql_where=text("status != 'cancelled'"),
        ),
    )

    interview_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.vacancy_id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    calendar_sync_status: Mapped[str] = mapped_column(String(32), nullable=False)
    schedule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    scheduled_start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    scheduled_end_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(128), nullable=False)
    location_kind: Mapped[str] = mapped_column(String(32), nullable=False)
    location_details: Mapped[str | None] = mapped_column(Text, nullable=True)
    interviewer_staff_ids_json: Mapped[list[str]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    calendar_event_id: Mapped[str | None] = mapped_column(String(512), nullable=True)
    candidate_token_nonce: Mapped[str | None] = mapped_column(String(128), nullable=True)
    candidate_token_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    candidate_token_expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    candidate_response_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="pending",
    )
    candidate_response_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    cancelled_by: Mapped[str | None] = mapped_column(String(32), nullable=True)
    cancel_reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    calendar_sync_reason_code: Mapped[str | None] = mapped_column(String(128), nullable=True)
    calendar_sync_error_detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
    updated_by_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
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
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
