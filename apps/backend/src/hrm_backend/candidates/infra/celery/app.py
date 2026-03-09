"""Celery application factory for candidate background tasks."""

from __future__ import annotations

from celery import Celery

from hrm_backend.settings import get_settings

settings = get_settings()
celery_app = Celery(
    "hrm.candidates",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_default_queue=settings.celery_task_default_queue,
    task_time_limit=settings.celery_task_time_limit_seconds,
    task_always_eager=settings.celery_task_always_eager,
    imports=(
        "hrm_backend.candidates.infra.celery.tasks",
        "hrm_backend.scoring.infra.celery.tasks",
    ),
)
