"""Integration tests for public vacancy apply hardening controls."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from time import time
from typing import Any
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.core.models.base import Base
from hrm_backend.main import app
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dependencies.vacancies import get_public_apply_rate_limiter
from hrm_backend.vacancies.services.public_apply_rate_limiter import PublicApplyRateLimiter

pytestmark = pytest.mark.anyio


class InMemoryCandidateStorage:
    """In-memory object storage replacement for integration tests."""

    def __init__(self) -> None:
        self._store: dict[str, bytes] = {}

    def put_object(
        self,
        *,
        object_key: str,
        data: bytes,
        mime_type: str,
        enable_sse: bool,
    ) -> None:
        del mime_type, enable_sse
        self._store[object_key] = data

    def get_object(self, *, object_key: str) -> bytes:
        return self._store[object_key]


@dataclass
class _BucketState:
    count: int = 0
    expires_at: float | None = None


class FakeRedis:
    """Minimal in-memory Redis emulator for integration limiter tests."""

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


@pytest.fixture()
def sqlite_database_url(tmp_path: Path) -> str:
    """Provide temporary SQLite URL for integration tests."""
    return f"sqlite+pysqlite:///{tmp_path / 'public_apply_hardening.db'}"


@pytest.fixture()
def configured_app(sqlite_database_url: str):
    """Configure app dependency overrides for public apply hardening tests."""
    settings = AppSettings(
        database_url=sqlite_database_url,
        redis_url="redis://localhost:6379/15",
        jwt_secret="integration-secret-with-minimum-32-bytes",
        cv_max_size_bytes=1024,
        public_apply_rate_limit_ip=20,
        public_apply_rate_limit_ip_window_seconds=15 * 60,
        public_apply_rate_limit_ip_vacancy=20,
        public_apply_rate_limit_ip_vacancy_window_seconds=15 * 60,
        public_apply_rate_limit_email_vacancy=20,
        public_apply_rate_limit_email_vacancy_window_seconds=24 * 60 * 60,
        public_apply_dedup_window_seconds=24 * 60 * 60,
        public_apply_email_cooldown_seconds=60,
    )
    storage = InMemoryCandidateStorage()
    redis = FakeRedis()
    context_holder = {
        "context": AuthContext(
            subject_id=uuid4(),
            role="hr",
            session_id=uuid4(),
            token_id=uuid4(),
            expires_at=9999999999,
        )
    }

    def _get_settings_override() -> AppSettings:
        return settings

    def _get_auth_context_override() -> AuthContext:
        return context_holder["context"]

    def _get_storage_override() -> InMemoryCandidateStorage:
        return storage

    def _get_rate_limiter_override() -> PublicApplyRateLimiter:
        return PublicApplyRateLimiter(
            redis_client=redis,  # type: ignore[arg-type]
            key_prefix=settings.public_apply_rate_limit_redis_prefix,
            ip_limit=settings.public_apply_rate_limit_ip,
            ip_window_seconds=settings.public_apply_rate_limit_ip_window_seconds,
            ip_vacancy_limit=settings.public_apply_rate_limit_ip_vacancy,
            ip_vacancy_window_seconds=settings.public_apply_rate_limit_ip_vacancy_window_seconds,
            email_vacancy_limit=settings.public_apply_rate_limit_email_vacancy,
            email_vacancy_window_seconds=settings.public_apply_rate_limit_email_vacancy_window_seconds,
        )

    app.dependency_overrides[get_settings] = _get_settings_override
    app.dependency_overrides[get_current_auth_context] = _get_auth_context_override
    app.dependency_overrides[get_candidate_storage] = _get_storage_override
    app.dependency_overrides[get_public_apply_rate_limiter] = _get_rate_limiter_override

    engine = create_engine(sqlite_database_url, future=True)
    Base.metadata.create_all(engine)
    try:
        yield app, settings, sqlite_database_url
    finally:
        app.dependency_overrides.pop(get_settings, None)
        app.dependency_overrides.pop(get_current_auth_context, None)
        app.dependency_overrides.pop(get_candidate_storage, None)
        app.dependency_overrides.pop(get_public_apply_rate_limiter, None)
        engine.dispose()


@pytest.fixture()
async def api_client(configured_app) -> AsyncClient:
    """Provide async API client for public apply integration tests."""
    configured, *_ = configured_app
    async with AsyncClient(
        transport=ASGITransport(app=configured),
        base_url="http://testserver",
    ) as client:
        yield client


def _load_events(database_url: str) -> list[AuditEvent]:
    """Load ordered audit events from database URL."""
    engine = create_engine(database_url, future=True)
    try:
        with Session(engine) as session:
            return list(
                session.execute(
                    select(AuditEvent).order_by(AuditEvent.occurred_at, AuditEvent.event_id)
                ).scalars()
            )
    finally:
        engine.dispose()


async def _create_vacancy(api_client: AsyncClient, suffix: str) -> str:
    response = await api_client.post(
        "/api/v1/vacancies",
        json={
            "title": f"Vacancy {suffix}",
            "description": "Build hiring pipeline",
            "department": "Engineering",
            "status": "open",
        },
    )
    assert response.status_code == 200
    return response.json()["vacancy_id"]


async def _apply_public(
    api_client: AsyncClient,
    *,
    vacancy_id: str,
    email: str,
    cv_seed: str,
    website: str | None = None,
) -> Any:
    content = f"cv-content-{cv_seed}".encode()
    checksum = hashlib.sha256(content).hexdigest()
    data: dict[str, str] = {
        "first_name": "Alice",
        "last_name": "Doe",
        "email": email,
        "phone": "+375291112233",
        "consent_confirmed": "true",
        "checksum_sha256": checksum,
    }
    if website is not None:
        data["website"] = website
    return await api_client.post(
        f"/api/v1/vacancies/{vacancy_id}/applications",
        data=data,
        files={"file": ("cv.pdf", content, "application/pdf")},
    )


def _extract_apply_failure_reasons(database_url: str) -> list[str]:
    return [
        str(event.reason)
        for event in _load_events(database_url)
        if event.action == "vacancy:apply_public" and event.result == "failure"
    ]


async def test_public_apply_honeypot_rejected_with_reason_code(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify honeypot field blocks request and writes specific audit reason."""
    _, _, database_url = configured_app
    vacancy_id = await _create_vacancy(api_client, "honeypot")

    response = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="honeypot@example.com",
        cv_seed="honeypot",
        website="https://bot.invalid",
    )
    assert response.status_code == 422

    reasons = _extract_apply_failure_reasons(database_url)
    assert "honeypot_triggered" in reasons


