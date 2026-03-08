# Operations Runbook

## Last Updated
- Date: 2026-03-09
- Updated by: devops-engineer + backend-engineer + frontend-engineer

## Local Environment (Docker Compose)
### Prerequisites
- Docker Engine 24+ with Docker Compose plugin.
- Local Google Chrome/Chromium binary for browser smoke checks (`google-chrome`, `google-chrome-stable`, `chromium-browser`, `chromium`, or `CHROME_BIN` override).
- Available local ports: `5173`, `8000`, `5432`, `6379`, `9000`, `9001`.

### Bootstrap
1. Create runtime env file: `cp .env.example .env`
2. Start stack: `docker compose up -d --build`
3. Verify status: `docker compose ps`
4. Run smoke suite: `./scripts/smoke-compose.sh`

Compose bootstrap notes:
- `postgres-init` ensures `${POSTGRES_DB}` exists even when reusing an old data volume.
- `backend-migrate` runs `alembic upgrade head` before backend starts.
- `backend-worker` runs the Celery `cv_parsing` queue consumer against the same compose dependencies as `backend`.
- Backend container starts only after DB bootstrap and migrations complete successfully.

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

Runtime auth/browser integration settings:
- Frontend browser API base URL: `VITE_API_BASE_URL` (compose default: `http://localhost:8000`).
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
  `uv run --project apps/backend celery -A hrm_backend.candidates.infra.celery.app:celery_app worker --loglevel=INFO --queues=cv_parsing`
- Compose service: `backend-worker`.
- Runtime lifecycle in DB (`cv_parsing_jobs` source of truth):
  `queued -> running -> succeeded/failed`.
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

### Smoke Verification
1. Run canonical smoke script: `./scripts/smoke-compose.sh`.
2. Script validation scope:
   - `docker compose ps` contains `running + healthy` for `backend`, `postgres`, `redis`, `minio`;
   - `docker compose ps` contains `running` for `frontend` and `backend-worker`;
   - backend health endpoint returns `{"status":"ok"}`;
   - frontend and MinIO health endpoints respond successfully;
   - auth login endpoint returns token payload (`access_token`, `refresh_token`, `token_type`, `expires_in`, `session_id`).
   - headless Chrome completes `/login -> /api/v1/auth/login -> /api/v1/auth/me -> logout -> /login`;
   - browser auth requests target `http://localhost:8000` rather than relative `/api/...` on the frontend origin;
   - browser CORS preflight succeeds for cross-origin auth requests during login/logout.
   - staff API creates one deterministic `open` vacancy for browser candidate smoke;
   - headless Chrome completes `/candidate?vacancyId=...&vacancyTitle=... -> /api/v1/vacancies/{vacancy_id}/applications -> /api/v1/public/cv-parsing-jobs/{job_id}`;
   - candidate browser requests target `http://localhost:8000` rather than relative `/api/...` on the frontend origin;
   - candidate smoke succeeds when public tracking reaches at least `queued` or `running`; `analysis_ready=true` is preferred but not required.
   - scoring/Ollama verification is intentionally excluded from compose smoke; validate the scoring slice through targeted unit and integration suites to avoid nondeterministic browser smoke failures.
3. For reproducibility checks, run one teardown/restart cycle:
   - `docker compose down`
   - `docker compose up -d --build`
   - `./scripts/smoke-compose.sh`

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
  5. If status never moves past `queued`, inspect `backend-worker` logs; compose smoke still treats `queued/running` as acceptable minimum.

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
  2. Query `audit_events` by `action=vacancy:apply_public` and recent `correlation_id`.
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
  3. Query `audit_events` by `action in ('admin.staff:list','admin.staff:update')` and `correlation_id`.
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
  3. Query `audit_events` by `action in ('admin.employee_key:list','admin.employee_key:revoke')` and `correlation_id`.
  4. For revoke conflicts, validate lifecycle precedence: `revoked` -> `used` -> `expired` -> `active`.
  5. For register failures with revoked keys, confirm `employee_registration_keys.revoked_at` is not null.

## Compliance Baseline (Dev Non-Blocking, Prod Blocking)
This section defines provisional operational controls until final legal/security sign-off.

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

- TODO(owner: devops + security, due_trigger: before first production release): attach concrete infrastructure evidence (KMS/SSE/TLS termination config) to release checklist.

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
- Dev and test deployments are allowed with provisional controls.
- Production release is blocked until critical controls in `docs/project/legal-controls-matrix.md` are at least `implemented`.
- Production release is additionally blocked until legal/security sign-off marks critical controls as `verified`.

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
