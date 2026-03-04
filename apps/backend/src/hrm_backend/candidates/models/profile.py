"""Candidate profile persistence model."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class CandidateProfile(Base):
    """Primary candidate profile entity used by recruitment workflows.

    Attributes:
        candidate_id: Unique candidate identifier.
        owner_subject_id: Auth subject that owns this profile.
        first_name: Candidate first name.
        last_name: Candidate last name.
        email: Candidate e-mail address.
        phone: Candidate phone number.
        location: Candidate location or city.
        current_title: Candidate current job title.
        extra_data: Extensible profile attributes (JSON).
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "candidate_profiles"
    __table_args__ = (
        Index("ix_candidate_profiles_owner_subject_id", "owner_subject_id"),
        Index("ix_candidate_profiles_email", "email"),
    )

    candidate_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    owner_subject_id: Mapped[str] = mapped_column(String(128), nullable=False)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extra_data: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
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
