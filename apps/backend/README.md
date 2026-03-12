# Backend (uv)

## Setup
- Install dependencies: `uv sync --project .`
- Run app: `uv run --project . uvicorn hrm_backend.main:app --reload`
- Run CV parsing worker loop: `uv run --project . python -m hrm_backend.candidates.workers.cv_parsing_worker`
- Run tests: `uv run --project . pytest -q`
- Run only unit tests: `uv run --project . pytest -q tests/unit`
- Run only integration tests: `uv run --project . pytest -q tests/integration`
- Run lint: `uv run --project . ruff check .`
- Run migrations: `uv run --project . alembic -c alembic.ini upgrade head`

## Docker
- Built by root compose stack using `docker/backend.Dockerfile`.
- Container health endpoint: `GET /health`.
- Default compose scoring path stays external-host compatible:
  `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
- `backend` and `backend-worker` now include `host.docker.internal:host-gateway` for Linux-safe access to host Ollama without changing the default compose command.
- Optional self-contained AI runtime:
  `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build`
- Optional operator-facing compose scoring smoke:
  `./scripts/smoke-scoring-compose.sh`

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
- `OBJECT_STORAGE_SSE_ENABLED`
- `CV_ALLOWED_MIME_TYPES`
- `CV_MAX_SIZE_BYTES`
- `CV_PARSING_MAX_ATTEMPTS`
- `MATCH_SCORING_MAX_ATTEMPTS`
- `SCORING_LOW_CONFIDENCE_THRESHOLD`
- `MATCH_SCORING_MODEL_NAME`
- `MATCH_SCORING_REQUEST_TIMEOUT_SECONDS`
- `MATCH_SCORING_QUEUE_NAME`
- `OLLAMA_BASE_URL`
- `GOOGLE_CALENDAR_ENABLED`
- `HRM_JWT_SECRET`
- `HRM_JWT_ALGORITHM`
- `HRM_ACCESS_TOKEN_TTL_SECONDS`
- `HRM_REFRESH_TOKEN_TTL_SECONDS`
- `HRM_AUTH_REDIS_PREFIX`
- `CELERY_BROKER_URL`
- `CELERY_RESULT_BACKEND`
- `CELERY_TASK_DEFAULT_QUEUE`
- `CELERY_TASK_TIME_LIMIT_SECONDS`
- Settings loading policy:
  - Use `pydantic BaseSettings` models for all runtime config.
  - Canonical settings module: `hrm_backend/settings.py` (`AppSettings`, `get_settings`).

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

## Recruitment APIs (Phase 1)
- Candidate profile + CV:
  - `POST /api/v1/candidates`
  - `GET /api/v1/candidates/{candidate_id}`
  - `PATCH /api/v1/candidates/{candidate_id}`
  - `GET /api/v1/candidates`
    - Recruiter list contract is paginated: `items`, `total`, `limit`, `offset`.
    - Supported optional query params:
      `limit`, `offset`, `search`, `location`, `current_title`, `skill`,
      `analysis_ready`, `min_years_experience`, `vacancy_id`, `in_pipeline_only`, `stage`.
    - `search` performs case-insensitive contains across candidate base fields plus active parsed CV
      `summary`, `skills`, workplace employer/position, and normalized titles.
    - `analysis_ready=true` requires an active CV with both `parsed_profile_json` and `parsed_at`.
      `analysis_ready=false` returns candidates with missing or incomplete parsed analysis.
    - `vacancy_id` adds `vacancy_stage` from the latest transition for that vacancy.
      `in_pipeline_only=true` and `stage` are valid only together with `vacancy_id`.
    - List rows use an additive `CandidateListItemResponse` contract and include:
      `analysis_ready`, `detected_language`, `parsed_at`, `years_experience`, `skills`,
      and `vacancy_stage`.
  - `POST /api/v1/candidates/{candidate_id}/cv`
  - `GET /api/v1/candidates/{candidate_id}/cv`
  - `GET /api/v1/candidates/{candidate_id}/cv/parsing-status`
- Vacancy + pipeline:
  - `POST /api/v1/vacancies`
  - `GET /api/v1/vacancies`
  - `GET /api/v1/vacancies/{vacancy_id}`
  - `PATCH /api/v1/vacancies/{vacancy_id}`
  - `POST /api/v1/pipeline/transitions`
- Match scoring:
  - `POST /api/v1/vacancies/{vacancy_id}/match-scores`
  - `GET /api/v1/vacancies/{vacancy_id}/match-scores`
  - `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`
  - `MatchScoreResponse` remains additive and now includes:
    `requires_manual_review`, `manual_review_reason`, and `confidence_threshold`.
  - Manual-review semantics:
    `requires_manual_review=true` only when `status="succeeded"` and persisted
    `confidence < SCORING_LOW_CONFIDENCE_THRESHOLD`.
  - Current fallback reason code:
    `manual_review_reason="low_confidence"`.
  - `confidence_threshold` is echoed only for succeeded score responses so the frontend can explain
    why a score is treated as assistive-only.
