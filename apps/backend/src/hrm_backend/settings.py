"""Application-level runtime settings for the backend service.

This module is the canonical settings entrypoint for all backend packages.
Domain packages should consume `AppSettings` / `get_settings` from here.
"""

from __future__ import annotations

import json
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
        cv_allowed_mime_types: Allowed MIME types for CV uploads.
        cv_max_size_bytes: Maximum allowed CV payload size.
        object_storage_sse_enabled: Whether uploads use SSE-S3 headers.
        cv_parsing_max_attempts: Maximum worker retries for CV parsing.
        employee_key_ttl_seconds: Default ttl for one-time employee registration keys.
        cors_allowed_origins: Allowed browser origins for credentialed API CORS requests.
        public_apply_rate_limit_redis_prefix: Redis key prefix for public apply rate limits.
        public_apply_rate_limit_ip: Rate limit threshold for IP bucket.
        public_apply_rate_limit_ip_window_seconds: Time window for IP bucket.
        public_apply_rate_limit_ip_vacancy: Rate limit threshold for IP+vacancy bucket.
        public_apply_rate_limit_ip_vacancy_window_seconds: Time window for IP+vacancy bucket.
        public_apply_rate_limit_email_vacancy: Rate limit threshold for email+vacancy bucket.
        public_apply_rate_limit_email_vacancy_window_seconds: Time window for email+vacancy bucket.
        public_apply_dedup_window_seconds:
            Deduplication window for vacancy+checksum anti-spam check.
        public_apply_email_cooldown_seconds: Cooldown between submissions by one email per vacancy.
        public_apply_blocked_alert_threshold_per_minute:
            Anomaly threshold for blocked submissions per minute.
        celery_broker_url: Celery broker URL.
        celery_result_backend: Celery result backend URL.
        celery_task_default_queue: Default Celery queue name.
        celery_task_time_limit_seconds: Hard Celery task timeout.
        celery_task_always_eager: Whether Celery executes tasks synchronously in-process.
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
    cv_allowed_mime_types: tuple[str, ...] = Field(
        default=(
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ),
        env="CV_ALLOWED_MIME_TYPES",
    )
    cv_max_size_bytes: int = Field(default=10 * 1024 * 1024, env="CV_MAX_SIZE_BYTES", gt=0)
    object_storage_sse_enabled: bool = Field(default=True, env="OBJECT_STORAGE_SSE_ENABLED")
    cv_parsing_max_attempts: int = Field(default=3, env="CV_PARSING_MAX_ATTEMPTS", gt=0)
    employee_key_ttl_seconds: int = Field(
        default=7 * 24 * 60 * 60,
        env="EMPLOYEE_KEY_TTL_SECONDS",
        gt=0,
    )
    cors_allowed_origins: tuple[str, ...] = Field(
        default=(
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ),
        env="HRM_CORS_ALLOWED_ORIGINS",
    )
    public_apply_rate_limit_redis_prefix: str = Field(
        default="vacancy:apply_public:rl",
        env="PUBLIC_APPLY_RATE_LIMIT_REDIS_PREFIX",
    )
    public_apply_rate_limit_ip: int = Field(default=10, env="PUBLIC_APPLY_RATE_LIMIT_IP", gt=0)
    public_apply_rate_limit_ip_window_seconds: int = Field(
        default=15 * 60,
        env="PUBLIC_APPLY_RATE_LIMIT_IP_WINDOW_SECONDS",
        gt=0,
    )
    public_apply_rate_limit_ip_vacancy: int = Field(
        default=5,
        env="PUBLIC_APPLY_RATE_LIMIT_IP_VACANCY",
        gt=0,
    )
    public_apply_rate_limit_ip_vacancy_window_seconds: int = Field(
        default=15 * 60,
        env="PUBLIC_APPLY_RATE_LIMIT_IP_VACANCY_WINDOW_SECONDS",
        gt=0,
    )
    public_apply_rate_limit_email_vacancy: int = Field(
        default=8,
        env="PUBLIC_APPLY_RATE_LIMIT_EMAIL_VACANCY",
        gt=0,
    )
    public_apply_rate_limit_email_vacancy_window_seconds: int = Field(
        default=24 * 60 * 60,
        env="PUBLIC_APPLY_RATE_LIMIT_EMAIL_VACANCY_WINDOW_SECONDS",
        gt=0,
    )
    public_apply_dedup_window_seconds: int = Field(
        default=24 * 60 * 60,
        env="PUBLIC_APPLY_DEDUP_WINDOW_SECONDS",
        ge=0,
    )
    public_apply_email_cooldown_seconds: int = Field(
        default=60,
        env="PUBLIC_APPLY_EMAIL_COOLDOWN_SECONDS",
        ge=0,
    )
    public_apply_blocked_alert_threshold_per_minute: int = Field(
        default=30,
        env="PUBLIC_APPLY_BLOCKED_ALERT_THRESHOLD_PER_MINUTE",
        gt=0,
    )
    celery_broker_url: str = Field(default="redis://redis:6379/0", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://redis:6379/0", env="CELERY_RESULT_BACKEND")
    celery_task_default_queue: str = Field(default="cv_parsing", env="CELERY_TASK_DEFAULT_QUEUE")
    celery_task_time_limit_seconds: int = Field(
        default=120,
        env="CELERY_TASK_TIME_LIMIT_SECONDS",
        gt=0,
    )
    celery_task_always_eager: bool = Field(default=False, env="CELERY_TASK_ALWAYS_EAGER")

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
        "public_apply_rate_limit_redis_prefix",
        "celery_broker_url",
        "celery_result_backend",
        "celery_task_default_queue",
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

    @validator("cv_allowed_mime_types", pre=True)
    def _parse_cv_allowed_mime_types(cls, value: object) -> tuple[str, ...]:
        """Parse CV MIME list from env string/list into normalized tuple.

        Args:
            value: Raw value loaded from environment.

        Returns:
            tuple[str, ...]: Normalized non-empty MIME type set preserving order.
        """
        if isinstance(value, tuple):
            raw_items = list(value)
        elif isinstance(value, list):
            raw_items = value
        elif isinstance(value, str):
            raw_items = value.split(",")
        else:
            raise ValueError("CV allowed MIME types must be list/tuple/comma-separated string")

        normalized: list[str] = []
        for raw_item in raw_items:
            item = str(raw_item).strip().lower()
            if item and item not in normalized:
                normalized.append(item)

        if not normalized:
            raise ValueError("CV allowed MIME types must contain at least one value")
        return tuple(normalized)

    @validator("cors_allowed_origins", pre=True)
    def _parse_cors_allowed_origins(cls, value: object) -> tuple[str, ...]:
        """Parse configured CORS origins from env string/list into normalized tuple.

        Args:
            value: Raw value loaded from environment.

        Returns:
            tuple[str, ...]: Normalized non-empty origin list preserving order.
        """
        if isinstance(value, tuple):
            raw_items = list(value)
        elif isinstance(value, list):
            raw_items = value
        elif isinstance(value, str):
            raw_items = value.split(",")
        else:
            raise ValueError("CORS allowed origins must be list/tuple/comma-separated string")

        normalized: list[str] = []
        for raw_item in raw_items:
            item = str(raw_item).strip().rstrip("/")
            if item and item not in normalized:
                normalized.append(item)

        if not normalized:
            raise ValueError("CORS allowed origins must contain at least one value")
        return tuple(normalized)

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

        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            """Parse selected env vars before model-level validation.

            Args:
                field_name: Target settings field name.
                raw_val: Raw scalar environment value.

            Returns:
                Any: Parsed value passed to pydantic field validation.
            """
            if field_name not in {"cv_allowed_mime_types", "cors_allowed_origins"}:
                return super().parse_env_var(field_name, raw_val)

            normalized = raw_val.strip()
            if not normalized:
                return []

            if normalized.startswith("["):
                try:
                    return json.loads(normalized)
                except json.JSONDecodeError:
                    return [item for item in normalized.split(",")]

            return [item for item in normalized.split(",")]


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
