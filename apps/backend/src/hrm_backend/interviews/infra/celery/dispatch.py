"""Task dispatch helpers for interview sync Celery workflows."""

from __future__ import annotations

from hrm_backend.settings import get_settings


def enqueue_interview_sync(*, interview_id: str) -> None:
    """Enqueue one interview sync task by interview id."""
    settings = get_settings()
    try:
        from hrm_backend.interviews.infra.celery.tasks import process_interview_sync

        process_interview_sync.apply_async(
            args=[interview_id],
            queue=settings.interview_sync_queue_name,
        )
    except Exception:  # noqa: BLE001
        return
