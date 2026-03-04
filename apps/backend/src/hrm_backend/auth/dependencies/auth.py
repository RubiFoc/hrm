"""Auth dependency providers for FastAPI handlers and RBAC integration."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from redis import Redis
from sqlalchemy.orm import Session

from hrm_backend.auth.infra.postgres.employee_registration_key_dao import EmployeeRegistrationKeyDAO
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.infra.redis import RedisDenylistDAO, get_redis_client
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.auth_service import AuthService
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.core.db.session import get_db_session
from hrm_backend.core.errors.http import unauthorized
from hrm_backend.settings import AppSettings, get_settings

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
RedisClientDependency = Annotated[Redis, Depends(get_redis_client)]
SessionDependency = Annotated[Session, Depends(get_db_session)]

_bearer_scheme = HTTPBearer(auto_error=False)


def get_token_service(settings: SettingsDependency) -> TokenService:
    """Build token service from auth settings."""
    return TokenService(settings=settings)


def get_denylist_dao(
    settings: SettingsDependency,
    redis_client: RedisClientDependency,
) -> RedisDenylistDAO:
    """Build Redis denylist DAO."""
    return RedisDenylistDAO(redis_client=redis_client, key_prefix=settings.redis_prefix)


def get_denylist_service(
    settings: SettingsDependency,
    dao: Annotated[RedisDenylistDAO, Depends(get_denylist_dao)],
) -> DenylistService:
    """Build denylist business service."""
    return DenylistService(dao=dao, refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds)


def get_staff_account_dao(session: SessionDependency) -> StaffAccountDAO:
    """Build PostgreSQL DAO for staff accounts."""
    return StaffAccountDAO(session=session)


def get_employee_registration_key_dao(session: SessionDependency) -> EmployeeRegistrationKeyDAO:
    """Build PostgreSQL DAO for employee registration keys."""
    return EmployeeRegistrationKeyDAO(session=session)


def get_password_service() -> PasswordService:
    """Build password service for auth operations."""
    return PasswordService()


def get_auth_service(
    settings: SettingsDependency,
    token_service: Annotated[TokenService, Depends(get_token_service)],
    denylist_service: Annotated[DenylistService, Depends(get_denylist_service)],
    staff_account_dao: Annotated[StaffAccountDAO, Depends(get_staff_account_dao)],
    registration_key_dao: Annotated[
        EmployeeRegistrationKeyDAO,
        Depends(get_employee_registration_key_dao),
    ],
    password_service: Annotated[PasswordService, Depends(get_password_service)],
) -> AuthService:
    """Build auth orchestration service."""
    return AuthService(
        token_service=token_service,
        denylist_service=denylist_service,
        staff_account_dao=staff_account_dao,
        registration_key_dao=registration_key_dao,
        password_service=password_service,
        settings=settings,
    )


def get_bearer_token(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Security(_bearer_scheme)],
) -> str:
    """Extract bearer access token from OpenAPI-aware HTTPBearer security dependency."""
    if isinstance(credentials, Request):  # compatibility for direct unit-test calls
        raw_header = credentials.headers.get("Authorization")
        if raw_header is None:
            raise unauthorized("Missing Authorization header: use Bearer token")
        scheme, _, token = raw_header.partition(" ")
        if scheme.lower() != "bearer" or not token.strip():
            raise unauthorized("Malformed Authorization header: use Bearer <token>")
        return token.strip()

    if credentials is None:
        raise unauthorized("Missing Authorization header: use Bearer token")
    if credentials.scheme.lower() != "bearer" or not credentials.credentials.strip():
        raise unauthorized("Malformed Authorization header: use Bearer <token>")
    return credentials.credentials.strip()


def get_current_auth_context(
    token: Annotated[str, Depends(get_bearer_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthContext:
    """Resolve validated auth context for protected request handling."""
    return auth_service.authenticate_access_token(token)
