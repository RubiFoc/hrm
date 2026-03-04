"""Dependency providers for vacancy API services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.infra.minio import CandidateStorage
from hrm_backend.candidates.infra.postgres import (
    CandidateDocumentDAO,
    CandidateProfileDAO,
    CVParsingJobDAO,
)
from hrm_backend.core.db.session import get_db_session
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.infra.postgres import PipelineTransitionDAO, VacancyDAO
from hrm_backend.vacancies.services.application_service import VacancyApplicationService
from hrm_backend.vacancies.services.vacancy_service import VacancyService

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
CandidateStorageDependency = Annotated[CandidateStorage, Depends(get_candidate_storage)]


def get_vacancy_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> VacancyService:
    """Build vacancy service dependency.

    Args:
        session: SQLAlchemy session.
        audit_service: Audit service dependency.

    Returns:
        VacancyService: Vacancy domain service.
    """
    return VacancyService(
        vacancy_dao=VacancyDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        audit_service=audit_service,
    )


def get_vacancy_application_service(
    settings: SettingsDependency,
    session: SessionDependency,
    storage: CandidateStorageDependency,
    audit_service: AuditDependency,
) -> VacancyApplicationService:
    """Build public vacancy application service dependency."""
    return VacancyApplicationService(
        settings=settings,
        vacancy_dao=VacancyDAO(session=session),
        profile_dao=CandidateProfileDAO(session=session),
        document_dao=CandidateDocumentDAO(session=session),
        parsing_job_dao=CVParsingJobDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        storage=storage,
        audit_service=audit_service,
    )
