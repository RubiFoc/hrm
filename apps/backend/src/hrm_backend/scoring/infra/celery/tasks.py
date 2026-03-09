"""Celery tasks for asynchronous match scoring lifecycle."""

from __future__ import annotations

from celery import Task

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.core.db.session import get_session_factory
from hrm_backend.scoring.dao.match_score_artifact_dao import MatchScoreArtifactDAO
from hrm_backend.scoring.dao.match_scoring_job_dao import MatchScoringJobDAO
from hrm_backend.scoring.infra.celery.app import celery_app
from hrm_backend.scoring.infra.ollama.adapter import OllamaMatchScoringAdapter
from hrm_backend.scoring.services.match_scoring_worker_service import MatchScoringWorkerService
from hrm_backend.settings import get_settings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO


@celery_app.task(bind=True, name="scoring.process_match_scoring_job", max_retries=50)
def process_match_scoring_job(self: Task, job_id: str) -> str:
    """Process one `match_scoring_jobs` row by job id with controlled retries."""
    settings = get_settings()
    session_factory = get_session_factory(settings.database_url)
    session = session_factory()
    try:
        worker = MatchScoringWorkerService(
            settings=settings,
            scoring_job_dao=MatchScoringJobDAO(session=session),
            score_artifact_dao=MatchScoreArtifactDAO(session=session),
            vacancy_dao=VacancyDAO(session=session),
            candidate_profile_dao=CandidateProfileDAO(session=session),
            document_dao=CandidateDocumentDAO(session=session),
            adapter=OllamaMatchScoringAdapter(
                base_url=settings.ollama_base_url,
                model_name=settings.match_scoring_model_name,
                timeout_seconds=settings.match_scoring_request_timeout_seconds,
            ),
            audit_service=AuditService(dao=AuditEventDAO(session=session)),
        )
        result = worker.process_job_by_id(job_id=job_id)
        if result.status == "failed" and result.can_retry:
            raise self.retry(countdown=2)
        return result.status
    finally:
        session.close()
