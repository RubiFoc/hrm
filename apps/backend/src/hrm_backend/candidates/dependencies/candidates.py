"""Dependency providers for candidate API and worker services."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.infra.minio import CandidateStorage, MinioCandidateStorage
from hrm_backend.candidates.infra.postgres import (
    CandidateDocumentDAO,
    CandidateProfileDAO,
    CVParsingJobDAO,
)
from hrm_backend.candidates.services.candidate_service import CandidateService
from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService
from hrm_backend.core.db.session import get_db_session
from hrm_backend.settings import AppSettings, get_settings

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]


@lru_cache(maxsize=4)
def _build_storage(
    endpoint: str,
    access_key: str,
    secret_key: str,
    bucket_name: str,
) -> CandidateStorage:
    """Build cached MinIO storage adapter per configuration tuple.

    Args:
        endpoint: Object storage endpoint.
        access_key: Access key.
        secret_key: Secret key.
        bucket_name: Bucket name.

    Returns:
        CandidateStorage: MinIO-backed storage adapter.
    """
    return MinioCandidateStorage(
        endpoint=endpoint,
        access_key=access_key,
        secret_key=secret_key,
        bucket_name=bucket_name,
    )


def get_candidate_storage(settings: SettingsDependency) -> CandidateStorage:
    """Provide storage adapter for candidate document operations.

    Args:
        settings: Application settings.

    Returns:
        CandidateStorage: Object storage adapter.
    """
    return _build_storage(
        endpoint=settings.object_storage_endpoint,
        access_key=settings.object_storage_access_key,
        secret_key=settings.object_storage_secret_key,
        bucket_name=settings.object_storage_bucket,
    )


def get_candidate_service(
    settings: SettingsDependency,
    session: SessionDependency,
    storage: Annotated[CandidateStorage, Depends(get_candidate_storage)],
    audit_service: AuditDependency,
) -> CandidateService:
    """Build candidate service dependency.

    Args:
        settings: Application settings.
        session: SQLAlchemy session.
        storage: Object storage adapter.
        audit_service: Audit service dependency.

    Returns:
        CandidateService: Candidate business service.
    """
    return CandidateService(
        settings=settings,
        profile_dao=CandidateProfileDAO(session=session),
        document_dao=CandidateDocumentDAO(session=session),
        parsing_job_dao=CVParsingJobDAO(session=session),
        storage=storage,
        audit_service=audit_service,
    )


def get_cv_parsing_worker_service(
    settings: SettingsDependency,
    session: SessionDependency,
    storage: Annotated[CandidateStorage, Depends(get_candidate_storage)],
    audit_service: AuditDependency,
) -> CVParsingWorkerService:
    """Build worker service dependency for CV parsing loop.

    Args:
        settings: Application settings.
        session: SQLAlchemy session.
        storage: Object storage adapter.
        audit_service: Audit service dependency.

    Returns:
        CVParsingWorkerService: Worker orchestration service.
    """
    return CVParsingWorkerService(
        settings=settings,
        parsing_job_dao=CVParsingJobDAO(session=session),
        document_dao=CandidateDocumentDAO(session=session),
        storage=storage,
        audit_service=audit_service,
    )
