"""Celery app alias for interview sync tasks."""

from hrm_backend.candidates.infra.celery.app import celery_app

__all__ = ["celery_app"]
