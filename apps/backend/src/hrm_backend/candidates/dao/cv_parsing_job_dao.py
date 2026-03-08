"""DAO for CV parsing job lifecycle persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hrm_backend.candidates.models.parsing_job import CVParsingJob


class CVParsingJobDAO:
    """Data-access helper for CV parsing job state rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_queued_job(self, *, candidate_id: str, document_id: str) -> CVParsingJob:
        """Create queued parsing job for uploaded CV document.

        Args:
            candidate_id: Candidate profile identifier.
            document_id: Candidate document identifier.

        Returns:
            CVParsingJob: Persisted queued job.
        """
        entity = CVParsingJob(
            candidate_id=candidate_id,
            document_id=document_id,
            status="queued",
            attempt_count=0,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_latest_by_candidate(self, candidate_id: str) -> CVParsingJob | None:
        """Fetch latest parsing job for candidate.

        Args:
            candidate_id: Candidate profile identifier.

        Returns:
            CVParsingJob | None: Latest job row or `None`.
        """
        return (
            self._session.query(CVParsingJob)
            .filter(CVParsingJob.candidate_id == candidate_id)
            .order_by(CVParsingJob.queued_at.desc(), CVParsingJob.job_id.desc())
            .first()
        )

    def get_by_id(self, job_id: str) -> CVParsingJob | None:
        """Fetch parsing job by identifier.

        Args:
            job_id: Parsing job identifier.

        Returns:
            CVParsingJob | None: Matched job row or `None`.
        """
        return self._session.get(CVParsingJob, job_id)

    def claim_next_job(self, *, max_attempts: int) -> CVParsingJob | None:
        """Claim one queued/failed job and move it to `running`.

        Args:
            max_attempts: Maximum attempts allowed for one job.

        Returns:
            CVParsingJob | None: Claimed running job or `None` when queue is empty.
        """
        candidate = (
            self._session.query(CVParsingJob)
            .filter(
                CVParsingJob.status.in_(["queued", "failed"]),
                CVParsingJob.attempt_count < max_attempts,
            )
            .order_by(CVParsingJob.queued_at.asc(), CVParsingJob.job_id.asc())
            .first()
        )
        if candidate is None:
            return None

        now = datetime.now(UTC)
        candidate.status = "running"
        candidate.attempt_count += 1
        candidate.started_at = now
        candidate.updated_at = now
        candidate.last_error = None
        self._session.add(candidate)
        self._session.commit()
        self._session.refresh(candidate)
        return candidate

    def claim_job_by_id(self, *, job_id: str, max_attempts: int) -> CVParsingJob | None:
        """Claim one specific queued/failed job by id and move it to `running`.

        Args:
            job_id: Parsing job identifier.
            max_attempts: Maximum attempts allowed for one job.

        Returns:
            CVParsingJob | None: Claimed running job or `None` when not claimable.
        """
        candidate = (
            self._session.query(CVParsingJob)
            .filter(
                CVParsingJob.job_id == job_id,
                CVParsingJob.status.in_(["queued", "failed"]),
                CVParsingJob.attempt_count < max_attempts,
            )
            .first()
        )
        if candidate is None:
            return None

        now = datetime.now(UTC)
        candidate.status = "running"
        candidate.attempt_count += 1
        candidate.started_at = now
        candidate.updated_at = now
        candidate.last_error = None
        self._session.add(candidate)
        self._session.commit()
        self._session.refresh(candidate)
        return candidate

    def mark_succeeded(self, job: CVParsingJob) -> CVParsingJob:
        """Mark one running job as succeeded.

        Args:
            job: Running job entity.

        Returns:
            CVParsingJob: Updated succeeded entity.
        """
        now = datetime.now(UTC)
        job.status = "succeeded"
        job.last_error = None
        job.finished_at = now
        job.updated_at = now
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def mark_failed(self, job: CVParsingJob, *, error_text: str) -> CVParsingJob:
        """Mark one running job as failed.

        Args:
            job: Running job entity.
            error_text: Failure reason.

        Returns:
            CVParsingJob: Updated failed entity.
        """
        now = datetime.now(UTC)
        job.status = "failed"
        job.last_error = error_text[:2048]
        job.finished_at = now
        job.updated_at = now
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job
