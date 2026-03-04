"""Version 1 auth HTTP router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.dependencies.auth import get_auth_service, get_current_auth_context
from hrm_backend.auth.schemas.requests import LoginRequest, RefreshRequest
from hrm_backend.auth.schemas.responses import MeResponse, TokenResponse
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]


@router.post("/login", response_model=TokenResponse)
def login(
    request: LoginRequest,
    http_request: Request,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> TokenResponse:
    """Issue access and refresh JWT token pair.

    Args:
        request: Login payload with actor identity claims.
        auth_service: Auth service dependency.

    Returns:
        TokenResponse: Issued token pair payload.
    """
    try:
        token_response = auth_service.login(subject_id=request.subject_id, role=request.role)
    except HTTPException as exc:
        audit_service.record_api_event(
            action="auth.login",
            resource_type="auth_session",
            result="failure",
            request=http_request,
            actor_sub=request.subject_id,
            actor_role=request.role,
            reason=str(exc.detail),
        )
        raise

    audit_service.record_api_event(
        action="auth.login",
        resource_type="auth_session",
        result="success",
        request=http_request,
        actor_sub=request.subject_id,
        actor_role=request.role,
        resource_id=token_response.session_id,
    )
    return token_response


@router.post("/refresh", response_model=TokenResponse)
def refresh(
    request: RefreshRequest,
    http_request: Request,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> TokenResponse:
    """Rotate JWT token pair using refresh token.

    Args:
        request: Refresh payload.
        auth_service: Auth service dependency.

    Returns:
        TokenResponse: Rotated token pair payload.
    """
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
        resource_id=token_response.session_id,
    )
    return token_response


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    http_request: Request,
    auth_context: CurrentAuthContext,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> Response:
    """Invalidate current token and session via Redis denylist.

    Args:
        auth_context: Current validated auth context.
        auth_service: Auth service dependency.

    Returns:
        Response: Empty response with status `204 No Content`.
    """
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
            resource_id=auth_context.session_id,
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
        resource_id=auth_context.session_id,
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(
    http_request: Request,
    auth_context: CurrentAuthContext,
    audit_service: AuditServiceDependency,
) -> MeResponse:
    """Return identity metadata derived from current access token.

    Args:
        auth_context: Current validated auth context.

    Returns:
        MeResponse: Authenticated identity payload.
    """
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    response = AuthService.build_me_response(auth_context)
    audit_service.record_api_event(
        action="auth.me.read",
        resource_type="auth_identity",
        result="success",
        request=http_request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=auth_context.session_id,
    )
    return response
