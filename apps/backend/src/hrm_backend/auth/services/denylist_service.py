"""Business service for denylist operations and fail-closed Redis handling."""

from __future__ import annotations

from redis.exceptions import RedisError

from hrm_backend.auth.dao.redis_denylist_dao import RedisDenylistDAO
from hrm_backend.core.errors.http import service_unavailable, unauthorized
from hrm_backend.core.utils.time import ttl_until_epoch


class DenylistService:
    """Auth denylist service with fail-closed behavior on Redis errors."""

    def __init__(self, dao: RedisDenylistDAO, refresh_token_ttl_seconds: int) -> None:
        """Initialize denylist service.

        Args:
            dao: Redis denylist DAO.
            refresh_token_ttl_seconds: TTL to denylist session id on logout.
        """
        self._dao = dao
        self._refresh_token_ttl_seconds = refresh_token_ttl_seconds

    def ensure_not_denied(self, token_id: str, session_id: str) -> None:
        """Ensure token/session are not denylisted.

        Args:
            token_id: JWT token identifier (`jti`).
            session_id: JWT session identifier (`sid`).

        Raises:
            HTTPException: 401 when token/session are denied, 503 on Redis errors.
        """
        try:
            if self._dao.is_jti_denied(token_id) or self._dao.is_sid_denied(session_id):
                raise unauthorized("Token revoked")
        except RedisError as exc:
            raise service_unavailable("Token validation is temporarily unavailable") from exc

    def deny_jti_until_exp(self, token_id: str, expires_at: int) -> None:
        """Denylist token id until token expiration.

        Args:
            token_id: JWT token identifier.
            expires_at: Token expiration timestamp.

        Raises:
            HTTPException: 503 when Redis write fails.
        """
        ttl_seconds = ttl_until_epoch(expires_at)
        if ttl_seconds <= 0:
            return

        try:
            self._dao.deny_jti(token_id, ttl_seconds)
        except RedisError as exc:
            raise service_unavailable("Token validation is temporarily unavailable") from exc

    def deny_sid_for_refresh_window(self, session_id: str) -> None:
        """Denylist session id for full refresh window after logout.

        Args:
            session_id: JWT session identifier.

        Raises:
            HTTPException: 503 when Redis write fails.
        """
        try:
            self._dao.deny_sid(session_id, self._refresh_token_ttl_seconds)
        except RedisError as exc:
            raise service_unavailable("Token validation is temporarily unavailable") from exc
