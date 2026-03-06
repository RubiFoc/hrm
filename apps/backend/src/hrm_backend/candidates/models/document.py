"""Candidate document persistence model for CV files."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class CandidateDocument(Base):
    """Stored metadata for uploaded candidate CV documents.

    Attributes:
        document_id: Unique document identifier.
        candidate_id: Linked candidate profile identifier.
        object_key: Object storage key in MinIO bucket.
        filename: Original filename from upload.
        mime_type: Validated MIME type.
        size_bytes: Uploaded file size in bytes.
        checksum_sha256: SHA-256 digest in hex form.
        is_active: Whether this row is the current active CV.
        parsed_profile_json: Canonical normalized profile extracted from CV.
        evidence_json: Evidence links from extracted fields to source snippets.
        detected_language: Detected CV language (`ru`, `en`, `mixed`, `unknown`).
        parsed_at: Timestamp when parsing and normalization succeeded.
        created_at: Upload timestamp.
    """

    __tablename__ = "candidate_documents"
    __table_args__ = (
        Index("ix_candidate_documents_candidate_id", "candidate_id"),
        Index("ix_candidate_documents_object_key", "object_key", unique=True),
        Index("ix_candidate_documents_candidate_active", "candidate_id", "is_active"),
        Index("ix_candidate_documents_parsed_at", "parsed_at"),
        Index("ix_candidate_documents_candidate_parsed_at", "candidate_id", "parsed_at"),
    )

    document_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(128), nullable=False)
    size_bytes: Mapped[int] = mapped_column(nullable=False)
    checksum_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    parsed_profile_json: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    evidence_json: Mapped[list[dict[str, object]] | None] = mapped_column(JSON, nullable=True)
    detected_language: Mapped[str] = mapped_column(String(16), nullable=False, default="unknown")
    parsed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
