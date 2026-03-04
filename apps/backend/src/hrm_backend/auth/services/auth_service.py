"""Business orchestration for auth login, refresh, logout, and access checks."""

from __future__ import annotations

import uuid

from hrm_backend.auth.schemas.responses import MeResponse, TokenResponse
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.auth.utils.settings import AuthSettings


class AuthService:
    """Auth service implementing stateless JWT lifecycle with Redis denylist."""

    def __init__(
        self,
        token_service: TokenService,
        denylist_service: DenylistService,
        settings: AuthSettings,
    ) -> None:
        """Initialize auth service.

        Args:
            token_service: JWT issuance/validation service.
            denylist_service: Denylist business service.
            settings: Auth runtime settings.
        """
        self._token_service = token_service
        self._denylist_service = denylist_service
        self._settings = settings

    def login(self, subject_id: str, role: str) -> TokenResponse:
        """Issue initial access/refresh token pair for a new session.

        Args:
            subject_id: Authenticated actor identifier.
            role: Role claim for the session.

        Returns:
            TokenResponse: Access and refresh token pair payload.
        """
        session_id = uuid.uuid4().hex
        access_token, _ = self._token_service.issue_access_token(subject_id, role, session_id)
        refresh_token, _ = self._token_service.issue_refresh_token(subject_id, role, session_id)

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._settings.access_token_ttl_seconds,
            session_id=session_id,
        )

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Rotate token pair using refresh token.

        Args:
            refresh_token: JWT refresh token.

        Returns:
            TokenResponse: Newly issued access and refresh token pair.
        """
        refresh_claims = self._token_service.decode_refresh_token(refresh_token)
        self._denylist_service.ensure_not_denied(refresh_claims.jti, refresh_claims.sid)
        self._denylist_service.deny_jti_until_exp(refresh_claims.jti, refresh_claims.exp)

        next_access_token, _ = self._token_service.issue_access_token(
            refresh_claims.sub,
            refresh_claims.role,
            refresh_claims.sid,
        )
        next_refresh_token, _ = self._token_service.issue_refresh_token(
            refresh_claims.sub,
            refresh_claims.role,
            refresh_claims.sid,
        )

        return TokenResponse(
            access_token=next_access_token,
            refresh_token=next_refresh_token,
            token_type="bearer",
            expires_in=self._settings.access_token_ttl_seconds,
            session_id=refresh_claims.sid,
        )

    def logout(self, auth_context: AuthContext) -> None:
        """Invalidate current access token and entire JWT session window.

        Args:
            auth_context: Validated auth context from access token.
        """
        self._denylist_service.deny_jti_until_exp(auth_context.token_id, auth_context.expires_at)
        self._denylist_service.deny_sid_for_refresh_window(auth_context.session_id)

    def authenticate_access_token(self, access_token: str) -> AuthContext:
        """Validate access token and denylist state.

        Args:
            access_token: JWT access token from request headers.

        Returns:
            AuthContext: Verified request-scoped identity context.
        """
        claims = self._token_service.decode_access_token(access_token)
        self._denylist_service.ensure_not_denied(claims.jti, claims.sid)

        return AuthContext(
            subject_id=claims.sub,
            role=claims.role,
            session_id=claims.sid,
            token_id=claims.jti,
            expires_at=claims.exp,
        )

    @staticmethod
    def build_me_response(auth_context: AuthContext) -> MeResponse:
        """Build `/me` endpoint payload from request auth context.

        Args:
            auth_context: Validated auth context from dependency chain.

        Returns:
            MeResponse: Authenticated actor metadata.
        """
        return MeResponse(
            subject_id=auth_context.subject_id,
            role=auth_context.role,
            session_id=auth_context.session_id,
            access_token_expires_at=auth_context.expires_at,
        )
