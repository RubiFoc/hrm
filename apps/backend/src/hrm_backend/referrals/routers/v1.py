"""Versioned HTTP routes for employee referrals."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.rbac import Role, require_permission
from hrm_backend.referrals.dependencies.referrals import get_referral_service
from hrm_backend.referrals.schemas.referral import (
    ReferralListResponse,
    ReferralReviewRequest,
    ReferralReviewResponse,
    ReferralSubmitResponse,
)
from hrm_backend.referrals.services.referral_service import ReferralService

router = APIRouter(prefix="/api/v1/referrals", tags=["referrals"])
ReferralServiceDependency = Annotated[ReferralService, Depends(get_referral_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
ReferralCreateRole = Annotated[Role, Depends(require_permission("referral:create"))]
ReferralReadRole = Annotated[Role, Depends(require_permission("referral:read"))]
ReferralReviewRole = Annotated[Role, Depends(require_permission("referral:review"))]
ReferralLimitQuery = Annotated[int, Query(ge=1, le=100)]
ReferralOffsetQuery = Annotated[int, Query(ge=0)]


@router.post("", response_model=ReferralSubmitResponse)
async def submit_referral(
    request: Request,
    vacancy_id: Annotated[UUID, Form()],
    full_name: Annotated[str, Form(min_length=1, max_length=256)],
    phone: Annotated[str, Form(min_length=3, max_length=64)],
    email: Annotated[str, Form(min_length=3, max_length=256)],
    checksum_sha256: Annotated[str, Form(min_length=64, max_length=64)],
    file: Annotated[UploadFile, File(...)],
    _: ReferralCreateRole,
    auth_context: CurrentAuthContext,
    service: ReferralServiceDependency,
) -> ReferralSubmitResponse:
    """Submit an employee referral with candidate CV payload."""
    return await service.submit_referral(
        vacancy_id=vacancy_id,
        full_name=full_name,
        phone=phone,
        email=email,
        file=file,
        checksum_sha256=checksum_sha256,
        auth_context=auth_context,
        request=request,
    )


@router.get("", response_model=ReferralListResponse)
def list_referrals(
    request: Request,
    _: ReferralReadRole,
    auth_context: CurrentAuthContext,
    service: ReferralServiceDependency,
    vacancy_id: Annotated[UUID | None, Query()] = None,
    limit: ReferralLimitQuery = 20,
    offset: ReferralOffsetQuery = 0,
) -> ReferralListResponse:
    """List referrals visible to HR or manager roles."""
    return service.list_referrals(
        auth_context=auth_context,
        request=request,
        vacancy_id=vacancy_id,
        limit=limit,
        offset=offset,
    )


@router.post("/{referral_id}/review", response_model=ReferralReviewResponse)
def review_referral(
    referral_id: UUID,
    request: Request,
    payload: ReferralReviewRequest,
    _: ReferralReviewRole,
    auth_context: CurrentAuthContext,
    service: ReferralServiceDependency,
) -> ReferralReviewResponse:
    """Append a referral review transition."""
    return service.review_referral(
        referral_id=referral_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )
