# Operations Runbook

## Last Updated
- Date: 2026-03-19
- Updated by: coordinator + devops-engineer + architect

## Local Environment (Docker Compose)
### Prerequisites
- Docker Engine 24+ with Docker Compose plugin.
- Local Google Chrome/Chromium binary for browser smoke checks (`google-chrome`, `google-chrome-stable`, `chromium-browser`, `chromium`, or `CHROME_BIN` override).
- Available local ports: `5173`, `8000`, `5432`, `6379`, `9000`, `9001`.

### Bootstrap
1. Create runtime env file: `cp .env.example .env`
2. Validate compose file: `docker compose config`
3. Start stack: `docker compose up -d --build`
4. Verify status: `docker compose ps`
5. Run smoke suite: `./scripts/smoke-compose.sh`

Optional self-contained AI runtime:
1. Override scoring runtime target:
   `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build`
2. Verify real scoring lifecycle:
   `./scripts/smoke-scoring-compose.sh`

Compose bootstrap notes:
- `postgres-init` ensures `${POSTGRES_DB}` exists even when reusing an old data volume.
- `backend-migrate` runs `alembic upgrade head` before backend starts.
- `backend-worker` runs one Celery worker process for `cv_parsing`, `match_scoring`, and `interview_sync` against the same compose dependencies as `backend`.
- Backend container starts only after DB bootstrap and migrations complete successfully.
- Default compose startup remains external-host compatible for scoring:
  `OLLAMA_BASE_URL` stays `http://host.docker.internal:11434`.
- `backend` and `backend-worker` inject `host.docker.internal:host-gateway` so the external-host Ollama path is Linux-safe.
- Optional `ai-local` compose profile adds:
  - `ollama` with persistent model storage in `ollama_data`;
  - `ollama-init` one-shot bootstrap that pulls `MATCH_SCORING_MODEL_NAME`;
  - no published Ollama port, so the profile does not conflict with a host-installed Ollama.

Shortcut wrappers:
- `make up` / `just up`
- `make rebuild` / `just rebuild`
- `make clean-orphans` / `just clean-orphans`
- `make ps` / `just ps`
- `make smoke` / `just smoke`
- `make down` / `just down`

### Service Endpoints
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- Backend health: `http://localhost:8000/health`
- Backend auth register/login:
  - `http://localhost:8000/api/v1/auth/register`
  - `http://localhost:8000/api/v1/auth/login`
- MinIO API: `http://localhost:9000`
- MinIO Console: `http://localhost:9001`

### Audit and Reporting Exports
- Audit evidence export (admin-only, `audit:read`):
  - `GET /api/v1/audit/events/export?format=csv|jsonl&limit=...&offset=...`
  - Example:
    `curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/audit/events/export?format=csv&limit=5000" -o audit-events.csv`
- KPI snapshot export (leader/admin, `kpi_snapshot:read`):
  - `GET /api/v1/reporting/kpi-snapshots/export?period_month=YYYY-MM-01&format=csv|xlsx`
  - Example:
    `curl -H "Authorization: Bearer <token>" "http://localhost:8000/api/v1/reporting/kpi-snapshots/export?period_month=2026-03-01&format=xlsx" -o kpi-snapshot-2026-03.xlsx`

Runtime auth/browser integration settings:
- Frontend browser API base URL: `VITE_API_BASE_URL` (compose default: `http://localhost:8000`).
- Frontend Sentry envs:
  - `VITE_SENTRY_DSN`
  - `VITE_SENTRY_ENVIRONMENT` (compose default: `local-compose`)
  - `VITE_SENTRY_RELEASE` (compose default: `local-dev`)
  - `VITE_SENTRY_TRACES_SAMPLE_RATE` (compose default: `0.2`)
- Backend credentialed CORS allow list: `HRM_CORS_ALLOWED_ORIGINS` (compose default: `http://localhost:5173,http://127.0.0.1:5173`).
- Local object-storage encryption flag: `OBJECT_STORAGE_SSE_ENABLED=false` in compose/.env.example because the bundled MinIO dev stack does not provide KMS-backed SSE-S3; production/staging encryption remains a separate release control.

### Stop and Cleanup
- Stop stack: `docker compose down`
- Stop and remove volumes: `docker compose down -v`
- Wrapper cleanup: `make down-v` or `just down-v`

