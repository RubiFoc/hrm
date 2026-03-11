"""Dependency providers for vacancy API services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from redis import Redis
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.infra.redis import get_redis_client
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.infra.minio import CandidateStorage
from hrm_backend.candidates.infra.postgres import (
    CandidateDocumentDAO,
    CandidateProfileDAO,
    CVParsingJobDAO,
)
from hrm_backend.core.db.session import get_db_session
from hrm_backend.employee.dependencies.employee import get_hire_conversion_service
from hrm_backend.interviews.dao.feedback_dao import InterviewFeedbackDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.public_apply_guard_dao import PublicApplyGuardDAO
from hrm_backend.vacancies.infra.postgres import OfferDAO, PipelineTransitionDAO, VacancyDAO
from hrm_backend.vacancies.services.application_service import VacancyApplicationService
from hrm_backend.vacancies.services.offer_service import OfferService
from hrm_backend.vacancies.services.public_apply_policy import PublicApplyPolicyService
from hrm_backend.vacancies.services.public_apply_rate_limiter import PublicApplyRateLimiter
from hrm_backend.vacancies.services.vacancy_service import VacancyService

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
CandidateStorageDependency = Annotated[CandidateStorage, Depends(get_candidate_storage)]
RedisClientDependency = Annotated[Redis, Depends(get_redis_client)]


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
    hire_conversion_service = get_hire_conversion_service(session=session)
    return VacancyService(
        session=session,
        vacancy_dao=VacancyDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        offer_dao=OfferDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        interview_dao=InterviewDAO(session=session),
        interview_feedback_dao=InterviewFeedbackDAO(session=session),
        hire_conversion_service=hire_conversion_service,
        audit_service=audit_service,
    )


def get_offer_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> OfferService:
    """Build offer service dependency."""
    return OfferService(
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        offer_dao=OfferDAO(session=session),
        audit_service=audit_service,
    )


def get_public_apply_guard_dao(session: SessionDependency) -> PublicApplyGuardDAO:
    """Build read-only anti-spam guard DAO for public apply policy."""
    return PublicApplyGuardDAO(session=session)


def get_public_apply_rate_limiter(
    settings: SettingsDependency,
    redis_client: RedisClientDependency,
) -> PublicApplyRateLimiter:
    """Build Redis-backed rate limiter for public apply endpoint."""
    return PublicApplyRateLimiter(
        redis_client=redis_client,
        key_prefix=settings.public_apply_rate_limit_redis_prefix,
        ip_limit=settings.public_apply_rate_limit_ip,
        ip_window_seconds=settings.public_apply_rate_limit_ip_window_seconds,
        ip_vacancy_limit=settings.public_apply_rate_limit_ip_vacancy,
        ip_vacancy_window_seconds=settings.public_apply_rate_limit_ip_vacancy_window_seconds,
        email_vacancy_limit=settings.public_apply_rate_limit_email_vacancy,
        email_vacancy_window_seconds=settings.public_apply_rate_limit_email_vacancy_window_seconds,
    )


def get_public_apply_policy_service(
    settings: SettingsDependency,
    guard_dao: Annotated[PublicApplyGuardDAO, Depends(get_public_apply_guard_dao)],
) -> PublicApplyPolicyService:
    """Build anti-spam policy service for public apply endpoint."""
    return PublicApplyPolicyService(
        guard_dao=guard_dao,
        email_cooldown_seconds=settings.public_apply_email_cooldown_seconds,
        dedup_window_seconds=settings.public_apply_dedup_window_seconds,
    )


def get_vacancy_application_service(
    settings: SettingsDependency,
    session: SessionDependency,
    storage: CandidateStorageDependency,
    audit_service: AuditDependency,
    rate_limiter: Annotated[PublicApplyRateLimiter, Depends(get_public_apply_rate_limiter)],
    policy_service: Annotated[PublicApplyPolicyService, Depends(get_public_apply_policy_service)],
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
        rate_limiter=rate_limiter,
        policy_service=policy_service,
    )
