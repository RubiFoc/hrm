"""Version 1 auth HTTP router."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status

from hrm_backend.auth.dependencies.auth import get_auth_service, get_current_auth_context
from hrm_backend.auth.schemas.requests import LoginRequest, RefreshRequest
from hrm_backend.auth.schemas.responses import MeResponse, TokenResponse
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.auth_service import AuthService

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, auth_service: AuthServiceDependency) -> TokenResponse:
    """Issue access and refresh JWT token pair.

    Args:
        request: Login payload with actor identity claims.
        auth_service: Auth service dependency.

    Returns:
        TokenResponse: Issued token pair payload.
    """
    return auth_service.login(subject_id=request.subject_id, role=request.role)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest, auth_service: AuthServiceDependency) -> TokenResponse:
    """Rotate JWT token pair using refresh token.

    Args:
        request: Refresh payload.
        auth_service: Auth service dependency.

    Returns:
        TokenResponse: Rotated token pair payload.
    """
    return auth_service.refresh(refresh_token=request.refresh_token)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    auth_context: CurrentAuthContext,
    auth_service: AuthServiceDependency,
) -> Response:
    """Invalidate current token and session via Redis denylist.

    Args:
        auth_context: Current validated auth context.
        auth_service: Auth service dependency.

    Returns:
        Response: Empty response with status `204 No Content`.
    """
    auth_service.logout(auth_context)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(auth_context: CurrentAuthContext) -> MeResponse:
    """Return identity metadata derived from current access token.

    Args:
        auth_context: Current validated auth context.

    Returns:
        MeResponse: Authenticated identity payload.
    """
    return AuthService.build_me_response(auth_context)
