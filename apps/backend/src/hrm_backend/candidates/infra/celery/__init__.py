"""Celery adapters for candidate domain."""

from hrm_backend.candidates.infra.celery.app import celery_app
from hrm_backend.candidates.infra.celery.dispatch import enqueue_cv_parsing
from hrm_backend.candidates.infra.celery.tasks import process_cv_parsing_job

__all__ = ["celery_app", "enqueue_cv_parsing", "process_cv_parsing_job"]
