"""Polling worker loop for asynchronous CV parsing jobs."""

from __future__ import annotations

import time

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.infra.minio import MinioCandidateStorage
from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService
from hrm_backend.core.db.session import get_session_factory
from hrm_backend.settings import get_settings


def run_cv_parsing_worker_loop(*, poll_interval_seconds: float = 1.0) -> None:
    """Run infinite polling loop that processes queued CV parsing jobs.

    Args:
        poll_interval_seconds: Sleep duration between worker iterations.
    """
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    storage = MinioCandidateStorage(
        endpoint=settings.object_storage_endpoint,
        access_key=settings.object_storage_access_key,
        secret_key=settings.object_storage_secret_key,
        bucket_name=settings.object_storage_bucket,
    )

    while True:
        session = session_factory()
        try:
            worker = CVParsingWorkerService(
                settings=settings,
                parsing_job_dao=CVParsingJobDAO(session=session),
                document_dao=CandidateDocumentDAO(session=session),
                storage=storage,
                audit_service=AuditService(dao=AuditEventDAO(session=session)),
            )
            worker.process_next_job()
        finally:
            session.close()
        time.sleep(poll_interval_seconds)


if __name__ == "__main__":
    run_cv_parsing_worker_loop()
