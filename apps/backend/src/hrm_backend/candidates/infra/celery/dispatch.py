"""Task dispatch helpers for candidate Celery workflows."""

from __future__ import annotations

from hrm_backend.candidates.infra.celery.tasks import process_cv_parsing_job


def enqueue_cv_parsing(*, job_id: str) -> None:
    """Enqueue one CV parsing task by job id."""
    try:
        process_cv_parsing_job.delay(job_id)
    except Exception:  # noqa: BLE001
        # Queue delivery failures are surfaced by job status polling and worker health checks.
        # We keep API path resilient because `cv_parsing_jobs` remains source of truth.
        return
