"""Unit tests for auth domain BaseSettings configuration."""

from __future__ import annotations

import pytest
from pydantic.v1 import ValidationError

from hrm_backend.settings import AppSettings, get_settings


def test_get_settings_reads_values_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verify canonical settings are loaded from environment variables."""
    monkeypatch.setenv("BACKEND_PORT", "8010")
    monkeypatch.setenv("DATABASE_URL", "postgresql://test-user:test-pass@localhost:5432/hrm_test")
    monkeypatch.setenv("HRM_JWT_SECRET", "env-secret-123")
    monkeypatch.setenv("HRM_JWT_ALGORITHM", "HS256")
    monkeypatch.setenv("HRM_ACCESS_TOKEN_TTL_SECONDS", "1200")
    monkeypatch.setenv("HRM_REFRESH_TOKEN_TTL_SECONDS", "7200")
    monkeypatch.setenv("REDIS_URL", "redis://localhost:6380/5")
    monkeypatch.setenv("HRM_AUTH_REDIS_PREFIX", "auth:test")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.backend_port == 8010
    assert settings.database_url.endswith("/hrm_test")
    assert settings.jwt_secret == "env-secret-123"
    assert settings.jwt_algorithm == "HS256"
    assert settings.access_token_ttl_seconds == 1200
    assert settings.refresh_token_ttl_seconds == 7200
    assert settings.redis_url == "redis://localhost:6380/5"
    assert settings.redis_prefix == "auth:test"

    get_settings.cache_clear()


def test_app_settings_rejects_empty_required_string_values() -> None:
    """Verify canonical settings validation rejects blank critical strings."""
    with pytest.raises(ValidationError):
        AppSettings(jwt_secret="   ")


def test_app_settings_rejects_non_positive_numeric_values() -> None:
    """Verify positive numeric constraints for port and token ttl settings."""
    with pytest.raises(ValidationError):
        AppSettings(backend_port=0)

    with pytest.raises(ValidationError):
        AppSettings(access_token_ttl_seconds=0)


def test_get_settings_parses_cv_allowed_mime_types_from_csv_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify CSV-style MIME types env variable is accepted by settings loader."""
    monkeypatch.setenv("CV_ALLOWED_MIME_TYPES", "application/pdf, application/msword")

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.cv_allowed_mime_types == ("application/pdf", "application/msword")
    get_settings.cache_clear()


def test_get_settings_parses_cv_allowed_mime_types_from_json_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify JSON-array MIME types env variable remains supported."""
    monkeypatch.setenv(
        "CV_ALLOWED_MIME_TYPES",
        '["application/pdf","application/vnd.openxmlformats-officedocument.wordprocessingml.document"]',
    )

    get_settings.cache_clear()
    settings = get_settings()

    assert settings.cv_allowed_mime_types == (
        "application/pdf",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    )
    get_settings.cache_clear()
