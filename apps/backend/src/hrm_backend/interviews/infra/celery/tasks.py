"""Celery tasks for asynchronous interview calendar synchronization."""

from __future__ import annotations

from celery import Task

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.core.db.session import get_session_factory
from hrm_backend.interviews.dao.calendar_binding_dao import InterviewCalendarBindingDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.infra.celery.app import celery_app
from hrm_backend.interviews.infra.google_calendar.adapter import GoogleCalendarAdapter
from hrm_backend.interviews.services.interview_sync_worker_service import InterviewSyncWorkerService
from hrm_backend.interviews.utils.tokens import InterviewTokenManager
from hrm_backend.settings import get_settings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO


@celery_app.task(bind=True, name="interviews.process_interview_sync", max_retries=10)
def process_interview_sync(self: Task, interview_id: str) -> str:
    """Process one interview sync row by interview id."""
    del self
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    session = session_factory()
    try:
        worker = InterviewSyncWorkerService(
            settings=settings,
            interview_dao=InterviewDAO(session=session),
            binding_dao=InterviewCalendarBindingDAO(session=session),
            vacancy_dao=VacancyDAO(session=session),
            candidate_profile_dao=CandidateProfileDAO(session=session),
            transition_dao=PipelineTransitionDAO(session=session),
            calendar_adapter=GoogleCalendarAdapter(
                enabled=settings.google_calendar_enabled,
                service_account_key_path=settings.google_calendar_service_account_key_path,
                staff_calendar_map=settings.interview_staff_calendar_map,
            ),
            token_manager=InterviewTokenManager(
                secret=settings.interview_public_token_secret or settings.jwt_secret,
            ),
            audit_service=AuditService(dao=AuditEventDAO(session=session)),
        )
        return worker.process_interview_by_id(interview_id=interview_id).status
    finally:
        session.close()
