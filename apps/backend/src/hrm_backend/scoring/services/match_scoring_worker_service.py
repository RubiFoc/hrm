"""Worker service for asynchronous match scoring lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.scoring.dao.match_score_artifact_dao import MatchScoreArtifactDAO
from hrm_backend.scoring.dao.match_scoring_job_dao import MatchScoringJobDAO
from hrm_backend.scoring.infra.ollama.adapter import MatchScoringAdapter
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO


@dataclass(frozen=True)
class MatchScoringIterationResult:
    """Worker iteration result payload."""

    processed_job_id: str | None
    status: str
    attempt_count: int | None = None
    can_retry: bool = False


class MatchScoringWorkerService:
    """Orchestrates match scoring polling and lifecycle transitions."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        scoring_job_dao: MatchScoringJobDAO,
        score_artifact_dao: MatchScoreArtifactDAO,
        vacancy_dao: VacancyDAO,
        candidate_profile_dao: CandidateProfileDAO,
        document_dao: CandidateDocumentDAO,
        adapter: MatchScoringAdapter,
        audit_service: AuditService,
    ) -> None:
        """Initialize worker service dependencies."""
        self._settings = settings
        self._scoring_job_dao = scoring_job_dao
        self._score_artifact_dao = score_artifact_dao
        self._vacancy_dao = vacancy_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._document_dao = document_dao
        self._adapter = adapter
        self._audit_service = audit_service

    def process_next_job(self) -> MatchScoringIterationResult:
        """Claim and process one scoring job from queue."""
        job = self._scoring_job_dao.claim_next_job(
            max_attempts=self._settings.match_scoring_max_attempts
        )
        if job is None:
            return MatchScoringIterationResult(processed_job_id=None, status="idle")
        return self._process_claimed_job(job)

    def process_job_by_id(self, *, job_id: str) -> MatchScoringIterationResult:
        """Claim and process one specific scoring job identified by UUID string."""
        job = self._scoring_job_dao.claim_job_by_id(
            job_id=job_id,
            max_attempts=self._settings.match_scoring_max_attempts,
        )
        if job is None:
            return MatchScoringIterationResult(processed_job_id=job_id, status="idle")
        return self._process_claimed_job(job)

    def _process_claimed_job(self, job) -> MatchScoringIterationResult:
        """Process already claimed running job and update lifecycle state."""
        vacancy = self._vacancy_dao.get_by_id(job.vacancy_id)
        if vacancy is None:
            return self._fail_job(job, reason="Vacancy not found for scoring")

        candidate = self._candidate_profile_dao.get_by_id(job.candidate_id)
        if candidate is None:
            return self._fail_job(job, reason="Candidate not found for scoring")
        del candidate

        document = self._document_dao.get_by_id(job.document_id)
        if document is None:
            return self._fail_job(job, reason="Candidate document not found for scoring")
        if (
            document.parsed_profile_json is None
            or document.evidence_json is None
            or document.parsed_at is None
        ):
            return self._fail_job(job, reason="CV analysis is not ready")

        try:
            payload = self._adapter.score_candidate(vacancy=vacancy, document=document)
            self._score_artifact_dao.upsert_artifact(
                job_id=job.job_id,
                vacancy_id=job.vacancy_id,
                candidate_id=job.candidate_id,
                document_id=job.document_id,
                payload=payload,
            )
        except Exception as exc:  # noqa: BLE001
            return self._fail_job(job, reason=str(exc))

        succeeded = self._scoring_job_dao.mark_succeeded(job)
        self._audit_service.record_background_event(
            action="match_score:create",
            resource_type="match_score",
            result="success",
            correlation_id=job.job_id,
            resource_id=f"{job.vacancy_id}:{job.candidate_id}",
        )
        return MatchScoringIterationResult(
            processed_job_id=job.job_id,
            status="succeeded",
            attempt_count=succeeded.attempt_count,
            can_retry=False,
        )

    def _fail_job(self, job, *, reason: str) -> MatchScoringIterationResult:
        """Mark one claimed job as failed and return retry metadata."""
        failed = self._scoring_job_dao.mark_failed(job, error_text=reason)
        self._audit_service.record_background_event(
            action="match_score:create",
            resource_type="match_score",
            result="failure",
            correlation_id=job.job_id,
            resource_id=f"{job.vacancy_id}:{job.candidate_id}",
            reason=reason,
        )
        can_retry = failed.attempt_count < self._settings.match_scoring_max_attempts
        return MatchScoringIterationResult(
            processed_job_id=job.job_id,
            status="failed",
            attempt_count=failed.attempt_count,
            can_retry=can_retry,
        )