### Database Migrations (Alembic)
- Upgrade: `uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head`
- Downgrade one revision: `uv run --project apps/backend alembic -c apps/backend/alembic.ini downgrade -1`
- Offline SQL preview: `uv run --project apps/backend alembic -c apps/backend/alembic.ini upgrade head --sql`

### Admin Bootstrap
- First `admin` bootstrap is manual:
  `uv run --project apps/backend python -m hrm_backend.auth.cli.create_admin`

### CV Parsing Worker (Celery executor)
- Primary worker command:
  `uv run --project apps/backend celery -A hrm_backend.candidates.infra.celery.app:celery_app worker --loglevel=INFO --queues=cv_parsing,match_scoring,interview_sync`
- Compose service: `backend-worker`.
- Runtime lifecycle in DB (`cv_parsing_jobs` source of truth):
  `queued -> running -> succeeded/failed`.
- Native extraction behavior before RU/EN normalization:
  - `application/pdf` -> `pypdf` text extraction with PDF page traceability in evidence when available;
  - `application/vnd.openxmlformats-officedocument.wordprocessingml.document` -> OOXML zip/XML text extraction;
  - parsed CV artifacts are profession-agnostic and now include workplaces with employer plus held
    position, education, normalized titles/dates, generic skills, and indexed evidence fields;
  - broken archives/documents or empty extracted text fail closed and keep `analysis_ready=false`.
- Retry behavior is bounded by `CV_PARSING_MAX_ATTEMPTS`.
- Celery runtime settings:
  - `CELERY_BROKER_URL`
  - `CELERY_RESULT_BACKEND`
  - `CELERY_TASK_DEFAULT_QUEUE`
  - `CELERY_TASK_TIME_LIMIT_SECONDS`
- Upload validation settings:
  - `CV_ALLOWED_MIME_TYPES`
  - `CV_MAX_SIZE_BYTES`
  - `OBJECT_STORAGE_SSE_ENABLED`

### Match Scoring Worker (Celery executor)
- Primary worker command:
  `uv run --project apps/backend celery -A hrm_backend.candidates.infra.celery.app:celery_app worker --loglevel=INFO --queues=cv_parsing,match_scoring,interview_sync`
- Compose service: `backend-worker`.
- Runtime lifecycle in DB:
  - `match_scoring_jobs`: `queued -> running -> succeeded/failed`
  - `match_score_artifacts`: persisted score payloads keyed by vacancy, candidate, and active document
- Retry behavior is bounded by `MATCH_SCORING_MAX_ATTEMPTS`.
- Scoring runtime settings:
  - `MATCH_SCORING_MODEL_NAME`
  - `MATCH_SCORING_REQUEST_TIMEOUT_SECONDS`
  - `MATCH_SCORING_QUEUE_NAME`
  - `OLLAMA_BASE_URL`
- Compose runtime modes:
  - default: external-host Ollama via `http://host.docker.internal:11434`;
  - opt-in self-contained: `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build`.
- Optional compose-local AI services:
  - `ollama` exposes `11434` only inside the compose network and stores models in `ollama_data`;
  - `ollama-init` waits for `ollama`, pulls `MATCH_SCORING_MODEL_NAME`, and exits with code `0`.
- API endpoints:
  - `POST /api/v1/vacancies/{vacancy_id}/match-scores`
  - `GET /api/v1/vacancies/{vacancy_id}/match-scores`
  - `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`
- Expected precondition failure:
  - `409 Conflict` with `detail=CV analysis is not ready` when the active document is not yet parsed.

### Interview Sync Worker (Celery executor)
- Primary worker command:
  `uv run --project apps/backend celery -A hrm_backend.candidates.infra.celery.app:celery_app worker --loglevel=INFO --queues=cv_parsing,match_scoring,interview_sync`
- Compose service: `backend-worker`.
- Runtime queue: `interview_sync`.
- Calendar runtime settings:
  - `GOOGLE_CALENDAR_ENABLED`
  - `GOOGLE_CALENDAR_SERVICE_ACCOUNT_KEY_PATH`
  - `INTERVIEW_STAFF_CALENDAR_MAP_JSON`
  - `INTERVIEW_SYNC_QUEUE_NAME`
- Invite-link runtime settings:
  - `INTERVIEW_PUBLIC_TOKEN_SECRET`
  - `PUBLIC_FRONTEND_BASE_URL`
- Local compose acceptance does not require live Google Calendar verification; interview sync is diagnosed separately when interview runtime behavior changes.

