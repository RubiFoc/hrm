"""Database guard queries used by public vacancy application anti-spam policy."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition


class PublicApplyGuardDAO:
    """Read-only DAO with anti-spam lookup helpers for public applications."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def has_recent_submission_for_email(
        self,
        *,
        vacancy_id: str,
        email: str,
        window_seconds: int,
    ) -> bool:
        """Check whether email already applied to vacancy in recent time window.

        Args:
            vacancy_id: Vacancy identifier.
            email: Normalized candidate email.
            window_seconds: Cooldown window in seconds.

        Returns:
            bool: ``True`` when a recent public application exists.
        """
        if window_seconds <= 0:
            return False

        threshold = datetime.now(UTC) - timedelta(seconds=window_seconds)
        stmt = (
            select(PipelineTransition.transition_id)
            .join(
                CandidateProfile,
                CandidateProfile.candidate_id == PipelineTransition.candidate_id,
            )
            .where(PipelineTransition.vacancy_id == vacancy_id)
            .where(PipelineTransition.to_stage == "applied")
            .where(PipelineTransition.reason == "public_application")
            .where(CandidateProfile.email == email)
            .where(PipelineTransition.transitioned_at >= threshold)
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None

    def has_recent_submission_for_checksum(
        self,
        *,
        vacancy_id: str,
        checksum_sha256: str,
        window_seconds: int,
    ) -> bool:
        """Check whether checksum was already submitted to the same vacancy recently.

        Args:
            vacancy_id: Vacancy identifier.
            checksum_sha256: SHA-256 document checksum.
            window_seconds: Deduplication window in seconds.

        Returns:
            bool: ``True`` when duplicate submission is detected.
        """
        if window_seconds <= 0:
            return False

        threshold = datetime.now(UTC) - timedelta(seconds=window_seconds)
        stmt = (
            select(PipelineTransition.transition_id)
            .join(
                CandidateDocument,
                CandidateDocument.candidate_id == PipelineTransition.candidate_id,
            )
            .where(PipelineTransition.vacancy_id == vacancy_id)
            .where(PipelineTransition.to_stage == "applied")
            .where(PipelineTransition.reason == "public_application")
            .where(CandidateDocument.checksum_sha256 == checksum_sha256)
            .where(PipelineTransition.transitioned_at >= threshold)
            .limit(1)
        )
        return self._session.execute(stmt).scalar_one_or_none() is not None
