"""Runtime settings for auth domain services and dependencies."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Final

from hrm_backend.core.config.env import normalize_non_empty, read_positive_int_env

DEFAULT_JWT_ALGORITHM: Final[str] = "HS256"
DEFAULT_JWT_SECRET: Final[str] = "hrm-dev-secret-change-me"
DEFAULT_ACCESS_TOKEN_TTL_SECONDS: Final[int] = 15 * 60
DEFAULT_REFRESH_TOKEN_TTL_SECONDS: Final[int] = 7 * 24 * 60 * 60
DEFAULT_REDIS_URL: Final[str] = "redis://redis:6379/0"
DEFAULT_REDIS_PREFIX: Final[str] = "auth:deny"


@dataclass(frozen=True)
class AuthSettings:
    """Typed runtime config for auth package.

    Attributes:
        jwt_secret: Secret key used to sign and verify JWT tokens.
        jwt_algorithm: JWT signing algorithm.
        access_token_ttl_seconds: Access token lifetime in seconds.
        refresh_token_ttl_seconds: Refresh token lifetime in seconds.
        redis_url: Redis DSN used for denylist storage.
        redis_prefix: Key prefix used for denylist keys.
    """

    jwt_secret: str
    jwt_algorithm: str
    access_token_ttl_seconds: int
    refresh_token_ttl_seconds: int
    redis_url: str
    redis_prefix: str

@lru_cache(maxsize=1)
def get_auth_settings() -> AuthSettings:
    """Build and cache auth settings from environment variables.

    Returns:
        AuthSettings: Immutable auth runtime configuration.

    Raises:
        RuntimeError: If resolved JWT secret is empty.
    """
    jwt_secret = normalize_non_empty(
        os.getenv("HRM_JWT_SECRET"),
        DEFAULT_JWT_SECRET,
    )
    jwt_algorithm = normalize_non_empty(
        os.getenv("HRM_JWT_ALGORITHM"),
        DEFAULT_JWT_ALGORITHM,
    )
    redis_url = normalize_non_empty(os.getenv("REDIS_URL"), DEFAULT_REDIS_URL)
    redis_prefix = normalize_non_empty(
        os.getenv("HRM_AUTH_REDIS_PREFIX"),
        DEFAULT_REDIS_PREFIX,
    )

    if not jwt_secret:
        raise RuntimeError("HRM_JWT_SECRET must be non-empty")

    return AuthSettings(
        jwt_secret=jwt_secret,
        jwt_algorithm=jwt_algorithm,
        access_token_ttl_seconds=read_positive_int_env(
            os.getenv("HRM_ACCESS_TOKEN_TTL_SECONDS"),
            DEFAULT_ACCESS_TOKEN_TTL_SECONDS,
        ),
        refresh_token_ttl_seconds=read_positive_int_env(
            os.getenv("HRM_REFRESH_TOKEN_TTL_SECONDS"),
            DEFAULT_REFRESH_TOKEN_TTL_SECONDS,
        ),
        redis_url=redis_url,
        redis_prefix=redis_prefix,
    )