### Smoke Verification
1. Validate normalized compose file: `docker compose config`.
2. Run canonical smoke script: `./scripts/smoke-compose.sh`.
3. Script validation scope:
   - `docker compose ps` contains `running + healthy` for `backend`, `postgres`, `redis`, `minio`;
   - `docker compose ps` contains `running` for `frontend` and `backend-worker`;
   - backend health endpoint returns `{"status":"ok"}`;
   - frontend and MinIO health endpoints respond successfully;
   - auth login endpoint returns token payload (`access_token`, `refresh_token`, `token_type`, `expires_in`, `session_id`).
   - headless Chrome completes `/login -> /api/v1/auth/login -> /api/v1/auth/me -> logout -> /login`;
   - browser auth requests target `http://localhost:8000` rather than relative `/api/...` on the frontend origin;
   - browser CORS preflight succeeds for cross-origin auth requests during login/logout.
   - staff API creates one deterministic `open` vacancy for browser candidate smoke;
  - headless Chrome completes `/candidate?vacancyId=...&vacancyTitle=... -> /api/v1/vacancies/{vacancy_id}/applications -> /api/v1/public/cv-parsing-jobs/{job_id}` using the checked-in valid PDF fixture `apps/backend/tests/fixtures/candidates/sample_cv_en.pdf`;
   - candidate browser requests target `http://localhost:8000` rather than relative `/api/...` on the frontend origin;
   - candidate smoke succeeds when public tracking reaches at least `queued` or `running`; `analysis_ready=true` is preferred but not required.
   - scoring/Ollama verification is intentionally excluded from compose smoke; validate the scoring slice through targeted unit and integration suites to avoid nondeterministic browser smoke failures.
   - Google Calendar verification is intentionally excluded from compose smoke; disabled or unreachable calendar integration does not block local compose baseline acceptance.
4. For reproducibility checks, run one teardown/restart cycle:
   - `docker compose down`
   - `docker compose up -d --build`
   - `./scripts/smoke-compose.sh`

### Optional AI-Local Scoring Smoke
1. Start the opt-in runtime:
   `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build`
2. Run the operator-facing verification:
   `./scripts/smoke-scoring-compose.sh`
3. Script validation scope:
   - `docker compose ps` reports `ollama=healthy` and `ollama-init` exited `0`;
   - `backend` and `backend-worker` both expose `OLLAMA_BASE_URL=http://ollama:11434`;
   - the pulled model matches `MATCH_SCORING_MODEL_NAME`;
   - one real candidate CV reaches `analysis_ready=true`;
   - scoring reaches `succeeded` through the canonical API lifecycle and returns the canonical score payload keys.
4. This smoke is opt-in and operator-facing; do not treat it as a mandatory CI/browser smoke gate.

### Login Browser Integration Diagnostics (`/login`)
- Symptoms:
  - login page loads, but browser submit/bootstrap requests fail while direct `curl` to backend succeeds;
  - browser console shows CORS or wrong-origin request failures for `/api/v1/auth/login`, `/api/v1/auth/me`, or `/api/v1/auth/logout`.
- Expected local config:
  - frontend `VITE_API_BASE_URL=http://localhost:8000`
  - backend `HRM_CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173`
- Preflight verification command:
  - `curl -i -X OPTIONS http://localhost:8000/api/v1/auth/login -H 'Origin: http://localhost:5173' -H 'Access-Control-Request-Method: POST' -H 'Access-Control-Request-Headers: content-type'`
- Browser verification command:
  - `python3 scripts/browser_auth_smoke.py --frontend-url http://localhost:5173/login --api-origin http://localhost:8000 --login <login> --password <password>`
- Expected preflight response:
  - `HTTP/1.1 200 OK`
  - `Access-Control-Allow-Origin: http://localhost:5173`
  - `Access-Control-Allow-Credentials: true`
- Browser smoke failure artifact:
  - screenshot path defaults to `/tmp/hrm-browser-auth-smoke/browser-auth-smoke-failure.png`
- Triage sequence:
  1. Inspect browser Network tab and confirm auth requests target `http://localhost:8000`, not relative `/api/...` on `localhost:5173`.
  2. Verify frontend env was rebuilt/restarted after changing `VITE_API_BASE_URL`.
  3. Verify backend response to preflight contains the expected `Access-Control-Allow-*` headers.
  4. Run `python3 scripts/browser_auth_smoke.py ...` with a known-good staff account to reproduce the browser path outside manual DevTools.
  5. If origin differs from default Vite dev host, add it to `HRM_CORS_ALLOWED_ORIGINS` and restart backend.

