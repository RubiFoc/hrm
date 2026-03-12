"""Business service for scoring API workflows and response mapping."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.scoring.dao.match_score_artifact_dao import MatchScoreArtifactDAO
from hrm_backend.scoring.dao.match_scoring_job_dao import MatchScoringJobDAO
from hrm_backend.scoring.infra.celery.dispatch import enqueue_match_scoring
from hrm_backend.scoring.models.score_artifact import MatchScoreArtifact
from hrm_backend.scoring.models.scoring_job import MatchScoringJob
from hrm_backend.scoring.schemas.match_scoring import (
    MatchScoreCreateRequest,
    MatchScoreEvidenceResponse,
    MatchScoreListResponse,
    MatchScoreResponse,
)
from hrm_backend.scoring.services.manual_review_policy import (
    evaluate_manual_review_requirement,
)
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO


class MatchScoringService:
    """Orchestrates explicit scoring requests and score retrieval endpoints."""

    def __init__(
        self,
        *,
        vacancy_dao: VacancyDAO,
        candidate_profile_dao: CandidateProfileDAO,
        document_dao: CandidateDocumentDAO,
        scoring_job_dao: MatchScoringJobDAO,
        score_artifact_dao: MatchScoreArtifactDAO,
        audit_service: AuditService,
        low_confidence_threshold: float,
    ) -> None:
        """Initialize scoring service dependencies."""
        self._vacancy_dao = vacancy_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._document_dao = document_dao
        self._scoring_job_dao = scoring_job_dao
        self._score_artifact_dao = score_artifact_dao
        self._audit_service = audit_service
        self._low_confidence_threshold = low_confidence_threshold

    def request_score(
        self,
        *,
        vacancy_id: UUID,
        payload: MatchScoreCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> MatchScoreResponse:
        """Enqueue scoring or return existing latest job for one vacancy+candidate pair."""
        vacancy_id_str = str(vacancy_id)
        candidate_id_str = str(payload.candidate_id)
        self._get_vacancy_or_404(vacancy_id_str)
        self._get_candidate_or_404(candidate_id_str)
        document = self._get_ready_document_or_409(candidate_id_str)
        latest_job = self._scoring_job_dao.get_latest_for_pair(
            vacancy_id=vacancy_id_str,
            candidate_id=candidate_id_str,
        )

        if (
            latest_job is None
            or latest_job.document_id != document.document_id
            or latest_job.status == "failed"
        ):
            latest_job = self._scoring_job_dao.create_queued_job(
                vacancy_id=vacancy_id_str,
                candidate_id=candidate_id_str,
                document_id=document.document_id,
            )
            enqueue_match_scoring(job_id=latest_job.job_id)

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="match_score:create",
            resource_type="match_score",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=f"{vacancy_id_str}:{candidate_id_str}",
        )
        return self._build_response(latest_job)

    def list_scores(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID | None,
        auth_context: AuthContext,
        request: Request,
    ) -> MatchScoreListResponse:
        """List latest score/status rows for one vacancy, optionally narrowed to one candidate."""
        vacancy_id_str = str(vacancy_id)
        self._get_vacancy_or_404(vacancy_id_str)
        candidate_id_str = None if candidate_id is None else str(candidate_id)
        if candidate_id_str is not None:
            self._get_candidate_or_404(candidate_id_str)

        jobs = self._scoring_job_dao.list_latest_for_vacancy(
            vacancy_id=vacancy_id_str,
            candidate_id=candidate_id_str,
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="match_score:read",
            resource_type="match_score",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=vacancy_id_str,
        )
        return MatchScoreListResponse(items=[self._build_response(job) for job in jobs])

    def get_score(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> MatchScoreResponse:
        """Return latest score/status payload for one candidate in one vacancy."""
        vacancy_id_str = str(vacancy_id)
        candidate_id_str = str(candidate_id)
        self._get_vacancy_or_404(vacancy_id_str)
        self._get_candidate_or_404(candidate_id_str)

        job = self._scoring_job_dao.get_latest_for_pair(
            vacancy_id=vacancy_id_str,
            candidate_id=candidate_id_str,
        )
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Match score not found",
            )

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="match_score:read",
            resource_type="match_score",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=f"{vacancy_id_str}:{candidate_id_str}",
        )
        return self._build_response(job)

    def _build_response(self, job: MatchScoringJob) -> MatchScoreResponse:
        """Map one job row and optional artifact into the UI contract."""
        artifact = self._score_artifact_dao.get_by_job_id(job.job_id)
        confidence = None if artifact is None else artifact.confidence
        decision = evaluate_manual_review_requirement(
            status=job.status,  # type: ignore[arg-type]
            confidence=confidence,
            threshold=self._low_confidence_threshold,
        )
        return MatchScoreResponse(
            vacancy_id=UUID(job.vacancy_id),
            candidate_id=UUID(job.candidate_id),
            status=job.status,  # type: ignore[arg-type]
            score=None if artifact is None else artifact.score,
            confidence=confidence,
            requires_manual_review=decision.requires_manual_review,
            manual_review_reason=decision.manual_review_reason,
            confidence_threshold=decision.confidence_threshold,
            summary=None if artifact is None else artifact.summary,
            matched_requirements=[]
            if artifact is None
            else list(artifact.matched_requirements_json or []),
            missing_requirements=[]
            if artifact is None
            else list(artifact.missing_requirements_json or []),
            evidence=self._build_evidence_payload(artifact),
            scored_at=None if artifact is None else artifact.scored_at,
            model_name=None if artifact is None else artifact.model_name,
            model_version=None if artifact is None else artifact.model_version,
        )

    def _build_evidence_payload(
        self,
        artifact: MatchScoreArtifact | None,
    ) -> list[MatchScoreEvidenceResponse]:
        """Map stored evidence JSON into API response models."""
        if artifact is None:
            return []
        items: list[MatchScoreEvidenceResponse] = []
        for item in artifact.evidence_json or []:
            if not isinstance(item, dict):
                continue
            requirement = str(item.get("requirement", "")).strip()
            snippet = str(item.get("snippet", "")).strip()
            if not requirement or not snippet:
                continue
            source_field = item.get("source_field")
            normalized_source = None if source_field is None else str(source_field).strip() or None
            items.append(
                MatchScoreEvidenceResponse(
                    requirement=requirement,
                    snippet=snippet,
                    source_field=normalized_source,
                )
            )
        return items

    def _get_vacancy_or_404(self, vacancy_id: str):
        """Load vacancy or raise 404."""
        vacancy = self._vacancy_dao.get_by_id(vacancy_id)
        if vacancy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")
        return vacancy

    def _get_candidate_or_404(self, candidate_id: str):
        """Load candidate profile or raise 404."""
        candidate = self._candidate_profile_dao.get_by_id(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
        return candidate

    def _get_ready_document_or_409(self, candidate_id: str):
        """Load active parsed document or reject scoring with 409."""
        document = self._document_dao.get_active_document(candidate_id)
        if (
            document is None
            or document.parsed_profile_json is None
            or document.evidence_json is None
            or document.parsed_at is None
        ):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="CV analysis is not ready",
            )
        return document
