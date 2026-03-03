"""Authentication API endpoints for token and session lifecycle management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel, Field

from hrm_backend.auth import (
    SESSION_STORE,
    AuthContext,
    TokenBundle,
    get_current_auth_context,
)
from hrm_backend.rbac import Role

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]


class LoginRequest(BaseModel):
    """Input payload for session creation.

    Attributes:
        subject_id: Stable actor id used as token ``sub`` claim.
        role: Role claim from project RBAC matrix.
    """

    subject_id: str = Field(min_length=3, max_length=128)
    role: Role


class RefreshRequest(BaseModel):
    """Input payload for refresh token rotation.

    Attributes:
        refresh_token: Current refresh token tied to active session.
    """

    refresh_token: str = Field(min_length=10, max_length=512)


class TokenResponse(BaseModel):
    """Response payload returned by login and refresh operations.

    Attributes:
        access_token: Signed bearer token for API calls.
        refresh_token: Rotating opaque token for obtaining new access token.
        token_type: Token type marker (`bearer`).
        expires_in: Access token lifetime in seconds.
        session_id: Server-side session identifier.
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: str


class MeResponse(BaseModel):
    """Authenticated identity metadata for the current request.

    Attributes:
        subject_id: Actor identifier from access token claims.
        role: Role claim resolved from access token.
        session_id: Current active session id.
        access_token_expires_at: UNIX timestamp when access token expires.
    """

    subject_id: str
    role: str
    session_id: str
    access_token_expires_at: int


def _to_token_response(bundle: TokenBundle) -> TokenResponse:
    """Map internal token bundle object to API response schema.

    Args:
        bundle: Internal token result from session store methods.

    Returns:
        TokenResponse: Serialized payload for HTTP responses.
    """
    return TokenResponse(
        access_token=bundle.access_token,
        refresh_token=bundle.refresh_token,
        token_type=bundle.token_type,
        expires_in=bundle.expires_in,
        session_id=bundle.session_id,
    )


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest) -> TokenResponse:
    """Authenticate actor and issue a new token pair.

    Args:
        request: Login payload with actor id and RBAC role claim.

    Returns:
        TokenResponse: Access and refresh tokens bound to a new session.
    """
    bundle = SESSION_STORE.issue_session(subject_id=request.subject_id, role=request.role)
    return _to_token_response(bundle)


@router.post("/refresh", response_model=TokenResponse)
def refresh(request: RefreshRequest) -> TokenResponse:
    """Rotate refresh token and issue a fresh access token.

    Args:
        request: Payload containing current refresh token.

    Returns:
        TokenResponse: New access and refresh token pair.
    """
    bundle = SESSION_STORE.rotate_refresh_token(refresh_token=request.refresh_token)
    return _to_token_response(bundle)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(auth_context: CurrentAuthContext) -> Response:
    """Revoke active session for the caller.

    Args:
        auth_context: Validated authentication claims for current request.

    Returns:
        Response: Empty `204 No Content` response.
    """
    SESSION_STORE.revoke_session(auth_context.session_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/me", response_model=MeResponse)
def me(auth_context: CurrentAuthContext) -> MeResponse:
    """Return authenticated identity claims for current access token.

    Args:
        auth_context: Validated authentication claims for current request.

    Returns:
        MeResponse: Caller identity metadata.
    """
    return MeResponse(
        subject_id=auth_context.subject_id,
        role=auth_context.role,
        session_id=auth_context.session_id,
        access_token_expires_at=auth_context.expires_at,
    )
