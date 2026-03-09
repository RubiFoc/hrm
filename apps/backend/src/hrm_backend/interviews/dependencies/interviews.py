"""Dependency providers for interview scheduling API and worker services."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.core.db.session import get_db_session
from hrm_backend.interviews.dao.calendar_binding_dao import InterviewCalendarBindingDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.infra.google_calendar import (
    GoogleCalendarAdapter,
    InterviewCalendarAdapter,
)
from hrm_backend.interviews.services.interview_service import InterviewService
from hrm_backend.interviews.services.interview_sync_worker_service import (
    InterviewSyncWorkerService,
)
from hrm_backend.interviews.utils.tokens import InterviewTokenManager
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]


@lru_cache(maxsize=4)
def _build_interview_calendar_adapter(
    *,
    enabled: bool,
    service_account_key_path: str | None,
    staff_calendar_items: tuple[tuple[str, str], ...],
) -> InterviewCalendarAdapter:
    """Build cached calendar adapter per stable configuration tuple."""
    return GoogleCalendarAdapter(
        enabled=enabled,
        service_account_key_path=service_account_key_path,
        staff_calendar_map=dict(staff_calendar_items),
    )


def get_interview_calendar_adapter(settings: SettingsDependency) -> InterviewCalendarAdapter:
    """Provide configured interview calendar adapter."""
    return _build_interview_calendar_adapter(
        enabled=settings.google_calendar_enabled,
        service_account_key_path=settings.google_calendar_service_account_key_path,
        staff_calendar_items=tuple(
            sorted(settings.interview_staff_calendar_map.items())
        ),
    )


def get_interview_token_manager(settings: SettingsDependency) -> InterviewTokenManager:
    """Provide token manager for interview invitation URLs."""
    secret = settings.interview_public_token_secret or settings.jwt_secret
    return InterviewTokenManager(secret=secret)


def get_interview_service(
    settings: SettingsDependency,
    session: SessionDependency,
    audit_service: AuditDependency,
    calendar_adapter: Annotated[
        InterviewCalendarAdapter, Depends(get_interview_calendar_adapter)
    ],
    token_manager: Annotated[InterviewTokenManager, Depends(get_interview_token_manager)],
) -> InterviewService:
    """Build interview API service dependency."""
    return InterviewService(
        settings=settings,
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        interview_dao=InterviewDAO(session=session),
        binding_dao=InterviewCalendarBindingDAO(session=session),
        calendar_adapter=calendar_adapter,
        token_manager=token_manager,
        audit_service=audit_service,
    )


def get_interview_sync_worker_service(
    settings: SettingsDependency,
    session: SessionDependency,
    audit_service: AuditDependency,
    calendar_adapter: Annotated[
        InterviewCalendarAdapter, Depends(get_interview_calendar_adapter)
    ],
    token_manager: Annotated[InterviewTokenManager, Depends(get_interview_token_manager)],
) -> InterviewSyncWorkerService:
    """Build interview worker service dependency."""
    return InterviewSyncWorkerService(
        settings=settings,
        interview_dao=InterviewDAO(session=session),
        binding_dao=InterviewCalendarBindingDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        calendar_adapter=calendar_adapter,
        token_manager=token_manager,
        audit_service=audit_service,
    )
