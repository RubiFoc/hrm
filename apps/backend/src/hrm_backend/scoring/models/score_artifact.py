"""Persistence model for explainable match score artifacts."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class MatchScoreArtifact(Base):
    """Persisted explainable score payload for one completed scoring job.

    Attributes:
        artifact_id: Unique artifact identifier.
        job_id: Linked match scoring job identifier.
        vacancy_id: Linked vacancy identifier.
        candidate_id: Linked candidate profile identifier.
        document_id: Candidate document identifier used as scoring source.
        score: Normalized score in the range 0..100.
        confidence: Confidence in the range 0..1.
        summary: Human-readable explanation summary.
        matched_requirements_json: Requirement list satisfied by the candidate.
        missing_requirements_json: Requirement list that remains missing.
        evidence_json: Evidence snippets supporting the score explanation.
        model_name: Model family/name used for scoring.
        model_version: Model version/tag used for scoring.
        scored_at: Timestamp when scoring completed.
        created_at: Artifact row creation timestamp.
    """

    __tablename__ = "match_score_artifacts"
    __table_args__ = (
        Index("ix_match_score_artifacts_job_id", "job_id", unique=True),
        Index("ix_match_score_artifacts_vacancy_id", "vacancy_id"),
        Index("ix_match_score_artifacts_candidate_id", "candidate_id"),
        Index("ix_match_score_artifacts_document_id", "document_id"),
        Index(
            "ix_match_score_artifacts_vacancy_candidate_scored_at",
            "vacancy_id",
            "candidate_id",
            "scored_at",
        ),
    )

    artifact_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    job_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("match_scoring_jobs.job_id", ondelete="CASCADE"),
        nullable=False,
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
    document_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_documents.document_id", ondelete="CASCADE"),
        nullable=False,
    )
    score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    matched_requirements_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    missing_requirements_json: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    evidence_json: Mapped[list[dict[str, object]]] = mapped_column(
        JSON,
        nullable=False,
        default=list,
    )
    model_name: Mapped[str] = mapped_column(String(128), nullable=False)
    model_version: Mapped[str] = mapped_column(String(128), nullable=False)
    scored_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

