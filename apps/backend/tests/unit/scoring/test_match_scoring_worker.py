"""Unit tests for match scoring worker lifecycle and retry behavior."""

from __future__ import annotations

from dataclasses import dataclass

from hrm_backend.scoring.services.match_scoring_worker_service import MatchScoringWorkerService
from hrm_backend.scoring.utils.result import MatchScoreResult
from hrm_backend.settings import AppSettings


@dataclass
class _Job:
    job_id: str
    vacancy_id: str
    candidate_id: str
    document_id: str
    status: str
    attempt_count: int
    last_error: str | None = None


@dataclass
class _Vacancy:
    vacancy_id: str
    title: str
    description: str
    department: str
    status: str


@dataclass
class _Document:
    document_id: str
    parsed_profile_json: dict[str, object] | None
    evidence_json: list[dict[str, object]] | None
    parsed_at: object | None


class _FakeScoringJobDAO:
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


class _FakeScoreArtifactDAO:
    def __init__(self) -> None:
        self.payloads: list[dict[str, object]] = []

    def upsert_artifact(self, **payload: object) -> None:
        self.payloads.append(payload)


class _FakeVacancyDAO:
    def __init__(self, vacancies: dict[str, _Vacancy]) -> None:
        self._vacancies = vacancies

    def get_by_id(self, vacancy_id: str) -> _Vacancy | None:
        return self._vacancies.get(vacancy_id)


class _FakeCandidateProfileDAO:
    def __init__(self, candidate_ids: set[str]) -> None:
        self._candidate_ids = candidate_ids

    def get_by_id(self, candidate_id: str) -> object | None:
        return object() if candidate_id in self._candidate_ids else None


class _FakeDocumentDAO:
    def __init__(self, documents: dict[str, _Document]) -> None:
        self._documents = documents

    def get_by_id(self, document_id: str) -> _Document | None:
        return self._documents.get(document_id)


class _FakeAdapter:
    def __init__(self, *, should_fail: bool = False) -> None:
        self._should_fail = should_fail

    def score_candidate(self, **_: object) -> MatchScoreResult:
        if self._should_fail:
            raise RuntimeError("Ollama scoring failed by deterministic test marker")
        return MatchScoreResult.model_validate(
            {
                "score": 83,
                "confidence": 0.78,
                "summary": "Good fit with strong Python and API background.",
                "matched_requirements": ["Python", "REST APIs"],
                "missing_requirements": ["Kubernetes"],
                "evidence": [
                    {
                        "requirement": "Python",
                        "snippet": "5 years of Python backend development",
                        "source_field": "skills",
                    }
                ],
                "model_name": "llama3.2",
                "model_version": "latest",
            }
        )


class _FakeAuditService:
    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_background_event(self, **payload: object) -> None:
        self.events.append(payload)


def _build_worker(
    *,
    jobs: list[_Job],
    vacancies: dict[str, _Vacancy],
    candidate_ids: set[str],
    documents: dict[str, _Document],
    adapter: _FakeAdapter,
    artifact_dao: _FakeScoreArtifactDAO,
    audit_service: _FakeAuditService,
) -> MatchScoringWorkerService:
    settings = AppSettings(
        match_scoring_max_attempts=3,
        jwt_secret="integration-secret-with-minimum-32-bytes",
    )
    return MatchScoringWorkerService(
        settings=settings,
        scoring_job_dao=_FakeScoringJobDAO(jobs),  # type: ignore[arg-type]
        score_artifact_dao=artifact_dao,  # type: ignore[arg-type]
        vacancy_dao=_FakeVacancyDAO(vacancies),  # type: ignore[arg-type]
        candidate_profile_dao=_FakeCandidateProfileDAO(candidate_ids),  # type: ignore[arg-type]
        document_dao=_FakeDocumentDAO(documents),  # type: ignore[arg-type]
        adapter=adapter,  # type: ignore[arg-type]
        audit_service=audit_service,  # type: ignore[arg-type]
    )


def test_worker_returns_idle_when_queue_is_empty() -> None:
    """Verify worker iteration is idle when no processable jobs exist."""
    worker = _build_worker(
        jobs=[],
        vacancies={},
        candidate_ids=set(),
        documents={},
        adapter=_FakeAdapter(),
        artifact_dao=_FakeScoreArtifactDAO(),
        audit_service=_FakeAuditService(),
    )

    result = worker.process_next_job()

    assert result.status == "idle"
    assert result.processed_job_id is None


def test_worker_marks_job_succeeded_and_persists_artifact_once() -> None:
    """Verify successful scoring persists one artifact and does not reprocess succeeded job."""
    jobs = [
        _Job(
            job_id="job-1",
            vacancy_id="vac-1",
            candidate_id="cand-1",
            document_id="doc-1",
            status="queued",
            attempt_count=0,
        )
    ]
    worker = _build_worker(
        jobs=jobs,
        vacancies={
            "vac-1": _Vacancy(
                vacancy_id="vac-1",
                title="Backend Engineer",
                description="Build APIs",
                department="Engineering",
                status="open",
            )
        },
        candidate_ids={"cand-1"},
        documents={
            "doc-1": _Document(
                document_id="doc-1",
                parsed_profile_json={"skills": ["Python"]},
                evidence_json=[{"field": "skills", "snippet": "Python"}],
                parsed_at="now",
            )
        },
        adapter=_FakeAdapter(),
        artifact_dao=_FakeScoreArtifactDAO(),
        audit_service=_FakeAuditService(),
    )

    first = worker.process_next_job()
    second = worker.process_next_job()

    assert first.status == "succeeded"
    assert first.processed_job_id == "job-1"
    assert second.status == "idle"
    assert jobs[0].status == "succeeded"


def test_worker_marks_failure_and_sets_retry_metadata() -> None:
    """Verify adapter failure marks job failed and returns retry metadata."""
    jobs = [
        _Job(
            job_id="job-2",
            vacancy_id="vac-1",
            candidate_id="cand-1",
            document_id="doc-1",
            status="queued",
            attempt_count=0,
        )
    ]
    artifact_dao = _FakeScoreArtifactDAO()
    audit_service = _FakeAuditService()
    worker = _build_worker(
        jobs=jobs,
        vacancies={
            "vac-1": _Vacancy(
                vacancy_id="vac-1",
                title="Backend Engineer",
                description="Build APIs",
                department="Engineering",
                status="open",
            )
        },
        candidate_ids={"cand-1"},
        documents={
            "doc-1": _Document(
                document_id="doc-1",
                parsed_profile_json={"skills": ["Python"]},
                evidence_json=[{"field": "skills", "snippet": "Python"}],
                parsed_at="now",
            )
        },
        adapter=_FakeAdapter(should_fail=True),
        artifact_dao=artifact_dao,
        audit_service=audit_service,
    )

    result = worker.process_next_job()

    assert result.status == "failed"
    assert result.can_retry is True
    assert jobs[0].status == "failed"
    assert jobs[0].last_error is not None
    assert artifact_dao.payloads == []
    assert audit_service.events[-1]["result"] == "failure"