### Candidate Browser Integration Diagnostics (`/candidate`)
- Canonical deep link:
  - `/candidate?vacancyId=<uuid>&vacancyTitle=<display-only>`
- Tracking storage contract:
  - `sessionStorage["hrm_candidate_application_context"] = {"vacancyId": "...", "candidateId": "...", "parsingJobId": "...", "vacancyTitle": "..."}`
- Expected public API path sequence:
  - `POST /api/v1/vacancies/{vacancy_id}/applications`
  - `GET /api/v1/public/cv-parsing-jobs/{job_id}`
  - optional `GET /api/v1/public/cv-parsing-jobs/{job_id}/analysis`
- Browser verification command:
  - `python3 scripts/browser_candidate_apply_smoke.py --frontend-url http://localhost:5173/candidate --api-origin http://localhost:8000 --vacancy-id <vacancy_id> --vacancy-title <title>`
- Expected minimal success signal:
  - application submit returns `200/201`
  - `hrm_candidate_application_context` is present in session storage
  - public parsing status returns `queued`, `running`, or `succeeded`
- Triage sequence:
  1. Confirm the page was opened with a real `vacancyId` query param and not only the diagnostic fallback field.
  2. Inspect browser Network tab and confirm apply/tracking requests target `http://localhost:8000`, not relative `/api/...` on `localhost:5173`.
  3. Verify the staff-created smoke vacancy is still `status=open`.
  4. Check `sessionStorage["hrm_candidate_application_context"]` for `vacancyId`, `candidateId`, and `parsingJobId`.
  5. If status becomes `failed`, inspect `backend-worker` logs for native extraction errors such as unreadable PDF/DOCX or empty extracted text.
  6. If status never moves past `queued`, inspect `backend-worker` logs; compose smoke still treats `queued/running` as acceptable minimum.

### HR Shortlist Review Diagnostics (`/`)
- API path sequence:
  - `POST /api/v1/vacancies/{vacancy_id}/match-scores`
  - `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`
- Expected UI states:
  - `queued`
  - `running`
  - `succeeded`
  - `failed`
- Triage sequence:
1. Verify the selected candidate already has parsed CV analysis (`parsed_profile_json`, `evidence_json`, `parsed_at`).
  2. Confirm the parsed profile contains the expected workplace history, held positions, education,
     normalized titles/dates, and generic skills for the candidate domain you are scoring.
  3. If API returns `409`, re-check candidate parsing status before retrying score.
  4. If status remains `queued`, inspect `backend-worker` logs and confirm it listens on `match_scoring`.
  5. If status becomes `failed`, verify `OLLAMA_BASE_URL` reachability and model availability for `MATCH_SCORING_MODEL_NAME`.
  6. Confirm the latest `match_score_artifacts` row contains `score`, `confidence`, `summary`, requirements, evidence, and model metadata.
  7. For compose-local diagnosis, rerun `./scripts/smoke-scoring-compose.sh` after confirming `ollama` is healthy and `ollama-init` has exited `0`.

### Auth Denylist Failure Policy
- Auth validation is fail-closed when Redis denylist is unavailable.
- Expected behavior during Redis outage: protected auth checks return `503`.

### Public Apply Abuse Diagnostics
- Endpoint: `POST /api/v1/vacancies/{vacancy_id}/applications`.
- Expected anti-abuse responses:
  - `429 Too Many Requests` with headers:
    - `Retry-After`
    - `X-RateLimit-Limit`
    - `X-RateLimit-Remaining`
    - `X-RateLimit-Reset`
  - `409 Conflict` for duplicate submission and active cooldown.
  - `422` for honeypot trigger or validation failure.
- Audit failure reason codes (`action=vacancy:apply_public`):
  - `rate_limited`
  - `honeypot_triggered`
  - `duplicate_submission`
  - `cooldown_active`
  - `validation_failed`
- Triage sequence:
  1. Check API response status and reason code.
  2. Query audit evidence via admin API:
     - `GET /api/v1/audit/events?action=vacancy:apply_public&correlation_id=<X-Request-ID>`
  3. Verify Redis availability and limiter key activity.
  4. Compare blocked volume with alert threshold (`PUBLIC_APPLY_BLOCKED_ALERT_THRESHOLD_PER_MINUTE`).