async def test_public_apply_rate_limit_ip_scope_returns_429_headers(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify IP rate limit returns 429 with required headers and reason code."""
    _, settings, database_url = configured_app
    settings.public_apply_rate_limit_ip = 2
    settings.public_apply_rate_limit_ip_vacancy = 20
    settings.public_apply_rate_limit_email_vacancy = 20
    settings.public_apply_email_cooldown_seconds = 0
    settings.public_apply_dedup_window_seconds = 0

    vacancy_1 = await _create_vacancy(api_client, "ip-1")
    vacancy_2 = await _create_vacancy(api_client, "ip-2")
    vacancy_3 = await _create_vacancy(api_client, "ip-3")

    assert (
        await _apply_public(
            api_client,
            vacancy_id=vacancy_1,
            email="ip-1@example.com",
            cv_seed="ip-1",
        )
    ).status_code == 200
    assert (
        await _apply_public(
            api_client,
            vacancy_id=vacancy_2,
            email="ip-2@example.com",
            cv_seed="ip-2",
        )
    ).status_code == 200
    blocked = await _apply_public(
        api_client,
        vacancy_id=vacancy_3,
        email="ip-3@example.com",
        cv_seed="ip-3",
    )
    assert blocked.status_code == 429
    expected_headers = {
        "Retry-After",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "X-RateLimit-Reset",
    }
    expected_headers_lower = {header.lower() for header in expected_headers}
    assert expected_headers_lower <= set(blocked.headers.keys())

    reasons = _extract_apply_failure_reasons(database_url)
    assert "rate_limited" in reasons


async def test_public_apply_rate_limit_ip_vacancy_scope(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify IP+vacancy rate limit blocks repeated submissions to one vacancy."""
    _, settings, _ = configured_app
    settings.public_apply_rate_limit_ip = 20
    settings.public_apply_rate_limit_ip_vacancy = 1
    settings.public_apply_rate_limit_email_vacancy = 20
    settings.public_apply_email_cooldown_seconds = 0
    settings.public_apply_dedup_window_seconds = 0
    vacancy_id = await _create_vacancy(api_client, "ip-vacancy")

    first = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="ip-vacancy-1@example.com",
        cv_seed="ip-vacancy-1",
    )
    second = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="ip-vacancy-2@example.com",
        cv_seed="ip-vacancy-2",
    )
    assert first.status_code == 200
    assert second.status_code == 429


