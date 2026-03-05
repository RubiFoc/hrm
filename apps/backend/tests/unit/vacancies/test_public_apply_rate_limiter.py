"""Unit tests for Redis-backed public apply rate limiter."""

from __future__ import annotations

from dataclasses import dataclass
from time import time

import pytest

from hrm_backend.vacancies.schemas.application import PUBLIC_APPLY_REASON_RATE_LIMITED
from hrm_backend.vacancies.services.public_apply_exceptions import PublicApplyRejectedError
from hrm_backend.vacancies.services.public_apply_rate_limiter import PublicApplyRateLimiter


@dataclass
class _BucketState:
    count: int = 0
    expires_at: float | None = None


class FakeRedis:
    """Minimal in-memory Redis emulator for limiter unit tests."""

    def __init__(self) -> None:
        self._store: dict[str, _BucketState] = {}
        self._now = time()

    def incr(self, key: str) -> int:
        self._cleanup_key_if_expired(key)
        state = self._store.setdefault(key, _BucketState())
        state.count += 1
        return state.count

    def expire(self, key: str, seconds: int) -> bool:
        state = self._store.setdefault(key, _BucketState())
        state.expires_at = self._now + seconds
        return True

    def ttl(self, key: str) -> int:
        self._cleanup_key_if_expired(key)
        state = self._store.get(key)
        if state is None:
            return -2
        if state.expires_at is None:
            return -1
        return max(int(state.expires_at - self._now), 0)

    def _cleanup_key_if_expired(self, key: str) -> None:
        state = self._store.get(key)
        if state is None or state.expires_at is None:
            return
        if state.expires_at > self._now:
            return
        self._store.pop(key, None)


def test_limiter_blocks_when_ip_bucket_exceeded() -> None:
    """Verify limiter rejects requests when IP bucket crosses threshold."""
    limiter = PublicApplyRateLimiter(
        redis_client=FakeRedis(),
        key_prefix="test:apply",
        ip_limit=2,
        ip_window_seconds=60,
        ip_vacancy_limit=20,
        ip_vacancy_window_seconds=60,
        email_vacancy_limit=20,
        email_vacancy_window_seconds=60,
    )

    limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-1", email="user-1@example.com")
    limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-2", email="user-2@example.com")

    with pytest.raises(PublicApplyRejectedError) as exc_info:
        limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-3", email="user-3@example.com")

    assert exc_info.value.reason_code == PUBLIC_APPLY_REASON_RATE_LIMITED
    assert exc_info.value.status_code == 429
    assert exc_info.value.headers is not None
    expected_headers = {
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    }
    assert expected_headers <= set(exc_info.value.headers)


def test_limiter_blocks_on_ip_vacancy_scope_before_global_ip_scope() -> None:
    """Verify dedicated IP+vacancy bucket can block while global IP bucket still allows."""
    limiter = PublicApplyRateLimiter(
        redis_client=FakeRedis(),
        key_prefix="test:apply",
        ip_limit=20,
        ip_window_seconds=60,
        ip_vacancy_limit=1,
        ip_vacancy_window_seconds=60,
        email_vacancy_limit=20,
        email_vacancy_window_seconds=60,
    )

    limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-1", email="user-1@example.com")

    with pytest.raises(PublicApplyRejectedError) as exc_info:
        limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-1", email="user-2@example.com")

    assert exc_info.value.reason_code == PUBLIC_APPLY_REASON_RATE_LIMITED
    assert "ip+vacancy" in str(exc_info.value.detail)


def test_limiter_normalizes_email_for_email_vacancy_scope() -> None:
    """Verify same email in different case shares one email+vacancy limiter bucket."""
    limiter = PublicApplyRateLimiter(
        redis_client=FakeRedis(),
        key_prefix="test:apply",
        ip_limit=20,
        ip_window_seconds=60,
        ip_vacancy_limit=20,
        ip_vacancy_window_seconds=60,
        email_vacancy_limit=1,
        email_vacancy_window_seconds=60,
    )

    limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-1", email="User@example.com")

    with pytest.raises(PublicApplyRejectedError) as exc_info:
        limiter.enforce(ip="10.0.0.1", vacancy_id="vacancy-1", email="user@example.com")

    assert exc_info.value.reason_code == PUBLIC_APPLY_REASON_RATE_LIMITED
    assert "email+vacancy" in str(exc_info.value.detail)
