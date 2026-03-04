"""Celery tasks for candidate CV parsing lifecycle."""

from __future__ import annotations

from celery import Task

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.infra.celery.app import celery_app
from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService
from hrm_backend.candidates.utils.storage import MinioCandidateStorage
from hrm_backend.core.db.session import get_session_factory
from hrm_backend.settings import get_settings


@celery_app.task(bind=True, name="candidates.process_cv_parsing_job", max_retries=50)
def process_cv_parsing_job(self: Task, job_id: str) -> str:
    """Process one cv_parsing_jobs row by job id with controlled retries."""
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    session = session_factory()
    try:
        storage = MinioCandidateStorage(
            endpoint=settings.object_storage_endpoint,
            access_key=settings.object_storage_access_key,
            secret_key=settings.object_storage_secret_key,
            bucket_name=settings.object_storage_bucket,
        )
        worker = CVParsingWorkerService(
            settings=settings,
            parsing_job_dao=CVParsingJobDAO(session=session),
            document_dao=CandidateDocumentDAO(session=session),
            storage=storage,
            audit_service=AuditService(dao=AuditEventDAO(session=session)),
        )
        result = worker.process_job_by_id(job_id=job_id)
        if result.status == "failed" and result.can_retry:
            raise self.retry(countdown=2)
        return result.status
    finally:
        session.close()
