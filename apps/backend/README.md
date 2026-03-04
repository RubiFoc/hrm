# Backend (uv)

## Setup
- Install dependencies: `uv sync --project .`
- Run app: `uv run --project . uvicorn hrm_backend.main:app --reload`
- Run tests: `uv run --project . pytest -q`
- Run only unit tests: `uv run --project . pytest -q tests/unit`
- Run only integration tests: `uv run --project . pytest -q tests/integration`
- Run lint: `uv run --project . ruff check .`
- Run migrations: `uv run --project . alembic -c alembic.ini upgrade head`

## Docker
- Built by root compose stack using `docker/backend.Dockerfile`.
- Container health endpoint: `GET /health`.

## Authentication Baseline (TASK-01-02)
- Auth endpoints:
  - `POST /api/v1/auth/login`
  - `POST /api/v1/auth/refresh`
  - `POST /api/v1/auth/logout`
  - `GET /api/v1/auth/me`
- Protected API routes require `Authorization: Bearer <access_token>`.
- Runtime auth config:
  - `HRM_JWT_SECRET`
  - `HRM_JWT_ALGORITHM`
  - `HRM_ACCESS_TOKEN_TTL_SECONDS`
  - `HRM_REFRESH_TOKEN_TTL_SECONDS`
  - `HRM_AUTH_REDIS_PREFIX`
  - `REDIS_URL`

## Application Runtime Config Baseline
- `BACKEND_PORT`
- `DATABASE_URL`
- `REDIS_URL`
- `OBJECT_STORAGE_ENDPOINT`
- `OBJECT_STORAGE_ACCESS_KEY`
- `OBJECT_STORAGE_SECRET_KEY`
- `OBJECT_STORAGE_BUCKET`
- `OLLAMA_BASE_URL`
- `GOOGLE_CALENDAR_ENABLED`
- `HRM_JWT_SECRET`
- `HRM_JWT_ALGORITHM`
- `HRM_ACCESS_TOKEN_TTL_SECONDS`
- `HRM_REFRESH_TOKEN_TTL_SECONDS`
- `HRM_AUTH_REDIS_PREFIX`
- Settings loading policy:
  - Use `pydantic BaseSettings` models for all runtime config.
  - Canonical settings module: `hrm_backend/settings.py` (`AppSettings`, `get_settings`).
  - Compatibility shims are temporary:
    `hrm_backend.auth.utils.settings` and `hrm_backend.core.config.settings`.

## Alembic
- Create revision: `uv run --project . alembic -c alembic.ini revision -m \"<message>\"`
- Upgrade DB: `uv run --project . alembic -c alembic.ini upgrade head`
- Downgrade last revision: `uv run --project . alembic -c alembic.ini downgrade -1`

## Backend Package Standard
- Extraction-ready domain components must use package decomposition:
  `models`, `schemas`, `services`, `dao`, `routers`, `utils`, `dependencies`.
- Domain infrastructure adapters are nested inside domain package (for example `auth/redis`).
- Tests are split by level and package:
  - `tests/unit/<package>/...`
  - `tests/integration/<package>/...`
