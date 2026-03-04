# Operations Runbook

## Last Updated
- Date: 2026-03-04
- Updated by: devops-engineer + backend-engineer

## Local Environment (Docker Compose)
### Prerequisites
- Docker Engine 24+ with Docker Compose plugin.
- Available local ports: `5173`, `8000`, `5432`, `6379`, `9000`, `9001`.

### Bootstrap
1. Create runtime env file: `cp .env.example .env`
2. Start stack: `docker compose up -d --build`
3. Verify status: `docker compose ps`
4. Run smoke suite: `./scripts/smoke-compose.sh`

Compose bootstrap notes:
- `postgres-init` ensures `${POSTGRES_DB}` exists even when reusing an old data volume.
- `backend-migrate` runs `alembic upgrade head` before backend starts.
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
   - backend health endpoint returns `{"status":"ok"}`;
   - frontend and MinIO health endpoints respond successfully;
   - auth login endpoint returns token payload (`access_token`, `refresh_token`, `token_type`, `expires_in`, `session_id`).
3. For reproducibility checks, run one teardown/restart cycle:
   - `docker compose down`
   - `docker compose up -d --build`
   - `./scripts/smoke-compose.sh`

### Auth Denylist Failure Policy
- Auth validation is fail-closed when Redis denylist is unavailable.
- Expected behavior during Redis outage: protected auth checks return `503`.

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
