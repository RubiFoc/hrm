"""Versioned HTTP routes for interview scheduling and public registration."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.interviews.dependencies.interviews import get_interview_service
from hrm_backend.interviews.schemas.interview import (
    HRInterviewListResponse,
    HRInterviewResponse,
    InterviewFeedbackItemResponse,
    InterviewFeedbackPanelSummaryResponse,
    InterviewFeedbackUpsertRequest,
    InterviewCancelRequest,
    InterviewCreateRequest,
    InterviewRescheduleRequest,
    InterviewStatus,
    PublicInterviewActionRequest,
    PublicInterviewRegistrationResponse,
)
from hrm_backend.interviews.services.interview_service import InterviewService
from hrm_backend.rbac import Role, require_permission

router = APIRouter(tags=["interviews"])
public_router = APIRouter(prefix="/api/v1/public/interview-registrations", tags=["interviews"])
InterviewServiceDependency = Annotated[InterviewService, Depends(get_interview_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
InterviewManageRole = Annotated[Role, Depends(require_permission("interview:manage"))]


@router.post("/api/v1/vacancies/{vacancy_id}/interviews", response_model=HRInterviewResponse)
def create_interview(
    vacancy_id: UUID,
    payload: InterviewCreateRequest,
    request: Request,
    _: InterviewManageRole,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> HRInterviewResponse:
    """Create one active interview and enqueue calendar sync."""
    return _execute_hr_action(
        action="interview:create",
        resource_id=str(vacancy_id),
        request=request,
        auth_context=auth_context,
        executor=lambda: service.create_interview(
            vacancy_id=vacancy_id,
            payload=payload,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.get("/api/v1/vacancies/{vacancy_id}/interviews", response_model=HRInterviewListResponse)
def list_interviews(
    vacancy_id: UUID,
    request: Request,
    _: InterviewManageRole,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
    candidate_id: UUID | None = None,
    status: InterviewStatus | None = None,
) -> HRInterviewListResponse:
    """List interviews for one vacancy with optional candidate/status filters."""
    return _execute_hr_action(
        action="interview:read",
        resource_id=str(vacancy_id),
        request=request,
        auth_context=auth_context,
        executor=lambda: service.list_interviews(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            interview_status=status,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.get(
    "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}",
    response_model=HRInterviewResponse,
)
def get_interview(
    vacancy_id: UUID,
    interview_id: UUID,
    request: Request,
    _: InterviewManageRole,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> HRInterviewResponse:
    """Read one interview by vacancy-scoped identifier."""
    return _execute_hr_action(
        action="interview:read",
        resource_id=str(interview_id),
        request=request,
        auth_context=auth_context,
        executor=lambda: service.get_interview(
            vacancy_id=vacancy_id,
            interview_id=interview_id,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.get(
    "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback",
    response_model=InterviewFeedbackPanelSummaryResponse,
)
def get_feedback_summary(
    vacancy_id: UUID,
    interview_id: UUID,
    request: Request,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> InterviewFeedbackPanelSummaryResponse:
    """Read current-version interview feedback summary for HR or assigned interviewer."""
    return _execute_hr_action(
        action="interview_feedback:read",
        resource_id=str(interview_id),
        resource_type="interview_feedback",
        request=request,
        auth_context=auth_context,
        executor=lambda: service.get_feedback_summary(
            vacancy_id=vacancy_id,
            interview_id=interview_id,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.put(
    "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback/me",
    response_model=InterviewFeedbackItemResponse,
)
def put_feedback_for_current_user(
    vacancy_id: UUID,
    interview_id: UUID,
    payload: InterviewFeedbackUpsertRequest,
    request: Request,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> InterviewFeedbackItemResponse:
    """Create or replace the current interviewer's feedback for active schedule version."""
    return _execute_hr_action(
        action="interview_feedback:write",
        resource_id=str(interview_id),
        resource_type="interview_feedback",
        request=request,
        auth_context=auth_context,
        executor=lambda: service.upsert_feedback_for_current_user(
            vacancy_id=vacancy_id,
            interview_id=interview_id,
            payload=payload,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/reschedule",
    response_model=HRInterviewResponse,
)
def reschedule_interview(
    vacancy_id: UUID,
    interview_id: UUID,
    payload: InterviewRescheduleRequest,
    request: Request,
    _: InterviewManageRole,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> HRInterviewResponse:
    """Replace schedule window and enqueue new sync."""
    return _execute_hr_action(
        action="interview:update",
        resource_id=str(interview_id),
        request=request,
        auth_context=auth_context,
        executor=lambda: service.reschedule_interview(
            vacancy_id=vacancy_id,
            interview_id=interview_id,
            payload=payload,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/cancel",
    response_model=HRInterviewResponse,
)
def cancel_interview(
    vacancy_id: UUID,
    interview_id: UUID,
    payload: InterviewCancelRequest,
    request: Request,
    _: InterviewManageRole,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> HRInterviewResponse:
    """Cancel one interview and remove public access immediately."""
    return _execute_hr_action(
        action="interview:cancel",
        resource_id=str(interview_id),
        request=request,
        auth_context=auth_context,
        executor=lambda: service.cancel_interview(
            vacancy_id=vacancy_id,
            interview_id=interview_id,
            payload=payload,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@router.post(
    "/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/resend-invite",
    response_model=HRInterviewResponse,
)
def resend_invite(
    vacancy_id: UUID,
    interview_id: UUID,
    request: Request,
    _: InterviewManageRole,
    auth_context: CurrentAuthContext,
    service: InterviewServiceDependency,
) -> HRInterviewResponse:
    """Reissue a fresh public token for the current synchronized schedule."""
    return _execute_hr_action(
        action="interview:resend_invite",
        resource_id=str(interview_id),
        request=request,
        auth_context=auth_context,
        executor=lambda: service.resend_invite(
            vacancy_id=vacancy_id,
            interview_id=interview_id,
            auth_context=auth_context,
            request=request,
        ),
        service=service,
    )


@public_router.get("/{token}", response_model=PublicInterviewRegistrationResponse)
def get_public_registration(
    token: str,
    request: Request,
    service: InterviewServiceDependency,
) -> PublicInterviewRegistrationResponse:
    """Load current public interview registration payload for one token."""
    return _execute_public_action(
        action="interview_registration:read",
        token=token,
        request=request,
        executor=lambda: service.get_public_registration(token=token, request=request),
        service=service,
    )


@public_router.post("/{token}/confirm", response_model=PublicInterviewRegistrationResponse)
def confirm_public_registration(
    token: str,
    request: Request,
    service: InterviewServiceDependency,
) -> PublicInterviewRegistrationResponse:
    """Confirm attendance for current token-bound schedule."""
    return _execute_public_action(
        action="interview_registration:confirm",
        token=token,
        request=request,
        executor=lambda: service.confirm_public_registration(token=token, request=request),
        service=service,
    )


@public_router.post(
    "/{token}/request-reschedule",
    response_model=PublicInterviewRegistrationResponse,
)
def request_public_reschedule(
    token: str,
    payload: PublicInterviewActionRequest,
    request: Request,
    service: InterviewServiceDependency,
) -> PublicInterviewRegistrationResponse:
    """Request interview reschedule via public token."""
    return _execute_public_action(
        action="interview_registration:request_reschedule",
        token=token,
        request=request,
        executor=lambda: service.request_public_reschedule(
            token=token,
            payload=payload,
            request=request,
        ),
        service=service,
    )


@public_router.post("/{token}/cancel", response_model=PublicInterviewRegistrationResponse)
def cancel_public_registration(
    token: str,
    payload: PublicInterviewActionRequest,
    request: Request,
    service: InterviewServiceDependency,
) -> PublicInterviewRegistrationResponse:
    """Decline interview via public token."""
    return _execute_public_action(
        action="interview_registration:cancel",
        token=token,
        request=request,
        executor=lambda: service.cancel_public_registration(
            token=token,
            payload=payload,
            request=request,
        ),
        service=service,
    )


def _execute_hr_action(
    *,
    action: str,
    resource_id: str,
    resource_type: str = "interview",
    request: Request,
    auth_context: AuthContext,
    executor,
    service: InterviewService,
):
    """Wrap HR routes with consistent failure audit handling."""
    actor_sub = str(auth_context.subject_id)
    actor_role = auth_context.role
    try:
        return executor()
    except HTTPException as exc:
        service._audit_service.record_api_event(  # noqa: SLF001
            action=action,
            resource_type=resource_type,
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
            reason=_extract_reason_code(exc),
        )
        raise


def _execute_public_action(
    *,
    action: str,
    token: str,
    request: Request,
    executor,
    service: InterviewService,
):
    """Wrap public routes with consistent failure audit handling."""
    try:
        return executor()
    except HTTPException as exc:
        service._audit_service.record_api_event(  # noqa: SLF001
            action=action,
            resource_type="interview",
            result="failure",
            request=request,
            resource_id=token[:32],
            reason=_extract_reason_code(exc),
        )
        raise


def _extract_reason_code(exc: HTTPException) -> str:
    """Normalize raised HTTP detail payload into audit-friendly reason code."""
    if isinstance(exc.detail, str) and exc.detail.strip():
        return exc.detail.strip()
    return f"http_{exc.status_code}"
