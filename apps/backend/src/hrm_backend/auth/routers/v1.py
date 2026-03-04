"""Version 1 auth HTTP router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.dependencies.auth import get_auth_service, get_current_auth_context
from hrm_backend.auth.schemas.requests import LoginRequest, RefreshRequest, RegisterRequest
from hrm_backend.auth.schemas.responses import MeResponse, TokenResponse
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]


@router.post("/register", response_model=TokenResponse)
def register(
    request: RegisterRequest,
    http_request: Request,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> TokenResponse:
    """Register staff account using one-time employee key and issue token pair."""
    try:
        token_response = auth_service.register(
            login=request.login,
            email=request.email,
            password=request.password,
            employee_key=request.employee_key,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="auth.register",
            resource_type="auth_session",
            result="failure",
            request=http_request,
            actor_sub=request.login,
            reason=str(exc.detail),
        )
        raise

    audit_service.record_api_event(
        action="auth.register",
        resource_type="auth_session",
        result="success",
        request=http_request,
        actor_sub=request.login,
        resource_id=str(token_response.session_id),
    )
    return token_response


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> TokenResponse:
    """Issue access and refresh JWT token pair for staff account."""
    try:
        token_response = auth_service.login(
            identifier=request.identifier,
            password=request.password,
            subject_id=request.subject_id,
            role=request.role,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="auth.login",
            resource_type="auth_session",
            result="failure",
            request=http_request,
            actor_sub=(
                request.identifier
                or (str(request.subject_id) if request.subject_id else None)
            ),
            actor_role=request.role,
            reason=str(exc.detail),
        )
        raise

    audit_service.record_api_event(
        action="auth.login",
        resource_type="auth_session",
        result="success",
        request=http_request,
        actor_sub=request.identifier or (str(request.subject_id) if request.subject_id else None),
        actor_role=request.role,
        resource_id=str(token_response.session_id),
    )
    return token_response


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshRequest,
    http_request: Request,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> TokenResponse:
    """Rotate JWT token pair using refresh token."""
    try:
        token_response = auth_service.refresh(refresh_token=request.refresh_token)
    except HTTPException as exc:
        audit_service.record_api_event(
            action="auth.refresh",
            resource_type="auth_session",
            result="failure",
            request=http_request,
            reason=str(exc.detail),
        )
        raise

    audit_service.record_api_event(
        action="auth.refresh",
        resource_type="auth_session",
        result="success",
        request=http_request,
        resource_id=str(token_response.session_id),
    )
    return token_response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    http_request: Request,
    auth_context: CurrentAuthContext,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> Response:
    """Invalidate current token and session via Redis denylist."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        auth_service.logout(auth_context)
    except HTTPException as exc:
        audit_service.record_api_event(
            action="auth.logout",
            resource_type="auth_session",
            result="failure",
            request=http_request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(auth_context.session_id),
            reason=str(exc.detail),
        )
        raise
    audit_service.record_api_event(
        action="auth.logout",
        resource_type="auth_session",
        result="success",
        request=http_request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=str(auth_context.session_id),
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(
    http_request: Request,
    auth_context: CurrentAuthContext,
    audit_service: AuditServiceDependency,
) -> MeResponse:
    """Return identity metadata derived from current access token."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    response = AuthService.build_me_response(auth_context)
    audit_service.record_api_event(
        action="auth.me.read",
        resource_type="auth_identity",
        result="success",
        request=http_request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=str(auth_context.session_id),
    )
    return response