### Admin Route Access Diagnostics (`/admin`)
- Guard behavior:
  - Missing auth token/session -> redirect to `/access-denied?reason=unauthorized`.
  - Authenticated non-admin role -> redirect to `/access-denied?reason=forbidden`.
  - Admin role -> allow route.
- Frontend telemetry requirements on admin route:
  - `workspace=admin`
  - `role`
  - `route`
- Triage sequence:
  1. Reproduce with browser local storage state (`hrm_access_token`, `hrm_user_role`).
  2. Verify redirect reason query param (`unauthorized` or `forbidden`).
  3. Check Sentry events for required tags and route breadcrumbs.

### Frontend Sentry Diagnostics (`TASK-11-10`)
- Critical routes covered by the baseline:
  - `/` -> `workspace=hr`, `route=/`
  - `/candidate` -> `workspace=candidate`, `route=/candidate`
  - `/login` -> `workspace=auth`, `route=/login`
  - `/admin`, `/admin/staff`, `/admin/employee-keys` -> `workspace=admin` with canonical route tags
- Expected capture paths:
  - route entry emits `workspace`, `role`, `route`
  - shared HTTP client captures request failures with `http_method`, optional `http_status`, and request path metadata
  - top-level render boundary captures React render failures and shows localized fallback UI
- Triage sequence:
  1. Verify frontend was rebuilt after changing any `VITE_SENTRY_*` environment variables.
  2. Open a critical route and confirm the Sentry event carries the expected `workspace`, `role`, and `route` tags.
  3. Trigger a known failing API request and confirm the Sentry event includes HTTP metadata.
  4. Check that release/environment values on the event match `VITE_SENTRY_RELEASE` and `VITE_SENTRY_ENVIRONMENT`.

### Admin Staff Management Diagnostics (`/admin/staff`)
- Endpoints:
  - `GET /api/v1/admin/staff`
  - `PATCH /api/v1/admin/staff/{staff_id}`
- Expected guard/error behavior:
  - `404` + `detail=staff_not_found`
  - `409` + `detail=self_modification_forbidden`
  - `409` + `detail=last_admin_protection`
  - `422` + `detail=empty_patch|unsupported_role|validation_failed`
- Audit actions:
  - `admin.staff:list`
  - `admin.staff:update`
- Triage sequence:
  1. Capture failing response with `X-Request-ID`.
  2. Check `detail` reason-code and request payload (`role`, `is_active` patch semantics).
  3. Query audit evidence via admin API by `correlation_id=<X-Request-ID>` and optionally narrow by `action`:
     - `GET /api/v1/audit/events?correlation_id=<X-Request-ID>`
     - `GET /api/v1/audit/events?action=admin.staff:update&correlation_id=<X-Request-ID>`
  4. For `last_admin_protection`, verify number of active admin rows in `staff_accounts`.
  5. For `self_modification_forbidden`, verify actor `subject_id` equals target `staff_id`.

### Admin Employee Key Lifecycle Diagnostics (`/admin/employee-keys`)
- Endpoints:
  - `GET /api/v1/admin/employee-keys`
  - `POST /api/v1/admin/employee-keys/{key_id}/revoke`
  - `POST /api/v1/admin/employee-keys` (create, backward-compatible)
- Expected guard/error behavior for revoke:
  - `404` + `detail=key_not_found`
  - `409` + `detail=key_already_used`
  - `409` + `detail=key_already_expired`
  - `409` + `detail=key_already_revoked`
  - `422` + `detail=validation_failed` (or framework validation payload)
- Audit actions:
  - `admin.employee_key:create`
  - `admin.employee_key:list`
  - `admin.employee_key:revoke`
- Triage sequence:
  1. Capture failing response with `X-Request-ID`.
  2. Check key lifecycle fields in DB (`used_at`, `expires_at`, `revoked_at`, `revoked_by_staff_id`).
  3. Query audit evidence via admin API by `correlation_id=<X-Request-ID>` and optionally narrow by `action`:
     - `GET /api/v1/audit/events?correlation_id=<X-Request-ID>`
     - `GET /api/v1/audit/events?action=admin.employee_key:revoke&correlation_id=<X-Request-ID>`
  4. For revoke conflicts, validate lifecycle precedence: `revoked` -> `used` -> `expired` -> `active`.
  5. For register failures with revoked keys, confirm `employee_registration_keys.revoked_at` is not null.

## Compliance Baseline (Dev Non-Blocking, Prod Blocking)
This section defines provisional operational controls until final legal/security sign-off.

