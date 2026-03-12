"""Dependency providers for scoring API and worker services."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.core.db.session import get_db_session
from hrm_backend.scoring.dao.match_score_artifact_dao import MatchScoreArtifactDAO
from hrm_backend.scoring.dao.match_scoring_job_dao import MatchScoringJobDAO
from hrm_backend.scoring.infra.ollama.adapter import MatchScoringAdapter, OllamaMatchScoringAdapter
from hrm_backend.scoring.services.match_scoring_service import MatchScoringService
from hrm_backend.scoring.services.match_scoring_worker_service import MatchScoringWorkerService
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]


@lru_cache(maxsize=4)
def _build_match_scoring_adapter(
    base_url: str,
    model_name: str,
    timeout_seconds: int,
) -> MatchScoringAdapter:
    """Build cached Ollama scoring adapter per configuration tuple."""
    return OllamaMatchScoringAdapter(
        base_url=base_url,
        model_name=model_name,
        timeout_seconds=timeout_seconds,
    )


def get_match_scoring_adapter(settings: SettingsDependency) -> MatchScoringAdapter:
    """Provide Ollama adapter for match scoring."""
    return _build_match_scoring_adapter(
        base_url=settings.ollama_base_url,
        model_name=settings.match_scoring_model_name,
        timeout_seconds=settings.match_scoring_request_timeout_seconds,
    )


def get_match_scoring_service(
    settings: SettingsDependency,
    session: SessionDependency,
    audit_service: AuditDependency,
) -> MatchScoringService:
    """Build scoring API service dependency."""
    return MatchScoringService(
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        document_dao=CandidateDocumentDAO(session=session),
        scoring_job_dao=MatchScoringJobDAO(session=session),
        score_artifact_dao=MatchScoreArtifactDAO(session=session),
        audit_service=audit_service,
        low_confidence_threshold=settings.scoring_low_confidence_threshold,
    )


def get_match_scoring_worker_service(
    settings: SettingsDependency,
    session: SessionDependency,
    adapter: Annotated[MatchScoringAdapter, Depends(get_match_scoring_adapter)],
    audit_service: AuditDependency,
) -> MatchScoringWorkerService:
    """Build worker service dependency for match scoring loop."""
    return MatchScoringWorkerService(
        settings=settings,
        scoring_job_dao=MatchScoringJobDAO(session=session),
        score_artifact_dao=MatchScoreArtifactDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        document_dao=CandidateDocumentDAO(session=session),
        adapter=adapter,
        audit_service=audit_service,
    )
