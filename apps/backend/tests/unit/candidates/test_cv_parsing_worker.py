"""Unit tests for CV parsing worker lifecycle and retry-safety."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService
from hrm_backend.settings import AppSettings

FIXTURES_DIR = Path(__file__).resolve().parents[2] / "fixtures" / "candidates"


def _read_fixture_bytes(filename: str) -> bytes:
    """Read one CV fixture payload by filename."""
    return (FIXTURES_DIR / filename).read_bytes()


@dataclass
class _Job:
    job_id: str
    candidate_id: str
    document_id: str
    status: str
    attempt_count: int
    last_error: str | None = None


@dataclass
class _Document:
    document_id: str
    object_key: str
    mime_type: str
    parsed_profile_json: dict[str, object] | None = None
    evidence_json: list[dict[str, object]] | None = None
    detected_language: str = "unknown"
    parsed_at: object | None = None


class _FakeParsingJobDAO:
    def __init__(self, jobs: list[_Job]) -> None:
        self._jobs = jobs

    def claim_next_job(self, *, max_attempts: int) -> _Job | None:
        for job in self._jobs:
            if job.status in {"queued", "failed"} and job.attempt_count < max_attempts:
                job.status = "running"
                job.attempt_count += 1
                job.last_error = None
                return job
        return None

    def mark_succeeded(self, job: _Job) -> _Job:
        job.status = "succeeded"
        return job

    def mark_failed(self, job: _Job, *, error_text: str) -> _Job:
        job.status = "failed"
        job.last_error = error_text
        return job


class _FakeDocumentDAO:
    def __init__(self, documents: dict[str, _Document]) -> None:
        self._documents = documents

    def get_by_id(self, document_id: str) -> _Document | None:
        return self._documents.get(document_id)

    def mark_document_parsed(
        self,
        document: _Document,
        *,
        parsed_profile: dict[str, object],
        evidence: list[dict[str, object]],
        detected_language: str,
    ) -> _Document:
        document.parsed_profile_json = parsed_profile
        document.evidence_json = evidence
        document.detected_language = detected_language
        document.parsed_at = "now"
        return document


class _FakeStorage:
    def __init__(self, payloads: dict[str, bytes]) -> None:
        self._payloads = payloads

    def get_object(self, *, object_key: str) -> bytes:
        return self._payloads[object_key]


class _FakeAuditService:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_background_event(self, **payload: object) -> None:
        self.events.append(payload)


def _build_worker(
    jobs: list[_Job],
    documents: dict[str, _Document],
    payloads: dict[str, bytes],
    audit_service: _FakeAuditService,
) -> CVParsingWorkerService:
    settings = AppSettings(
        cv_parsing_max_attempts=3,
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    return CVParsingWorkerService(
        settings=settings,
        parsing_job_dao=_FakeParsingJobDAO(jobs),  # type: ignore[arg-type]
        document_dao=_FakeDocumentDAO(documents),  # type: ignore[arg-type]
        storage=_FakeStorage(payloads),  # type: ignore[arg-type]
        audit_service=audit_service,  # type: ignore[arg-type]
    )


def test_worker_returns_idle_when_queue_is_empty() -> None:
    """Verify worker iteration is idle when no processable jobs exist."""
    audit_service = _FakeAuditService()
    worker = _build_worker(jobs=[], documents={}, payloads={}, audit_service=audit_service)

    result = worker.process_next_job()

    assert result.status == "idle"
    assert result.processed_job_id is None
    assert audit_service.events == []


def test_worker_marks_job_succeeded_and_is_retry_safe() -> None:
    """Verify worker marks successful parse once and does not reprocess succeeded job."""
    jobs = [
        _Job(
            job_id="job-1",
            candidate_id="cand-1",
            document_id="doc-1",
            status="queued",
            attempt_count=0,
        )
    ]
    documents = {
        "doc-1": _Document(
            document_id="doc-1",
            object_key="obj-1",
            mime_type="application/pdf",
        )
    }
    payloads = {"obj-1": _read_fixture_bytes("sample_cv_en.pdf")}
    audit_service = _FakeAuditService()
    worker = _build_worker(
        jobs=jobs,
        documents=documents,
        payloads=payloads,
        audit_service=audit_service,
    )

    first = worker.process_next_job()
    second = worker.process_next_job()

    assert first.status == "succeeded"
    assert first.processed_job_id == "job-1"
    assert second.status == "idle"
    assert jobs[0].status == "succeeded"
    assert documents["doc-1"].parsed_profile_json is not None
    assert documents["doc-1"].evidence_json is not None
    assert documents["doc-1"].detected_language == "en"
    assert len(audit_service.events) == 1
    assert audit_service.events[0]["result"] == "success"


def test_worker_marks_failure_and_records_reason() -> None:
    """Verify worker marks failed status and stores failure audit event."""
    jobs = [
        _Job(
            job_id="job-2",
            candidate_id="cand-1",
            document_id="doc-2",
            status="queued",
            attempt_count=0,
        )
    ]
    documents = {
        "doc-2": _Document(
            document_id="doc-2",
            object_key="obj-2",
            mime_type="application/pdf",
        )
    }
    payloads = {"obj-2": _read_fixture_bytes("broken_cv.pdf")}
    audit_service = _FakeAuditService()
    worker = _build_worker(
        jobs=jobs,
        documents=documents,
        payloads=payloads,
        audit_service=audit_service,
    )

    result = worker.process_next_job()

    assert result.status == "failed"
    assert jobs[0].status == "failed"
    assert jobs[0].last_error is not None
    assert "PDF" in jobs[0].last_error
    assert len(audit_service.events) == 1
    assert audit_service.events[0]["result"] == "failure"
