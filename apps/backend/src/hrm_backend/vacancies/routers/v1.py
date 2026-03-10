"""Versioned HTTP routes for vacancy and pipeline management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.rbac import Role, require_permission
from hrm_backend.vacancies.dependencies.vacancies import (
    get_offer_service,
    get_vacancy_application_service,
    get_vacancy_service,
)
from hrm_backend.vacancies.schemas.offer import (
    OfferDecisionRequest,
    OfferResponse,
    OfferUpsertRequest,
)
from hrm_backend.vacancies.schemas.application import PublicVacancyApplicationResponse
from hrm_backend.vacancies.schemas.pipeline import (
    PipelineTransitionCreateRequest,
    PipelineTransitionListResponse,
    PipelineTransitionResponse,
)
from hrm_backend.vacancies.schemas.vacancy import (
    VacancyCreateRequest,
    VacancyListResponse,
    VacancyResponse,
    VacancyUpdateRequest,
)
from hrm_backend.vacancies.services.offer_service import OfferService
from hrm_backend.vacancies.services.application_service import VacancyApplicationService
from hrm_backend.vacancies.services.vacancy_service import VacancyService

router = APIRouter(tags=["vacancies"])
VacancyServiceDependency = Annotated[VacancyService, Depends(get_vacancy_service)]
OfferServiceDependency = Annotated[OfferService, Depends(get_offer_service)]
VacancyApplicationServiceDependency = Annotated[
    VacancyApplicationService,
    Depends(get_vacancy_application_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
VacancyCreateRole = Annotated[Role, Depends(require_permission("vacancy:create"))]
VacancyReadRole = Annotated[Role, Depends(require_permission("vacancy:read"))]
VacancyUpdateRole = Annotated[Role, Depends(require_permission("vacancy:update"))]
PipelineTransitionRole = Annotated[Role, Depends(require_permission("pipeline:transition"))]
PipelineReadRole = Annotated[Role, Depends(require_permission("pipeline:read"))]


@router.post("/api/v1/vacancies", response_model=VacancyResponse)
def create_vacancy(
    request: Request,
    payload: VacancyCreateRequest,
    _: VacancyCreateRole,
    auth_context: CurrentAuthContext,
    service: VacancyServiceDependency,
) -> VacancyResponse:
    """Create vacancy resource."""
    return service.create_vacancy(payload=payload, auth_context=auth_context, request=request)


@router.get("/api/v1/vacancies", response_model=VacancyListResponse)
def list_vacancies(
    request: Request,
    _: VacancyReadRole,
    auth_context: CurrentAuthContext,
    service: VacancyServiceDependency,
) -> VacancyListResponse:
    """List vacancy resources."""
    return service.list_vacancies(auth_context=auth_context, request=request)


@router.get("/api/v1/vacancies/{vacancy_id}", response_model=VacancyResponse)
def get_vacancy(
    vacancy_id: UUID,
    request: Request,
    _: VacancyReadRole,
    auth_context: CurrentAuthContext,
    service: VacancyServiceDependency,
) -> VacancyResponse:
    """Load one vacancy resource by identifier."""
    return service.get_vacancy(vacancy_id=vacancy_id, auth_context=auth_context, request=request)


@router.patch("/api/v1/vacancies/{vacancy_id}", response_model=VacancyResponse)
def patch_vacancy(
    vacancy_id: UUID,
    payload: VacancyUpdateRequest,
    request: Request,
    _: VacancyUpdateRole,
    auth_context: CurrentAuthContext,
    service: VacancyServiceDependency,
) -> VacancyResponse:
    """Patch one vacancy resource."""
    return service.update_vacancy(
        vacancy_id=vacancy_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.post("/api/v1/pipeline/transitions", response_model=PipelineTransitionResponse)
def create_pipeline_transition(
    request: Request,
    payload: PipelineTransitionCreateRequest,
    _: PipelineTransitionRole,
    auth_context: CurrentAuthContext,
    service: VacancyServiceDependency,
) -> PipelineTransitionResponse:
    """Append one candidate pipeline transition event."""
    return service.transition_pipeline(payload=payload, auth_context=auth_context, request=request)


@router.get("/api/v1/pipeline/transitions", response_model=PipelineTransitionListResponse)
def list_pipeline_transitions(
    vacancy_id: UUID,
    candidate_id: UUID,
    request: Request,
    _: PipelineReadRole,
    auth_context: CurrentAuthContext,
    service: VacancyServiceDependency,
) -> PipelineTransitionListResponse:
    """Return ordered pipeline transition history for one vacancy+candidate pair."""
    return service.list_pipeline_transitions(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@router.get(
    "/api/v1/vacancies/{vacancy_id}/offers/{candidate_id}",
    response_model=OfferResponse,
)
def get_offer(
    vacancy_id: UUID,
    candidate_id: UUID,
    request: Request,
    _: PipelineReadRole,
    auth_context: CurrentAuthContext,
    service: OfferServiceDependency,
) -> OfferResponse:
    """Read current offer lifecycle state for one vacancy+candidate pair."""
    return service.get_offer(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@router.put(
    "/api/v1/vacancies/{vacancy_id}/offers/{candidate_id}",
    response_model=OfferResponse,
)
def put_offer(
    vacancy_id: UUID,
    candidate_id: UUID,
    payload: OfferUpsertRequest,
    request: Request,
    _: PipelineTransitionRole,
    auth_context: CurrentAuthContext,
    service: OfferServiceDependency,
) -> OfferResponse:
    """Create or update draft offer fields for one vacancy+candidate pair."""
    return service.upsert_offer_draft(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/offers/{candidate_id}/send",
    response_model=OfferResponse,
)
def send_offer(
    vacancy_id: UUID,
    candidate_id: UUID,
    request: Request,
    _: PipelineTransitionRole,
    auth_context: CurrentAuthContext,
    service: OfferServiceDependency,
) -> OfferResponse:
    """Move one draft offer to `sent`."""
    return service.send_offer(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/offers/{candidate_id}/accept",
    response_model=OfferResponse,
)
def accept_offer(
    vacancy_id: UUID,
    candidate_id: UUID,
    request: Request,
    _: PipelineTransitionRole,
    auth_context: CurrentAuthContext,
    service: OfferServiceDependency,
    payload: OfferDecisionRequest | None = None,
) -> OfferResponse:
    """Record accepted status for one sent offer."""
    return service.accept_offer(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        payload=payload or OfferDecisionRequest(),
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/offers/{candidate_id}/decline",
    response_model=OfferResponse,
)
def decline_offer(
    vacancy_id: UUID,
    candidate_id: UUID,
    request: Request,
    _: PipelineTransitionRole,
    auth_context: CurrentAuthContext,
    service: OfferServiceDependency,
    payload: OfferDecisionRequest | None = None,
) -> OfferResponse:
    """Record declined status for one sent offer."""
    return service.decline_offer(
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        payload=payload or OfferDecisionRequest(),
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/applications",
    response_model=PublicVacancyApplicationResponse,
    responses={
        409: {"description": "Duplicate submission or active cooldown"},
        429: {
            "description": "Too many requests",
            "headers": {
                "Retry-After": {
                    "description": "Seconds before next retry",
                    "schema": {"type": "string"},
                },
                "X-RateLimit-Limit": {
                    "description": "Bucket limit",
                    "schema": {"type": "string"},
                },
                "X-RateLimit-Remaining": {
                    "description": "Remaining requests in current window",
                    "schema": {"type": "string"},
                },
                "X-RateLimit-Reset": {
                    "description": "Unix epoch timestamp for limit reset",
                    "schema": {"type": "string"},
                },
            },
        },
    },
)
async def apply_to_vacancy_public(
    vacancy_id: UUID,
    request: Request,
    first_name: Annotated[str, Form(min_length=1, max_length=128)],
    last_name: Annotated[str, Form(min_length=1, max_length=128)],
    email: Annotated[str, Form(min_length=3, max_length=256)],
    phone: Annotated[str, Form(min_length=3, max_length=64)],
    checksum_sha256: Annotated[str, Form(min_length=64, max_length=64)],
    file: Annotated[UploadFile, File(...)],
    service: VacancyApplicationServiceDependency,
    location: Annotated[str | None, Form(max_length=256)] = None,
    current_title: Annotated[str | None, Form(max_length=256)] = None,
    extra_data: Annotated[str | None, Form()] = None,
    website: Annotated[str | None, Form(max_length=256)] = None,
) -> PublicVacancyApplicationResponse:
    """Submit public candidate application with CV to target vacancy."""
    return await service.apply_public(
        vacancy_id=vacancy_id,
        first_name=first_name,
        last_name=last_name,
        email=email,
        phone=phone,
        location=location,
        current_title=current_title,
        extra_data_raw=extra_data,
        file=file,
        checksum_sha256=checksum_sha256,
        website=website,
        request=request,
    )