async def test_public_apply_rate_limit_email_vacancy_scope(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify email+vacancy rate limit is enforced for repeated submissions."""
    _, settings, _ = configured_app
    settings.public_apply_rate_limit_ip = 20
    settings.public_apply_rate_limit_ip_vacancy = 20
    settings.public_apply_rate_limit_email_vacancy = 1
    settings.public_apply_email_cooldown_seconds = 0
    settings.public_apply_dedup_window_seconds = 0
    vacancy_id = await _create_vacancy(api_client, "email-vacancy")

    first = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="same@example.com",
        cv_seed="email-vacancy-1",
    )
    second = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="same@example.com",
        cv_seed="email-vacancy-2",
    )
    assert first.status_code == 200
    assert second.status_code == 429


async def test_public_apply_duplicate_submission_rejected(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify duplicate checksum+vacancy is blocked with duplicate reason code."""
    _, settings, database_url = configured_app
    settings.public_apply_rate_limit_ip = 20
    settings.public_apply_rate_limit_ip_vacancy = 20
    settings.public_apply_rate_limit_email_vacancy = 20
    settings.public_apply_email_cooldown_seconds = 0
    settings.public_apply_dedup_window_seconds = 24 * 60 * 60
    vacancy_id = await _create_vacancy(api_client, "duplicate")

    first = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="duplicate-1@example.com",
        cv_seed="same-seed",
    )
    second = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="duplicate-2@example.com",
        cv_seed="same-seed",
    )
    assert first.status_code == 200
    assert second.status_code == 409

    reasons = _extract_apply_failure_reasons(database_url)
    assert "duplicate_submission" in reasons


async def test_public_apply_email_cooldown_rejected(
    configured_app,
    api_client: AsyncClient,
) -> None:
    """Verify cooldown guard rejects immediate second submission for one email+vacancy."""
    _, settings, database_url = configured_app
    settings.public_apply_rate_limit_ip = 20
    settings.public_apply_rate_limit_ip_vacancy = 20
    settings.public_apply_rate_limit_email_vacancy = 20
    settings.public_apply_email_cooldown_seconds = 60
    settings.public_apply_dedup_window_seconds = 0
    vacancy_id = await _create_vacancy(api_client, "cooldown")

    first = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="cooldown@example.com",
        cv_seed="cooldown-1",
    )
    second = await _apply_public(
        api_client,
        vacancy_id=vacancy_id,
        email="cooldown@example.com",
        cv_seed="cooldown-2",
    )
    assert first.status_code == 200
    assert second.status_code == 409

    reasons = _extract_apply_failure_reasons(database_url)
    assert "cooldown_active" in reasons
