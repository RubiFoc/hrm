"""Versioned HTTP routes for candidate profile and CV workflows."""

from __future__ import annotations

from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dependencies.candidates import get_candidate_service
from hrm_backend.candidates.schemas.cv import CandidateCVUploadResponse
from hrm_backend.candidates.schemas.parsing import CVAnalysisResponse, CVParsingStatusResponse
from hrm_backend.candidates.schemas.profile import (
    CandidateCreateRequest,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdateRequest,
)
from hrm_backend.candidates.services.candidate_service import CandidateService
from hrm_backend.rbac import Role, require_permission
from hrm_backend.vacancies.schemas.pipeline import PipelineStage

router = APIRouter(prefix="/api/v1/candidates", tags=["candidates"])
public_router = APIRouter(prefix="/api/v1/public/cv-parsing-jobs", tags=["candidates"])
CandidateServiceDependency = Annotated[CandidateService, Depends(get_candidate_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
CandidateCreateRole = Annotated[Role, Depends(require_permission("candidate_profile:create"))]
CandidateReadRole = Annotated[Role, Depends(require_permission("candidate_profile:read"))]
CandidateUpdateRole = Annotated[Role, Depends(require_permission("candidate_profile:update"))]
CandidateListRole = Annotated[Role, Depends(require_permission("candidate_profile:list"))]
CandidateCVUploadRole = Annotated[Role, Depends(require_permission("candidate_cv:upload"))]
CandidateCVReadRole = Annotated[Role, Depends(require_permission("candidate_cv:read"))]
CandidateCVStatusRole = Annotated[Role, Depends(require_permission("candidate_cv:parsing_status"))]
CandidateSearchQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
CandidateLocationQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
CandidateCurrentTitleQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
CandidateSkillQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
CandidateAnalysisReadyQuery = Annotated[bool | None, Query()]
CandidateMinYearsExperienceQuery = Annotated[float | None, Query(ge=0)]
CandidateVacancyQuery = Annotated[UUID | None, Query()]
CandidateInPipelineOnlyQuery = Annotated[bool, Query()]
CandidateStageQuery = Annotated[PipelineStage | None, Query()]


@router.post("", response_model=CandidateResponse)
def create_candidate_profile(
    request: Request,
    payload: CandidateCreateRequest,
    _: CandidateCreateRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
) -> CandidateResponse:
    """Create candidate profile resource.

    Args:
        request: HTTP request context.
        payload: Candidate create request.
        _: RBAC validated role marker.
        auth_context: Authenticated actor context.
        service: Candidate domain service.

    Returns:
        CandidateResponse: Created profile payload.
    """
    return service.create_profile(payload=payload, auth_context=auth_context, request=request)


@router.get("/{candidate_id}", response_model=CandidateResponse)
def get_candidate_profile(
    candidate_id: UUID,
    request: Request,
    _: CandidateReadRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
) -> CandidateResponse:
    """Get one candidate profile by identifier."""
    return service.get_profile(
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def patch_candidate_profile(
    candidate_id: UUID,
    payload: CandidateUpdateRequest,
    request: Request,
    _: CandidateUpdateRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
) -> CandidateResponse:
    """Patch one candidate profile by identifier."""
    return service.update_profile(
        candidate_id=candidate_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.get("", response_model=CandidateListResponse)
def list_candidate_profiles(
    request: Request,
    _: CandidateListRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: CandidateSearchQuery = None,
    location: CandidateLocationQuery = None,
    current_title: CandidateCurrentTitleQuery = None,
    skill: CandidateSkillQuery = None,
    analysis_ready: CandidateAnalysisReadyQuery = None,
    min_years_experience: CandidateMinYearsExperienceQuery = None,
    vacancy_id: CandidateVacancyQuery = None,
    in_pipeline_only: CandidateInPipelineOnlyQuery = False,
    stage: CandidateStageQuery = None,
) -> CandidateListResponse:
    """List candidate profiles with recruiter-facing search, filter, and pagination."""
    return service.list_profiles(
        auth_context=auth_context,
        request=request,
        limit=limit,
        offset=offset,
        search=search,
        location=location,
        current_title=current_title,
        skill=skill,
        analysis_ready=analysis_ready,
        min_years_experience=min_years_experience,
        vacancy_id=vacancy_id,
        in_pipeline_only=in_pipeline_only,
        stage=stage,
    )


@router.post("/{candidate_id}/cv", response_model=CandidateCVUploadResponse)
async def upload_candidate_cv(
    candidate_id: UUID,
    request: Request,
    checksum_sha256: Annotated[str, Form(min_length=64, max_length=64)],
    file: Annotated[UploadFile, File(...)],
    _: CandidateCVUploadRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
) -> CandidateCVUploadResponse:
    """Upload candidate CV file via backend multipart endpoint."""
    return await service.upload_cv(
        candidate_id=candidate_id,
        file=file,
        checksum_sha256=checksum_sha256,
        auth_context=auth_context,
        request=request,
    )


@router.get("/{candidate_id}/cv")
def download_candidate_cv(
    candidate_id: UUID,
    request: Request,
    _: CandidateCVReadRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
):
    """Download active candidate CV as attachment stream."""
    payload = service.download_cv(
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )
    response = StreamingResponse(BytesIO(payload.content), media_type=payload.mime_type)
    response.headers["Content-Disposition"] = f'attachment; filename="{payload.filename}"'
    return response


@router.get("/{candidate_id}/cv/parsing-status", response_model=CVParsingStatusResponse)
def get_candidate_cv_parsing_status(
    candidate_id: UUID,
    request: Request,
    _: CandidateCVStatusRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
) -> CVParsingStatusResponse:
    """Return latest asynchronous CV parsing status."""
    return service.get_parsing_status(
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@router.get("/{candidate_id}/cv/analysis", response_model=CVAnalysisResponse)
def get_candidate_cv_analysis(
    candidate_id: UUID,
    request: Request,
    _: CandidateCVStatusRole,
    auth_context: CurrentAuthContext,
    service: CandidateServiceDependency,
) -> CVAnalysisResponse:
    """Return structured CV analysis with evidence for latest active CV."""
    return service.get_cv_analysis(
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@public_router.get("/{job_id}", response_model=CVParsingStatusResponse)
def get_public_candidate_cv_parsing_status(
    job_id: UUID,
    request: Request,
    service: CandidateServiceDependency,
) -> CVParsingStatusResponse:
    """Return public parsing status for one anonymous candidate application."""
    return service.get_public_parsing_status(job_id=job_id, request=request)


@public_router.get("/{job_id}/analysis", response_model=CVAnalysisResponse)
def get_public_candidate_cv_analysis(
    job_id: UUID,
    request: Request,
    service: CandidateServiceDependency,
) -> CVAnalysisResponse:
    """Return public CV analysis for one anonymous candidate application."""
    return service.get_public_cv_analysis(job_id=job_id, request=request)
