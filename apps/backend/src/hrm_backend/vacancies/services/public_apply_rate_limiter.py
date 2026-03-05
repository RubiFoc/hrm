"""Redis-backed rate limiter for the public vacancy application endpoint."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from time import time

from fastapi import status
from redis import Redis

from hrm_backend.vacancies.schemas.application import PUBLIC_APPLY_REASON_RATE_LIMITED
from hrm_backend.vacancies.services.public_apply_exceptions import PublicApplyRejectedError


@dataclass(frozen=True)
class _BucketResult:
    """Internal result for one rate-limit bucket consumption attempt."""

    count: int
    ttl_seconds: int
    limit: int
    scope: str


class PublicApplyRateLimiter:
    """Rate limiter with independent limits for IP, IP+vacancy, and email+vacancy."""

    def __init__(
        self,
        *,
        redis_client: Redis,
        key_prefix: str,
        ip_limit: int,
        ip_window_seconds: int,
        ip_vacancy_limit: int,
        ip_vacancy_window_seconds: int,
        email_vacancy_limit: int,
        email_vacancy_window_seconds: int,
    ) -> None:
        """Initialize limiter with Redis client and bucket thresholds.

        Args:
            redis_client: Redis client for atomic counter operations.
            key_prefix: Key namespace prefix.
            ip_limit: Max requests for one IP in configured window.
            ip_window_seconds: Window size for IP limit.
            ip_vacancy_limit: Max requests per IP+vacancy tuple in configured window.
            ip_vacancy_window_seconds: Window size for IP+vacancy limit.
            email_vacancy_limit: Max requests per email+vacancy tuple in configured window.
            email_vacancy_window_seconds: Window size for email+vacancy limit.
        """
        self._redis = redis_client
        self._key_prefix = key_prefix
        self._ip_limit = ip_limit
        self._ip_window_seconds = ip_window_seconds
        self._ip_vacancy_limit = ip_vacancy_limit
        self._ip_vacancy_window_seconds = ip_vacancy_window_seconds
        self._email_vacancy_limit = email_vacancy_limit
        self._email_vacancy_window_seconds = email_vacancy_window_seconds

    def enforce(
        self,
        *,
        ip: str | None,
        vacancy_id: str,
        email: str,
    ) -> None:
        """Consume all configured buckets and raise 429 on first exceeded limit.

        Args:
            ip: Client IP address.
            vacancy_id: Vacancy identifier from path.
            email: Candidate email from request payload.

        Raises:
            PublicApplyRejectedError: When any configured rate-limit bucket is exceeded.
            RedisError: When Redis operation fails.
        """
        normalized_ip = (ip or "").strip() or "unknown"
        normalized_vacancy_id = vacancy_id.strip()
        normalized_email = email.strip().lower()
        hashed_email = sha256(normalized_email.encode("utf-8")).hexdigest()

        buckets = (
            (
                f"{self._key_prefix}:ip:{normalized_ip}",
                self._ip_limit,
                self._ip_window_seconds,
                "ip",
            ),
            (
                f"{self._key_prefix}:ip_vacancy:{normalized_ip}:{normalized_vacancy_id}",
                self._ip_vacancy_limit,
                self._ip_vacancy_window_seconds,
                "ip+vacancy",
            ),
            (
                f"{self._key_prefix}:email_vacancy:{hashed_email}:{normalized_vacancy_id}",
                self._email_vacancy_limit,
                self._email_vacancy_window_seconds,
                "email+vacancy",
            ),
        )

        for key, limit, window_seconds, scope in buckets:
            result = self._consume_bucket(
                key=key,
                limit=limit,
                window_seconds=window_seconds,
                scope=scope,
            )
            if result.count <= result.limit:
                continue

            retry_after = max(result.ttl_seconds, 1)
            reset_epoch = int(time()) + retry_after
            headers = {
                "Retry-After": str(retry_after),
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": "0",
                "X-RateLimit-Reset": str(reset_epoch),
            }
            raise PublicApplyRejectedError(
                reason_code=PUBLIC_APPLY_REASON_RATE_LIMITED,
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Public application rate limit exceeded for scope '{result.scope}'",
                headers=headers,
            )

    def _consume_bucket(
        self,
        *,
        key: str,
        limit: int,
        window_seconds: int,
        scope: str,
    ) -> _BucketResult:
        """Increment one Redis counter bucket and ensure TTL is set."""
        count = int(self._redis.incr(key))
        if count == 1:
            self._redis.expire(key, window_seconds)
            ttl_seconds = window_seconds
        else:
            ttl_seconds = int(self._redis.ttl(key))
            if ttl_seconds <= 0:
                self._redis.expire(key, window_seconds)
                ttl_seconds = window_seconds

        return _BucketResult(
            count=count,
            ttl_seconds=ttl_seconds,
            limit=limit,
            scope=scope,
        )
