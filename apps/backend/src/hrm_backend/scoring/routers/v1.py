"""Versioned HTTP routes for match scoring and shortlist review."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.rbac import Role, require_permission
from hrm_backend.scoring.dependencies.scoring import get_match_scoring_service
from hrm_backend.scoring.schemas.match_scoring import (
    MatchScoreCreateRequest,
    MatchScoreListResponse,
    MatchScoreResponse,
)
from hrm_backend.scoring.services.match_scoring_service import MatchScoringService

router = APIRouter(tags=["match-scoring"])
MatchScoringServiceDependency = Annotated[MatchScoringService, Depends(get_match_scoring_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
MatchScoreCreateRole = Annotated[Role, Depends(require_permission("match_score:create"))]
MatchScoreReadRole = Annotated[Role, Depends(require_permission("match_score:read"))]


@router.post(
    "/api/v1/vacancies/{vacancy_id}/match-scores",
    response_model=MatchScoreResponse,
    responses={409: {"description": "CV analysis is not ready"}},
)
def create_match_score(
    vacancy_id: UUID,
    request: Request,
    payload: MatchScoreCreateRequest,
    _: MatchScoreCreateRole,
    auth_context: CurrentAuthContext,
    service: MatchScoringServiceDependency,
) -> MatchScoreResponse:
    """Enqueue scoring or return existing latest score job for one candidate."""
    return service.request_score(
        vacancy_id=vacancy_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.get("/api/v1/vacancies/{vacancy_id}/match-scores", response_model=MatchScoreListResponse)
def list_match_scores(
    vacancy_id: UUID,
    request: Request,
    _: MatchScoreReadRole,
    auth_context: CurrentAuthContext,
    service: MatchScoringServiceDependency,
    candidate_id: UUID | None = None,
) -> MatchScoreListResponse:
    """List latest score/status entries for one vacancy."""
    return service.list_scores(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@router.get(
    "/api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}",
    response_model=MatchScoreResponse,
)
def get_match_score(
    vacancy_id: UUID,
    candidate_id: UUID,
    request: Request,
    _: MatchScoreReadRole,
    auth_context: CurrentAuthContext,
    service: MatchScoringServiceDependency,
) -> MatchScoreResponse:
    """Load latest score/status payload for one candidate in one vacancy."""
    return service.get_score(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )

