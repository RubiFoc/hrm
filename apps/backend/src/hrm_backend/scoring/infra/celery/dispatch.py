"""Task dispatch helpers for match scoring Celery workflows."""

from __future__ import annotations

from hrm_backend.settings import get_settings


def enqueue_match_scoring(*, job_id: str) -> None:
    """Enqueue one match scoring task by job id."""
    settings = get_settings()
    try:
        from hrm_backend.scoring.infra.celery.tasks import process_match_scoring_job

        process_match_scoring_job.apply_async(
            args=[job_id],
            queue=settings.match_scoring_queue_name,
        )
    except Exception:  # noqa: BLE001
        # Queue delivery failures are surfaced by job status polling and worker health checks.
        # We keep API path resilient because `match_scoring_jobs` remains source of truth.
        return
