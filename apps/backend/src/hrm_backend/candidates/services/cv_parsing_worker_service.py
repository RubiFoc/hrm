"""Worker service for asynchronous CV parsing lifecycle."""

from __future__ import annotations

from dataclasses import dataclass

from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.infra.minio import CandidateStorage
from hrm_backend.candidates.utils.cv import parse_cv_document
from hrm_backend.settings import AppSettings


@dataclass(frozen=True)
class CVParsingIterationResult:
    """Worker iteration result payload."""

    processed_job_id: str | None
    status: str
    attempt_count: int | None = None
    can_retry: bool = False


class CVParsingWorkerService:
    """Orchestrates CV parsing job polling and lifecycle transitions."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        parsing_job_dao: CVParsingJobDAO,
        document_dao: CandidateDocumentDAO,
        storage: CandidateStorage,
        audit_service: AuditService,
    ) -> None:
        """Initialize worker service dependencies."""
        self._settings = settings
        self._parsing_job_dao = parsing_job_dao
        self._document_dao = document_dao
        self._storage = storage
        self._audit_service = audit_service

    def process_next_job(self) -> CVParsingIterationResult:
        """Claim and process one parsing job from queue."""
        job = self._parsing_job_dao.claim_next_job(
            max_attempts=self._settings.cv_parsing_max_attempts
        )
        if job is None:
            return CVParsingIterationResult(processed_job_id=None, status="idle")

        return self._process_claimed_job(job)

    def process_job_by_id(self, *, job_id: str) -> CVParsingIterationResult:
        """Claim and process one specific parsing job identified by UUID string."""
        job = self._parsing_job_dao.claim_job_by_id(
            job_id=job_id,
            max_attempts=self._settings.cv_parsing_max_attempts,
        )
        if job is None:
            return CVParsingIterationResult(processed_job_id=job_id, status="idle")

        return self._process_claimed_job(job)

    def _process_claimed_job(self, job) -> CVParsingIterationResult:
        """Process already claimed running job and update lifecycle state."""
        doc = self._document_dao.get_by_id(job.document_id)
        if doc is None:
            failed = self._parsing_job_dao.mark_failed(
                job,
                error_text="CV document not found for parsing",
            )
            self._audit_service.record_background_event(
                action="candidate_cv:parse",
                resource_type="candidate_document",
                result="failure",
                correlation_id=job.job_id,
                resource_id=job.document_id,
                reason="CV document not found for parsing",
            )
            can_retry = failed.attempt_count < self._settings.cv_parsing_max_attempts
            return CVParsingIterationResult(
                processed_job_id=job.job_id,
                status="failed",
                attempt_count=failed.attempt_count,
                can_retry=can_retry,
            )

        try:
            payload = self._storage.get_object(object_key=doc.object_key)
            parse_cv_document(content=payload, mime_type=doc.mime_type)
        except Exception as exc:  # noqa: BLE001
            failed = self._parsing_job_dao.mark_failed(job, error_text=str(exc))
            self._audit_service.record_background_event(
                action="candidate_cv:parse",
                resource_type="candidate_document",
                result="failure",
                correlation_id=job.job_id,
                resource_id=job.document_id,
                reason=str(exc),
            )
            can_retry = failed.attempt_count < self._settings.cv_parsing_max_attempts
            return CVParsingIterationResult(
                processed_job_id=job.job_id,
                status="failed",
                attempt_count=failed.attempt_count,
                can_retry=can_retry,
            )

        succeeded = self._parsing_job_dao.mark_succeeded(job)
        self._audit_service.record_background_event(
            action="candidate_cv:parse",
            resource_type="candidate_document",
            result="success",
            correlation_id=job.job_id,
            resource_id=job.document_id,
        )
        return CVParsingIterationResult(
            processed_job_id=job.job_id,
            status="succeeded",
            attempt_count=succeeded.attempt_count,
            can_retry=False,
        )
