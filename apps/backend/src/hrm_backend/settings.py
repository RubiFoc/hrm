"""Application-level runtime settings for the backend service.

This module is the canonical settings entrypoint for all backend packages.
Domain packages should consume `AppSettings` / `get_settings` from here.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic.v1 import BaseSettings, Field, validator


class AppSettings(BaseSettings):
    """Typed application settings loaded from environment and `.env`.

    Attributes:
        backend_port: Backend HTTP port.
        database_url: PostgreSQL DSN.
        redis_url: Redis DSN.
        object_storage_endpoint: Object storage endpoint URL.
        object_storage_access_key: Object storage access key.
        object_storage_secret_key: Object storage secret key.
        object_storage_bucket: Object storage bucket for documents.
        ollama_base_url: Ollama API base URL.
        google_calendar_enabled: Google Calendar integration feature flag.
        jwt_secret: JWT secret key.
        jwt_algorithm: JWT algorithm.
        access_token_ttl_seconds: Access token ttl in seconds.
        refresh_token_ttl_seconds: Refresh token ttl in seconds.
        redis_prefix: Redis key prefix for auth denylist.
    """

    backend_port: int = Field(default=8000, env="BACKEND_PORT", gt=0)
    database_url: str = Field(
        default="postgresql+psycopg://hrm:hrm@postgres:5432/hrm",
        env="DATABASE_URL",
    )
    redis_url: str = Field(default="redis://redis:6379/0", env="REDIS_URL")
    object_storage_endpoint: str = Field(
        default="http://minio:9000",
        env="OBJECT_STORAGE_ENDPOINT",
    )
    object_storage_access_key: str = Field(
        default="minioadmin",
        env="OBJECT_STORAGE_ACCESS_KEY",
    )
    object_storage_secret_key: str = Field(
        default="minioadmin",
        env="OBJECT_STORAGE_SECRET_KEY",
    )
    object_storage_bucket: str = Field(
        default="hrm-documents",
        env="OBJECT_STORAGE_BUCKET",
    )
    ollama_base_url: str = Field(default="http://host.docker.internal:11434", env="OLLAMA_BASE_URL")
    google_calendar_enabled: bool = Field(default=False, env="GOOGLE_CALENDAR_ENABLED")
    jwt_secret: str = Field(default="hrm-dev-secret-change-me", env="HRM_JWT_SECRET")
    jwt_algorithm: str = Field(default="HS256", env="HRM_JWT_ALGORITHM")
    access_token_ttl_seconds: int = Field(default=15 * 60, env="HRM_ACCESS_TOKEN_TTL_SECONDS", gt=0)
    refresh_token_ttl_seconds: int = Field(
        default=7 * 24 * 60 * 60,
        env="HRM_REFRESH_TOKEN_TTL_SECONDS",
        gt=0,
    )
    redis_prefix: str = Field(default="auth:deny", env="HRM_AUTH_REDIS_PREFIX")

    @validator(
        "database_url",
        "redis_url",
        "object_storage_endpoint",
        "object_storage_access_key",
        "object_storage_secret_key",
        "object_storage_bucket",
        "ollama_base_url",
        "jwt_secret",
        "jwt_algorithm",
        "redis_prefix",
    )
    def _normalize_required_strings(cls, value: str) -> str:
        """Normalize required string settings and reject empty values.

        Args:
            value: Raw configured value.

        Returns:
            str: Trimmed non-empty value.

        Raises:
            ValueError: If the normalized value is empty.
        """
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    class Config:
        """Base settings config with local `.env` support.

        The custom source is required because python-dotenv is not installed
        in the current environment and we still need `.env` loading behavior.
        """

        env_file_paths = (".env", "../../.env")
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

        @classmethod
        def customise_sources(
            cls,
            init_settings,
            env_settings,
            file_secret_settings,
        ):
            """Inject custom `.env` reader without external dotenv dependency."""
            return (
                init_settings,
                env_settings,
                _dotenv_settings_source,
                file_secret_settings,
            )


@lru_cache(maxsize=1)
def get_settings() -> AppSettings:
    """Build and cache application settings.

    Returns:
        AppSettings: Resolved backend settings object.
    """
    return AppSettings()


def _dotenv_settings_source(settings: BaseSettings) -> dict[str, Any]:
    """Read `.env` values and map them to model field names.

    Args:
        settings: Target settings instance with field metadata.

    Returns:
        dict[str, Any]: Field-name keyed values parsed from `.env` files.
    """
    config = settings.__config__
    raw_env = _read_dotenv_files(
        file_paths=config.env_file_paths,
        encoding=config.env_file_encoding,
    )
    case_sensitive = bool(config.case_sensitive)
    normalized_env = (
        raw_env
        if case_sensitive
        else {key.lower(): value for key, value in raw_env.items()}
    )

    resolved_values: dict[str, Any] = {}
    for field_name, model_field in settings.__fields__.items():
        env_meta = model_field.field_info.extra.get("env")
        if env_meta is None:
            env_names = [field_name]
        elif isinstance(env_meta, str):
            env_names = [env_meta]
        else:
            env_names = list(env_meta)

        for env_name in env_names:
            lookup_key = env_name if case_sensitive else env_name.lower()
            if lookup_key in normalized_env:
                resolved_values[field_name] = normalized_env[lookup_key]
                break

    return resolved_values


def _read_dotenv_files(file_paths: tuple[str, ...], encoding: str) -> dict[str, str]:
    """Load key/value pairs from `.env` files.

    Args:
        file_paths: Candidate paths resolved from current working directory.
        encoding: File read encoding.

    Returns:
        dict[str, str]: Parsed `.env` values with last-one-wins semantics.
    """
    merged: dict[str, str] = {}
    for raw_path in file_paths:
        path = Path(raw_path)
        if not path.is_file():
            continue

        for raw_line in path.read_text(encoding=encoding).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:].strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            normalized_key = key.strip()
            normalized_value = _strip_quotes(value.strip())
            if normalized_key:
                merged[normalized_key] = normalized_value

    return merged


def _strip_quotes(value: str) -> str:
    """Drop symmetric single/double quotes from `.env` scalar values.

    Args:
        value: Raw value from `.env`.

    Returns:
        str: Normalized scalar value.
    """
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
