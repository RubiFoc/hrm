"""Business orchestration for password auth, staff registration, and JWT lifecycle."""

from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import HTTPException, status

from hrm_backend.auth.infra.postgres.employee_registration_key_dao import EmployeeRegistrationKeyDAO
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.auth.schemas.responses import (
    MeResponse,
    TokenResponse,
)
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.settings import AppSettings


class AuthService:
    """Auth service implementing staff account auth with JWT + Redis denylist."""

    def __init__(
        self,
        *,
        token_service: TokenService,
        denylist_service: DenylistService,
        staff_account_dao: StaffAccountDAO | None = None,
        registration_key_dao: EmployeeRegistrationKeyDAO | None = None,
        password_service: PasswordService | None = None,
        settings: AppSettings,
    ) -> None:
        """Initialize auth service dependencies."""
        self._token_service = token_service
        self._denylist_service = denylist_service
        self._staff_account_dao = staff_account_dao
        self._registration_key_dao = registration_key_dao
        self._password_service = password_service
        self._settings = settings

    def register(
        self,
        *,
        login: str,
        email: str,
        password: str,
        employee_key: UUID,
    ) -> TokenResponse:
        """Register new staff account using one-time employee key."""
        self._require_account_dependencies()

        existing_login = self._staff_account_dao.get_by_login(login)
        if existing_login is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login already exists")

        existing_email = self._staff_account_dao.get_by_email(email)
        if existing_email is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        key_row = self._registration_key_dao.get_by_employee_key(str(employee_key))
        if key_row is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Employee key is invalid",
            )

        consumed = self._registration_key_dao.consume_key(
            employee_key=str(employee_key),
            target_role=key_row.target_role,
        )
        if consumed is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Employee key is expired, used, or role-mismatched",
            )

        password_hash = self._password_service.hash_password(password)
        account = self._staff_account_dao.create_account(
            login=login,
            email=email,
            password_hash=password_hash,
            role=consumed.target_role,
            is_active=True,
        )
        return self._issue_token_pair(staff_id=UUID(account.staff_id), role=account.role)

    def login(
        self,
        *,
        identifier: str,
        password: str,
    ) -> TokenResponse:
        """Issue JWT token pair for staff account by login or e-mail + password."""
        self._require_account_dependencies()
        account = self._staff_account_dao.get_by_identifier(identifier)
        if account is None or not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        if not self._password_service.verify_password(password, account.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid credentials",
            )

        return self._issue_token_pair(staff_id=UUID(account.staff_id), role=account.role)

    def refresh(self, refresh_token: str) -> TokenResponse:
        """Rotate token pair using refresh token."""
        refresh_claims = self._token_service.decode_refresh_token(refresh_token)
        self._denylist_service.ensure_not_denied(str(refresh_claims.jti), str(refresh_claims.sid))
        self._denylist_service.deny_jti_until_exp(str(refresh_claims.jti), refresh_claims.exp)

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
        """Invalidate current access token and entire JWT session window."""
        self._denylist_service.deny_jti_until_exp(
            str(auth_context.token_id),
            auth_context.expires_at,
        )
        self._denylist_service.deny_sid_for_refresh_window(str(auth_context.session_id))

    def authenticate_access_token(self, access_token: str) -> AuthContext:
        """Validate access token and denylist state."""
        claims = self._token_service.decode_access_token(access_token)
        self._denylist_service.ensure_not_denied(str(claims.jti), str(claims.sid))

        return AuthContext(
            subject_id=claims.sub,
            role=claims.role,
            session_id=claims.sid,
            token_id=claims.jti,
            expires_at=claims.exp,
        )

    @staticmethod
    def build_me_response(auth_context: AuthContext) -> MeResponse:
        """Build `/me` endpoint payload from request auth context."""
        return MeResponse(
            subject_id=auth_context.subject_id,
            role=auth_context.role,
            session_id=auth_context.session_id,
            access_token_expires_at=auth_context.expires_at,
        )

    def _issue_token_pair(self, *, staff_id: UUID, role: str) -> TokenResponse:
        """Issue fresh access/refresh pair for staff identity."""
        session_id = uuid4()
        access_token, _ = self._token_service.issue_access_token(staff_id, role, session_id)
        refresh_token, _ = self._token_service.issue_refresh_token(staff_id, role, session_id)
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            token_type="bearer",
            expires_in=self._settings.access_token_ttl_seconds,
            session_id=session_id,
        )

    def _require_account_dependencies(self) -> None:
        """Ensure account-backed dependencies are available."""
        if (
            self._staff_account_dao is None
            or self._registration_key_dao is None
            or self._password_service is None
        ):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Account storage dependencies are not configured",
            )