EPIC-13 release gating and sign-off requirements live in `docs/operations/release-checklist.md`.
The canonical production evidence manifest lives in `docs/project/production-legal-evidence-package.md`.
Assumption: release-specific evidence outputs and legal/security approvals are attached to the release ticket or PR, while the repo keeps the manifest and blocker logic.

### Data Retention Policy (Provisional)

| Data Class | Storage | Retention Window | Disposal Strategy | Owner |
| --- | --- | --- | --- | --- |
| Auth denylist keys (`jti`, `sid`) | Redis | TTL-bound to token/session validity window | Auto-expire via Redis TTL | backend |
| Audit events (`audit_events`) | PostgreSQL | 365 days hot storage | Archive then purge by approved retention job | backend + devops |
| Application logs | Container/log backend | 90 days | Rotation + purge | devops |
| Candidate CV/documents | Object storage | 24 months after workflow closure (provisional) | Delete object + metadata tombstone | hr-ops + backend |

- TODO(owner: business-analyst + legal, due_trigger: before first production release): approve final retention windows for each PD category.

### Encryption Policy (Provisional)
- In transit:
  - All production HTTP endpoints must be exposed only via TLS 1.2+.
  - Service-to-service integrations (Google Calendar, object storage access, admin consoles) must use TLS-enabled endpoints.
- At rest:
  - PostgreSQL data volume must use encrypted storage class.
  - Object storage buckets with personal data must use server-side encryption.
  - Backups/snapshots must be encrypted and access-restricted.

- TODO(owner: devops + security, due_trigger: before first production release): attach concrete infrastructure evidence (KMS/SSE/TLS termination config) to the EPIC-13 release checklist and close the `CTRL-RU-04` gap with a real artifact.

### Access Policy and Review Cadence (Provisional)
- Least-privilege access is mandatory for platform, database, object storage, and CI/CD.
- No shared human accounts for production administration.
- Privileged role grants require ticket-based justification and explicit expiration date.
- Access review cadence:
  - monthly review for privileged/admin roles;
  - quarterly review for all operational/service accounts.
- Access revocation SLA: same business day for role removal or offboarding events.

- TODO(owner: architect + security, due_trigger: before first production release): finalize break-glass procedure and reviewer roster.

### Release Gate Policy
- Dev and test deployments are allowed with provisional controls, but they do not waive EPIC-13 release gating.
- `docs/operations/release-checklist.md` is the canonical pre-prod and production gate.
- `docs/project/production-legal-evidence-package.md` is the canonical package manifest for repo-backed evidence, external attachments, freshness rules, and sign-off sequencing.
- Pre-prod promotion is blocked if any critical control in `docs/project/legal-controls-matrix.md` remains `planned` or `in-progress`.
- Production release is blocked unless every critical control is `verified` and legal/security sign-off records the refreshed evidence IDs.
- The current hard blockers are the gap rows for `CTRL-RU-04` and `CTRL-RU-06`; release cannot proceed until those artifacts exist as real evidence, not placeholders.

### Production Sign-Off Handling
1. Freeze the release candidate commit/tag before collecting approval evidence.
2. Refresh the repo-backed evidence rows required by the critical controls in scope and attach the outputs outside the repo.
3. Attach the non-repo approvals and gap-closure artifacts required by `docs/project/production-legal-evidence-package.md`.
4. Treat any stale attachment, changed release candidate, or unresolved gap row as a release blocker.

## Incident Triage
1. Confirm impact and affected user segment.
2. Capture failing signal (logs/metrics/error id).
3. Apply mitigations with lowest blast radius first.
4. Record timeline and root cause candidate.

## Escalation Matrix
| Severity | Condition | Notify | Target Response |
| --- | --- | --- | --- |
| Sev-1 | Full outage or data corruption risk | coordinator + architect | 15 min |
| Sev-2 | Major degradation | coordinator | 30 min |
| Sev-3 | Minor issue | owner role | 1 business day |

## Postmortem Minimum
- Impact summary
- Root cause
- Corrective actions
- Preventive actions

## Container Incident Commands
- Recent logs by service: `docker compose logs --tail 200 <service>`
- Follow logs: `docker compose logs -f <service>`
- Restart one service: `docker compose restart <service>`
- Rebuild after dependency/image changes: `docker compose up -d --build`
- Force-recreate all services: `make rebuild` or `just rebuild`
- Remove orphan containers: `make clean-orphans` or `just clean-orphans`
- Run full smoke suite after mitigation: `./scripts/smoke-compose.sh`
