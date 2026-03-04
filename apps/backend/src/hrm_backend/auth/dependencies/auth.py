"""Auth dependency providers for FastAPI handlers and RBAC integration."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request
from redis import Redis

from hrm_backend.auth.dao.redis_denylist_dao import RedisDenylistDAO
from hrm_backend.auth.redis.client import get_redis_client
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.auth_service import AuthService
from hrm_backend.auth.services.denylist_service import DenylistService
from hrm_backend.auth.services.token_service import TokenService
from hrm_backend.core.errors.http import unauthorized
from hrm_backend.settings import AppSettings, get_settings

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
RedisClientDependency = Annotated[Redis, Depends(get_redis_client)]


def get_token_service(settings: SettingsDependency) -> TokenService:
    """Build token service from auth settings.

    Args:
        settings: Auth runtime settings.

    Returns:
        TokenService: JWT token service instance.
    """
    return TokenService(settings=settings)


def get_denylist_dao(
    settings: SettingsDependency,
    redis_client: RedisClientDependency,
) -> RedisDenylistDAO:
    """Build Redis denylist DAO.

    Args:
        settings: Auth runtime settings.
        redis_client: Redis client instance.

    Returns:
        RedisDenylistDAO: DAO bound to configured Redis prefix.
    """
    return RedisDenylistDAO(redis_client=redis_client, key_prefix=settings.redis_prefix)


def get_denylist_service(
    settings: SettingsDependency,
    dao: Annotated[RedisDenylistDAO, Depends(get_denylist_dao)],
) -> DenylistService:
    """Build denylist business service.

    Args:
        settings: Auth runtime settings.
        dao: Redis denylist DAO.

    Returns:
        DenylistService: Denylist service with fail-closed behavior.
    """
    return DenylistService(dao=dao, refresh_token_ttl_seconds=settings.refresh_token_ttl_seconds)


def get_auth_service(
    settings: SettingsDependency,
    token_service: Annotated[TokenService, Depends(get_token_service)],
    denylist_service: Annotated[DenylistService, Depends(get_denylist_service)],
) -> AuthService:
    """Build auth orchestration service.

    Args:
        settings: Auth runtime settings.
        token_service: Token issuance and validation service.
        denylist_service: Denylist validation service.

    Returns:
        AuthService: Auth business service.
    """
    return AuthService(
        token_service=token_service,
        denylist_service=denylist_service,
        settings=settings,
    )


def get_bearer_token(request: Request) -> str:
    """Extract bearer access token from Authorization header.

    Args:
        request: Incoming HTTP request.

    Returns:
        str: Raw bearer token string.

    Raises:
        fastapi.HTTPException: If header is missing or malformed.
    """
    raw_header = request.headers.get("Authorization")
    if raw_header is None:
        raise unauthorized("Missing Authorization header: use Bearer token")

    scheme, _, token = raw_header.partition(" ")
    if scheme.lower() != "bearer" or not token.strip():
        raise unauthorized("Malformed Authorization header: use Bearer <token>")

    return token.strip()


def get_current_auth_context(
    token: Annotated[str, Depends(get_bearer_token)],
    auth_service: Annotated[AuthService, Depends(get_auth_service)],
) -> AuthContext:
    """Resolve validated auth context for protected request handling.

    Args:
        token: Bearer JWT access token.
        auth_service: Auth service with token/denylist checks.

    Returns:
        AuthContext: Validated identity context.
    """
    return auth_service.authenticate_access_token(token)
