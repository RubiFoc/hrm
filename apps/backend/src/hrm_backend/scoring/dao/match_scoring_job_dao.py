"""DAO for match scoring job lifecycle persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hrm_backend.scoring.models.scoring_job import MatchScoringJob


class MatchScoringJobDAO:
    """Data-access helper for match scoring job state rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_queued_job(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        document_id: str,
    ) -> MatchScoringJob:
        """Create queued scoring job for one vacancy-candidate-document tuple."""
        entity = MatchScoringJob(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            document_id=document_id,
            status="queued",
            attempt_count=0,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_latest_for_pair(self, *, vacancy_id: str, candidate_id: str) -> MatchScoringJob | None:
        """Fetch latest scoring job for one vacancy+candidate pair."""
        return (
            self._session.query(MatchScoringJob)
            .filter(
                MatchScoringJob.vacancy_id == vacancy_id,
                MatchScoringJob.candidate_id == candidate_id,
            )
            .order_by(MatchScoringJob.queued_at.desc(), MatchScoringJob.job_id.desc())
            .first()
        )

    def list_latest_for_vacancy(
        self,
        *,
        vacancy_id: str,
        candidate_id: str | None = None,
    ) -> list[MatchScoringJob]:
        """List latest scoring job rows for a vacancy, optionally filtered by candidate."""
        if candidate_id is not None:
            item = self.get_latest_for_pair(vacancy_id=vacancy_id, candidate_id=candidate_id)
            return [] if item is None else [item]

        ordered = (
            self._session.query(MatchScoringJob)
            .filter(MatchScoringJob.vacancy_id == vacancy_id)
            .order_by(MatchScoringJob.queued_at.desc(), MatchScoringJob.job_id.desc())
            .all()
        )
        items: list[MatchScoringJob] = []
        seen_candidates: set[str] = set()
        for job in ordered:
            if job.candidate_id in seen_candidates:
                continue
            seen_candidates.add(job.candidate_id)
            items.append(job)
        return items

    def get_by_id(self, job_id: str) -> MatchScoringJob | None:
        """Fetch scoring job by identifier."""
        return self._session.get(MatchScoringJob, job_id)

    def claim_next_job(self, *, max_attempts: int) -> MatchScoringJob | None:
        """Claim one queued/failed job and move it to `running`."""
        candidate = (
            self._session.query(MatchScoringJob)
            .filter(
                MatchScoringJob.status.in_(["queued", "failed"]),
                MatchScoringJob.attempt_count < max_attempts,
            )
            .order_by(MatchScoringJob.queued_at.asc(), MatchScoringJob.job_id.asc())
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

    def claim_job_by_id(self, *, job_id: str, max_attempts: int) -> MatchScoringJob | None:
        """Claim one specific queued/failed job by id and move it to `running`."""
        candidate = (
            self._session.query(MatchScoringJob)
            .filter(
                MatchScoringJob.job_id == job_id,
                MatchScoringJob.status.in_(["queued", "failed"]),
                MatchScoringJob.attempt_count < max_attempts,
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

    def mark_succeeded(self, job: MatchScoringJob) -> MatchScoringJob:
        """Mark one running job as succeeded."""
        now = datetime.now(UTC)
        job.status = "succeeded"
        job.last_error = None
        job.finished_at = now
        job.updated_at = now
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def mark_failed(self, job: MatchScoringJob, *, error_text: str) -> MatchScoringJob:
        """Mark one running job as failed."""
        now = datetime.now(UTC)
        job.status = "failed"
        job.last_error = error_text[:2048]
        job.finished_at = now
        job.updated_at = now
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

