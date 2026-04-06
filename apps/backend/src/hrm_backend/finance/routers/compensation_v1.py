"""Versioned HTTP routes for compensation controls."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.finance.dependencies.compensation import get_compensation_service
from hrm_backend.finance.schemas.compensation import (
    BonusEntryResponse,
    BonusUpsertRequest,
    CompensationRaiseCreateRequest,
    CompensationRaiseDecisionRequest,
    CompensationRaiseListResponse,
    CompensationRaiseResponse,
    CompensationRaiseStatus,
    CompensationTableListResponse,
    SalaryBandCreateRequest,
    SalaryBandListResponse,
    SalaryBandResponse,
)
from hrm_backend.finance.services.compensation_service import CompensationService
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/compensation", tags=["compensation"])

CompensationServiceDependency = Annotated[
    CompensationService,
    Depends(get_compensation_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
CompensationReadRole = Annotated[Role, Depends(require_permission("compensation:read"))]
RaiseCreateRole = Annotated[Role, Depends(require_permission("compensation_raise:create"))]
RaiseConfirmRole = Annotated[Role, Depends(require_permission("compensation_raise:confirm"))]
RaiseReadRole = Annotated[Role, Depends(require_permission("compensation_raise:read"))]
RaiseApproveRole = Annotated[Role, Depends(require_permission("compensation_raise:approve"))]
RaiseRejectRole = Annotated[Role, Depends(require_permission("compensation_raise:reject"))]
SalaryBandWriteRole = Annotated[Role, Depends(require_permission("salary_band:write"))]
BonusWriteRole = Annotated[Role, Depends(require_permission("bonus:write"))]
CompLimitQuery = Annotated[int, Query(ge=1, le=100)]
CompOffsetQuery = Annotated[int, Query(ge=0)]


@router.get(
    "/table",
    response_model=CompensationTableListResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
    },
)
def list_compensation_table(
    request: Request,
    _: CompensationReadRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
    limit: CompLimitQuery = 20,
    offset: CompOffsetQuery = 0,
) -> CompensationTableListResponse:
    """List compensation table rows visible to the current actor."""
    return service.list_compensation_table(
        auth_context=auth_context,
        request=request,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/raises",
    response_model=CompensationRaiseListResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
    },
)
def list_raise_requests(
    request: Request,
    _: RaiseReadRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
    status_filter: Annotated[CompensationRaiseStatus | None, Query(alias="status")] = None,
    limit: CompLimitQuery = 20,
    offset: CompOffsetQuery = 0,
) -> CompensationRaiseListResponse:
    """List raise requests for manager or leader workflows."""
    return service.list_raise_requests(
        auth_context=auth_context,
        request=request,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@router.post(
    "/raises",
    response_model=CompensationRaiseResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_404_NOT_FOUND: {"description": "Employee not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def create_raise_request(
    request: Request,
    payload: CompensationRaiseCreateRequest,
    _: RaiseCreateRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
) -> CompensationRaiseResponse:
    """Create a manager-initiated raise request."""
    return service.create_raise_request(
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/raises/{raise_request_id}/confirm",
    response_model=CompensationRaiseResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_404_NOT_FOUND: {"description": "Raise request not found"},
        status.HTTP_409_CONFLICT: {"description": "Confirmation conflict"},
    },
)
def confirm_raise_request(
    raise_request_id: UUID,
    request: Request,
    _: RaiseConfirmRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
) -> CompensationRaiseResponse:
    """Confirm a raise request as manager."""
    return service.confirm_raise_request(
        request_id=str(raise_request_id),
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/raises/{raise_request_id}/approve",
    response_model=CompensationRaiseResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_404_NOT_FOUND: {"description": "Raise request not found"},
        status.HTTP_409_CONFLICT: {"description": "Approval conflict"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def approve_raise_request(
    raise_request_id: UUID,
    request: Request,
    payload: CompensationRaiseDecisionRequest,
    _: RaiseApproveRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
) -> CompensationRaiseResponse:
    """Approve a raise request after quorum is reached."""
    return service.approve_raise_request(
        request_id=str(raise_request_id),
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/raises/{raise_request_id}/reject",
    response_model=CompensationRaiseResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_404_NOT_FOUND: {"description": "Raise request not found"},
        status.HTTP_409_CONFLICT: {"description": "Decision conflict"},
    },
)
def reject_raise_request(
    raise_request_id: UUID,
    request: Request,
    payload: CompensationRaiseDecisionRequest,
    _: RaiseRejectRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
) -> CompensationRaiseResponse:
    """Reject a raise request after quorum is reached."""
    return service.reject_raise_request(
        request_id=str(raise_request_id),
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.get(
    "/salary-bands",
    response_model=SalaryBandListResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
    },
)
def list_salary_bands(
    vacancy_id: Annotated[UUID, Query()],
    _: SalaryBandWriteRole,
    service: CompensationServiceDependency,
) -> SalaryBandListResponse:
    """List salary-band history for one vacancy."""
    return service.list_salary_bands(vacancy_id=str(vacancy_id))


@router.post(
    "/salary-bands",
    response_model=SalaryBandResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_404_NOT_FOUND: {"description": "Vacancy not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def create_salary_band(
    request: Request,
    payload: SalaryBandCreateRequest,
    _: SalaryBandWriteRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
) -> SalaryBandResponse:
    """Create a new vacancy salary band entry."""
    return service.create_salary_band(
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/bonuses",
    response_model=BonusEntryResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_404_NOT_FOUND: {"description": "Employee not found"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def upsert_bonus_entry(
    request: Request,
    payload: BonusUpsertRequest,
    _: BonusWriteRole,
    auth_context: CurrentAuthContext,
    service: CompensationServiceDependency,
) -> BonusEntryResponse:
    """Create or update a manual bonus entry."""
    return service.upsert_bonus_entry(
        payload=payload,
        auth_context=auth_context,
        request=request,
    )
