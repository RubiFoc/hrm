"""Redis DAO for auth JWT denylist read/write operations."""

from __future__ import annotations

from redis import Redis


class RedisDenylistDAO:
    """Data access object for denylist key checks and writes in Redis."""

    def __init__(self, redis_client: Redis, key_prefix: str) -> None:
        """Initialize Redis denylist DAO.

        Args:
            redis_client: Redis client used for denylist operations.
            key_prefix: Prefix for denylist keys.
        """
        self._redis = redis_client
        self._key_prefix = key_prefix.rstrip(":")

    def _jti_key(self, jti: str) -> str:
        """Build denylist key for token identifier.

        Args:
            jti: JWT token identifier.

        Returns:
            str: Redis key for token denylist marker.
        """
        return f"{self._key_prefix}:jti:{jti}"

    def _sid_key(self, sid: str) -> str:
        """Build denylist key for session identifier.

        Args:
            sid: JWT session identifier.

        Returns:
            str: Redis key for session denylist marker.
        """
        return f"{self._key_prefix}:sid:{sid}"

    def deny_jti(self, jti: str, ttl_seconds: int) -> None:
        """Write denylist marker for token identifier.

        Args:
            jti: JWT token identifier.
            ttl_seconds: TTL in seconds.
        """
        if ttl_seconds <= 0:
            return
        self._redis.set(self._jti_key(jti), b"1", ex=ttl_seconds)

    def deny_sid(self, sid: str, ttl_seconds: int) -> None:
        """Write denylist marker for session identifier.

        Args:
            sid: Session identifier.
            ttl_seconds: TTL in seconds.
        """
        if ttl_seconds <= 0:
            return
        self._redis.set(self._sid_key(sid), b"1", ex=ttl_seconds)

    def is_jti_denied(self, jti: str) -> bool:
        """Check whether token id is denylisted.

        Args:
            jti: JWT token identifier.

        Returns:
            bool: `True` if token is denied.
        """
        return bool(self._redis.exists(self._jti_key(jti)))

    def is_sid_denied(self, sid: str) -> bool:
        """Check whether session id is denylisted.

        Args:
            sid: Session identifier.

        Returns:
            bool: `True` if session is denied.
        """
        return bool(self._redis.exists(self._sid_key(sid)))
