# Backend (uv)

## Setup
- Install dependencies: `uv sync --project .`
- Run app: `uv run --project . uvicorn hrm_backend.main:app --reload`
- Run tests: `uv run --project . pytest -q`
- Run lint: `uv run --project . ruff check .`

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
  - `HRM_AUTH_SECRET`
  - `HRM_ACCESS_TOKEN_TTL_SECONDS`
  - `HRM_REFRESH_TOKEN_TTL_SECONDS`
