# Testing Strategy

## Goals
- Prevent regressions in critical business flows.
- Keep verification reproducible for humans and LLM agents.
- Ensure all backend logic is covered at unit and integration/e2e levels.

## Mandatory Coverage Policy
- Every logic module must have:
  - unit tests for isolated behavior and edge cases;
  - integration/e2e tests for boundary behavior (HTTP/API, storage adapters, external integration seams).
- Changes are not done until required tests are added or updated.

## Test Levels
| Level | Purpose | Minimum Requirement |
| --- | --- | --- |
| Unit | Validate isolated logic | Mandatory for all changed logic |
| Integration/E2E | Validate boundaries and user/system paths | Mandatory for all changed logic and interfaces |
| Infrastructure Smoke | Validate Docker Compose runtime readiness | Mandatory for container/runtime baseline changes (`TASK-12-01`) |

## Test Package Layout (Backend)
- Keep test tree aligned with application package boundaries and split by level.
- Required structure:

```text
apps/backend/tests/
  unit/
    admin/
    auth/
    core/
    rbac/
    ...
  integration/
    admin/
    auth/
    core/
    rbac/
    ...
```

## Integration Harness Stability Rules
- Canonical HTTP integration harness: `pytest-anyio` + `httpx.AsyncClient` + `ASGITransport`.
- Do not use `starlette.testclient.TestClient` in backend integration tests.
- Keep integration runtime pinned to `anyio_backend = "asyncio"` in `apps/backend/tests/integration/conftest.py`.
- Keep `inline_threadpool_patch` integration-only; it exists to avoid environment-specific deadlocks in `anyio.to_thread` during in-process ASGI runs.
- Integration tests should override external adapters (Redis/object storage/auth context) through FastAPI dependency overrides to keep runs deterministic.

### Mandatory Pre-PR Smoke Gate (Security/Auth Integration)
- Run before PR-B/PR-C/PR-D style contract-sensitive backend changes:
  - `uv run --project apps/backend pytest -q apps/backend/tests/integration/security/test_audit_enforcement.py apps/backend/tests/integration/auth/test_auth_stack.py`
- The gate must pass in two consecutive runs when harness-level changes are introduced.

## OpenAPI Freeze Discipline
- Frozen backend contract source of truth: `docs/api/openapi.frozen.json`.
- Regeneration command:
  - `./scripts/generate-openapi-frozen.sh`
- Verification command:
  - `./scripts/check-openapi-freeze.sh`
- CI must fail when runtime OpenAPI differs from frozen spec.
- Frontend typed contract generation must run from frozen spec:
  - `npm --prefix apps/frontend run api:types:generate`

## Change-Based Verification Matrix
| Change Type | Required Checks |
| --- | --- |
| Bugfix | Unit regression + integration regression + adjacent behavior check |
| New feature | Unit happy/negative + integration contract path |
| Refactor | Unit non-regression + integration non-regression |
| Runtime/Platform | Compose config validation + deterministic smoke cycle (`up -> smoke`, `down -> up -> smoke`) |

## Phase 1 Baseline Merge Gate
- Use this exact acceptance set before merging the current local baseline slice:
  - `./scripts/check-docs-structure.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/candidates/test_cv_parsing_jobs.py apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest apps/backend/tests/unit/test_cors.py apps/backend/tests/unit/auth/test_auth_settings.py -q`
  - `docker compose up -d --build`
  - `./scripts/smoke-compose.sh`
- This gate applies to the cohesive baseline PR only; do not add more feature scope before it lands.

## Infrastructure Smoke Baseline (`TASK-12-01`)
- Canonical command: `./scripts/smoke-compose.sh`.
- The smoke script must verify:
  - compose service status and health for `backend`, `postgres`, `redis`, `minio`;
  - compose runtime state for `frontend` and `backend-worker`;
  - compose bootstrap prerequisites (`postgres-init`, `backend-migrate`, `minio-init`) complete successfully before API checks;
  - backend `GET /health`;
  - frontend HTTP response;
  - MinIO live health endpoint;
  - backend auth login response contract.
  - headless Chrome browser auth path `/login -> login -> me -> logout -> /login`;
  - browser auth requests use `VITE_API_BASE_URL` backend origin rather than relative frontend origin;
  - browser-triggered CORS preflight succeeds for auth endpoints.
  - staff API creates one deterministic open vacancy fixture for the public browser scenario;
  - headless Chrome public candidate path `/candidate?vacancyId=...&vacancyTitle=... -> POST /api/v1/vacancies/{vacancy_id}/applications -> GET /api/v1/public/cv-parsing-jobs/{job_id} -> optional GET /analysis`;
  - browser public candidate requests use `VITE_API_BASE_URL` backend origin rather than relative frontend origin;
  - smoke passes when the public tracking status reaches at least `queued`/`running`; `analysis_ready=true` is preferred but not mandatory for compose success.

## Evidence Format
- Command
- Result (pass/fail)
- Artifact link/path (if available)

## Security Foundation Verification (TASK-01-03, TASK-01-04)

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Centralized policy evaluator | `tests/unit/rbac/test_rbac.py` (`evaluate_permission`, background deny path) | API allow/deny in `tests/integration/security/test_audit_enforcement.py` | `uv run --project apps/backend pytest -q` |
| API and background enforcement parity | `tests/unit/rbac/test_rbac.py` | `test_api_permission_decisions_are_audited`, `test_background_enforcement_writes_job_audit_event` | Audit records with `source=api` and `source=job` |
| Immutable audit storage writes | Audit service and payload validation via unit imports | `tests/integration/security/test_audit_enforcement.py` | Alembic migration + inserted `audit_events` rows |
| Auth sensitive audit hooks | N/A | `test_auth_login_is_audited` (+ auth regression suite) | `auth.login` audit event with `correlation_id` |

## Staff Auth Extension Verification

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Password policy and hashing (`argon2`) | `tests/unit/auth/*` | `tests/integration/auth/test_auth_stack.py` | `register/login` happy and negative scenarios |
| Employee key lifecycle (`valid/expired/used/revoked`) | `tests/unit/auth/*` | `tests/integration/auth/test_auth_stack.py` | `422` on invalid key paths |
| UUID claims and token contract | `tests/unit/auth/test_auth_services.py` | auth integration suite | `sub/sid/jti` are UUID-backed |
| Login contract (`identifier + password` only) | `tests/unit/auth/test_auth_services.py` | `tests/integration/security/test_audit_enforcement.py` (`test_auth_login_is_audited`) | Login accepts canonical identifier/password payload |
| Swagger bearer security scheme | N/A | OpenAPI contract check in auth integration suite | Swagger UI contains `Authorize` flow |
| Admin APIs and audit hooks | `tests/unit/rbac/test_rbac.py` | `tests/integration/security/test_audit_enforcement.py` | `admin.staff:create` and `admin.employee_key:create` success/failure events |

## Recruitment Domain Verification (TASK-03-01, TASK-03-02, TASK-02-01, TASK-02-02, TASK-03-03)

| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Candidate profile schema and ownership guards | `tests/unit/candidates/test_cv_validation.py` + role checks in `tests/unit/rbac/test_rbac.py` | `tests/integration/candidates/test_candidate_api.py` | `uv run --project apps/backend pytest -q` |
| UUID boundary validation for candidate/vacancy/pipeline contracts | Candidate/vacancy schema parsing via unit-level model validation | `tests/integration/candidates/test_candidate_api.py` + `tests/integration/vacancies/test_vacancy_pipeline_api.py` (invalid UUID -> `422`) | OpenAPI IDs expose `format: uuid` and boundary negatives are covered |
| CV upload validation (mime/size/checksum) | `tests/unit/candidates/test_cv_validation.py` | `test_cv_upload_download_status_and_validation_failures` | Validation negative paths return `415/422/413` |
| Public vacancy apply flow (anonymous) | `tests/unit/vacancies/test_pipeline_validator.py` + candidate validation units | `tests/integration/vacancies/test_vacancy_pipeline_api.py` | Apply creates candidate/doc/transition/parsing job and returns `parsing_job_id` for browser tracking |
| Vacancy lifecycle and canonical pipeline transitions | `tests/unit/vacancies/test_pipeline_validator.py` | `tests/integration/vacancies/test_vacancy_pipeline_api.py` | Valid chain passes, invalid chain returns `422`, and ordered history read returns append-only timeline |
| Async CV parsing lifecycle and retry-safe behavior (Celery executor) | `tests/unit/candidates/test_cv_parsing_worker.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` | `queued/running/succeeded/failed` with bounded retries and public tracking-by-job-id contract |
| RU/EN CV normalization and language detection (`TASK-03-05`) | `tests/unit/candidates/test_cv_parsing_normalization.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` | `detected_language` and canonical profile fields are persisted after worker success |
| Evidence traceability + analysis read contract (`TASK-03-06`) | `tests/unit/candidates/test_cv_parsing_normalization.py` (field-level evidence snippets/offsets) | `tests/integration/candidates/test_candidate_api.py` + `tests/integration/candidates/test_cv_parsing_jobs.py` | `GET /api/v1/candidates/{candidate_id}/cv/analysis` and `GET /api/v1/public/cv-parsing-jobs/{job_id}/analysis` return structured profile + evidence; pre-ready path returns `409` |
| RBAC + audit coverage for recruitment endpoints | `tests/unit/rbac/test_rbac.py` | `tests/integration/security/test_audit_enforcement.py` + recruitment integration suites | `allowed/denied/success/failure` audit records in `audit_events` |

## Frontend Login UX Verification (TASK-11-13)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Typed API client honors `VITE_API_BASE_URL` and trims trailing slash | `apps/frontend/src/api/typedClient.test.ts` | N/A | browser auth requests target backend origin instead of relative frontend origin |
| Session storage contract (`access/refresh/role`) and admin-guard compatibility | `apps/frontend/src/app/auth/session.test.ts` | N/A | write/read/clear behavior and invalid role handling |
| Auth API client request shape and `ApiError` mapping | `apps/frontend/src/api/auth.test.ts` | N/A | login/me/logout request contract and `401/422/http_*` handling |
| Login page submit flow (`login -> me -> redirect`) | `apps/frontend/src/pages/LoginPage.test.tsx` | `./scripts/smoke-compose.sh` | session is persisted and redirect follows resolved role |
| Login error states (`401`, `422`, generic) with RU/EN-readable messaging | `apps/frontend/src/pages/LoginPage.test.tsx` | Manual smoke on `/login` with locale toggle | localized error messaging for all required states |
| Router behavior for `/login` and pre-authenticated bootstrap redirect | `apps/frontend/src/app/router.auth.test.tsx` | `./scripts/smoke-compose.sh` | login route render, authenticated redirect, broken session cleanup |
| Admin guard non-regression | `apps/frontend/src/app/router.admin.test.tsx` | `./scripts/smoke-compose.sh` | unauthorized/forbidden redirects continue to work unchanged |
| Browser login/logout roundtrip against compose stack | N/A | `scripts/browser_auth_smoke.py` via `./scripts/smoke-compose.sh` and CI `browser-smoke` job | browser reaches `/admin`, persists session, calls backend auth origin, logs out, and returns to `/login` |
| Backend CORS preflight allows local Vite dev origin | `apps/backend/tests/unit/test_cors.py` + `apps/backend/tests/unit/auth/test_auth_settings.py` | `./scripts/smoke-compose.sh` | `OPTIONS /api/v1/auth/login` returns `200` with expected `Access-Control-Allow-*` headers |

## Frontend Candidate Workspace Verification (`TASK-11-06`, `TASK-11-09`, `TASK-11-11`)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Deep-link candidate route contract (`/candidate?vacancyId=...&vacancyTitle=...`) and diagnostic fallback | `apps/frontend/src/pages/CandidatePage.test.tsx` | `./scripts/smoke-compose.sh` | candidate page accepts deep link, falls back to manual vacancy ID only when query param is absent |
| Browser SHA-256 checksum + multipart public apply submission | `apps/frontend/src/pages/CandidatePage.test.tsx` + `apps/frontend/src/api/typedClient.test.ts` | `./scripts/smoke-compose.sh` | browser submit hits `POST /api/v1/vacancies/{vacancy_id}/applications` and persists returned tracking context |
| Session storage tracking contract (`hrm_candidate_application_context`) | `apps/frontend/src/pages/CandidatePage.test.tsx` | `./scripts/smoke-compose.sh` | stored payload contains `vacancyId`, `candidateId`, and `parsingJobId` |
| Public tracking and analysis polling by `parsing_job_id` | `apps/frontend/src/pages/CandidatePage.test.tsx` | `./scripts/smoke-compose.sh` | browser reaches at least `queued/running`; analysis/evidence render when ready |
| Localized candidate apply/tracking errors (`409`, `429`, `422`, generic) | `apps/frontend/src/pages/CandidatePage.test.tsx` | manual smoke or compose browser smoke with fixture variations | localized RU/EN mapping for duplicate/cooldown/validation/network failures |
| Browser origin correctness for public candidate requests | N/A | `scripts/browser_candidate_apply_smoke.py` via `./scripts/smoke-compose.sh` and CI `browser-smoke` job | apply/tracking requests target backend origin instead of relative frontend origin |

## Frontend HR Workspace Verification (`TASK-11-05`, `TASK-11-09`)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Vacancy list/create/edit UI on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | `./scripts/smoke-compose.sh` creates vacancy through staff API for downstream browser use | staff user can create and update vacancy through typed API wrappers |
| Candidate selection and pipeline transition append | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration: `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | valid transition appends and invalid transition returns localized `422` |
| Ordered transition history/timeline render | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration: `apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py` | timeline reflects append-only transition history for selected vacancy + candidate |
| Localized HR workspace errors (`403`, `404`, `422`, generic) | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | manual role smoke with expired/forbidden session variants | recruiter-facing failures remain readable in RU/EN |

## Scoring and Shortlist Review Verification (`TASK-04-01/02/03`, `TASK-11-07`)

### Backend
| Capability | Unit Coverage | Integration Coverage | Required Evidence |
| --- | --- | --- | --- |
| Ollama adapter mapping and score schema validation | `apps/backend/tests/unit/scoring/test_ollama_adapter.py` | N/A | model response mapping is deterministic and score payload validates against schema |
| Worker/job state transitions and retry behavior | `apps/backend/tests/unit/scoring/test_match_scoring_worker.py` | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | `queued/running/succeeded/failed` lifecycle is persisted correctly |
| Reject scoring when parsed CV analysis is not ready | N/A | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | `POST /api/v1/vacancies/{vacancy_id}/match-scores` returns `409` without silent fallback |
| Score payload shape and evidence propagation | `apps/backend/tests/unit/scoring/test_ollama_adapter.py` | `apps/backend/tests/integration/scoring/test_match_scoring_api.py` | latest score response includes `score`, `confidence`, `summary`, requirements, evidence, model metadata, and `scored_at` |

### Frontend
| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Run score -> polling -> success render | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | shortlist review block renders state transitions and final score card |
| Failed scoring job render | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | failed state is visible and recoverable in UI |
| Localized `409` when CV analysis is not ready | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | RU/EN-readable not-ready error is rendered |
| Confidence/explanation rendering | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend integration above | confidence, summary, matched requirements, missing requirements, and evidence sections are rendered |

### Acceptance Rules
- Freeze OpenAPI and update generated frontend types in the same change.
- Keep the current compose smoke green.
- Do not regress auth or CORS behavior.
- Keep scoring verification at unit/integration level; do not extend compose browser smoke to scoring until runtime nondeterminism is addressed.
- Shortlist review must work against the real backend scoring contract, not mock-only placeholder data.

## Interview Scheduling and Candidate Registration Verification (`TASK-11-08`, `TASK-05-01`, `TASK-05-02`)

Implementation source of truth:
- `docs/project/interview-planning-pass.md`

Current implementation coverage must stay green at minimum:

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Interview lifecycle validation (`pending_sync`, `awaiting_candidate_confirmation`, `confirmed`, `reschedule_requested`, `cancelled`) | `apps/backend/tests/unit/interviews/test_lifecycle.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | invalid transitions return `409`; terminal interviews cannot be mutated |
| Calendar sync lifecycle (`queued`, `running`, `synced`, `conflict`, `failed`) | `apps/backend/tests/unit/interviews/test_google_calendar_adapter.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | sync result persists correct interview and calendar statuses |
| One-active-interview rule per `vacancy_id + candidate_id` | `apps/backend/tests/unit/interviews/test_lifecycle.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | duplicate active interview returns `409` |
| Candidate invitation token hashing, expiry, and schedule-version invalidation | `apps/backend/tests/unit/interviews/test_token_manager.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | revoked/rescheduled tokens return `404`; expired token returns `410` |
| Candidate public actions (`confirm`, `request-reschedule`, `cancel`) | `apps/backend/tests/unit/interviews/test_lifecycle.py` + `apps/backend/tests/unit/interviews/test_token_manager.py` | `apps/backend/tests/integration/interviews/test_interview_api.py` | token-bound actions update state without candidate auth |
| HR route integration on `/` | `apps/frontend/src/pages/HrDashboardPage.test.tsx` | backend interview integration suite | create/reschedule/cancel and sync-state render are localized and stable |
| Candidate route-mode integration on `/candidate?interviewToken=...` | `apps/frontend/src/pages/CandidatePage.test.tsx` | backend interview integration suite | candidate interview mode renders localized `404/409/410/422` errors and rejects mixed route params |

Operational assumptions for the current interview slice:
- Freeze OpenAPI and generated frontend types in the same change.
- Keep candidate transport anonymous and token-based.
- Do not add candidate auth, Vite proxy rewrites, or new CORS behavior.
- Free Google Calendar mode uses a service-account JSON key and calendars manually shared with that service account; missing calendar mapping returns `422 interviewer_calendar_not_configured`, while missing runtime calendar configuration returns `503 calendar_not_configured`.
- Keep compose smoke green without adding nondeterministic Google Calendar browser automation.

## Frontend Admin Verification (ADMIN-01)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Admin guard decision logic | `apps/frontend/src/app/auth/session.test.ts` | N/A | `npm --prefix apps/frontend run test -- --run` |
| Unauthorized/forbidden redirect flow | `apps/frontend/src/app/router.admin.test.tsx` | `/admin` route smoke in browser/CI preview | Redirects to `/access-denied` with reason query |
| RU/EN admin shell rendering | `apps/frontend/src/app/router.admin.test.tsx` + i18n keys | UI smoke for `/admin` after language toggle | Admin shell strings are present in both locales |
| Admin observability tags | N/A | Manual/automated capture in Sentry QA project | `workspace`, `role`, `route` tags set on admin route access |

## Admin Staff Management Verification (ADMIN-02)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Staff DAO pagination/search/filter/count | `apps/backend/tests/unit/admin/test_staff_account_dao.py` | Covered indirectly by admin list integration API tests | `uv run --project apps/backend pytest -q` |
| Staff update strict guard validation | `apps/backend/tests/unit/admin/test_admin_staff_service.py` (`empty_patch`, `unsupported_role`, self/last-admin protection) | `apps/backend/tests/integration/admin/test_admin_staff_management.py` (`409` guard paths) | reason codes `self_modification_forbidden`, `last_admin_protection` |
| Admin list/update API contracts | N/A | `apps/backend/tests/integration/admin/test_admin_staff_management.py` | `GET /api/v1/admin/staff` and `PATCH /api/v1/admin/staff/{staff_id}` |
| RBAC deny path for non-admin access | `tests/unit/rbac/test_rbac.py` | `test_non_admin_gets_403_for_staff_list_and_update` | explicit `403` behavior |
| Admin audit events for list/update | N/A | `test_admin_staff_audit_events_capture_success_and_failure_reason_codes` | `admin.staff:list` and `admin.staff:update` success/failure with reason codes |
| Frontend `/admin/staff` rendering and interactions | `apps/frontend/src/pages/AdminStaffManagementPage.test.tsx` | Route guard tests in `apps/frontend/src/app/router.admin.test.tsx` | filters, PATCH action, localized `404/409/422` error mapping |
| Sentry route tag for admin staff screen | N/A | `apps/frontend/src/app/router.admin.test.tsx` + QA Sentry smoke | `route=/admin/staff` tag emitted by `AdminGuard` |

## Employee Key Lifecycle Verification (ADMIN-03)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Employee-key DAO list/count/revoke | `apps/backend/tests/unit/admin/test_employee_registration_key_dao.py` | Covered by admin employee-key integration API tests | `uv run --project apps/backend pytest -q` |
| Employee-key service guard and status model | `apps/backend/tests/unit/admin/test_admin_employee_key_service.py` | `apps/backend/tests/integration/admin/test_admin_employee_key_management.py` (`404/409` reason-code paths) | reason codes `key_not_found`, `key_already_used`, `key_already_expired`, `key_already_revoked` |
| Admin employee-key API contracts | N/A | `apps/backend/tests/integration/admin/test_admin_employee_key_management.py` | `GET /api/v1/admin/employee-keys`, `POST /api/v1/admin/employee-keys/{key_id}/revoke` |
| RBAC for key lifecycle endpoints | `tests/unit/rbac/test_rbac.py` | `test_non_privileged_roles_get_403_for_employee_key_list_and_revoke` | `admin/hr` allowed, non-privileged roles denied |
| Auth consume path rejects revoked keys | `apps/backend/tests/unit/auth/test_auth_employee_registration_key_dao.py` | Covered by auth stack invalid-key behavior | revoked keys are not consumable |
| Frontend `/admin/employee-keys` rendering and interactions | `apps/frontend/src/pages/AdminEmployeeKeysManagementPage.test.tsx` | route guard tests in `apps/frontend/src/app/router.admin.test.tsx` | list/filter/pagination, create/revoke actions, localized errors |
| Sentry route tag for employee-key screen | N/A | `apps/frontend/src/app/router.admin.test.tsx` + QA Sentry smoke | `route=/admin/employee-keys` tag emitted by `AdminGuard` |

## Frontend Observability Verification (`TASK-11-10`)

| Capability | Unit Coverage | Integration/Smoke Coverage | Required Evidence |
| --- | --- | --- | --- |
| Canonical Sentry tags on critical routes (`/`, `/candidate`, `/login`) | `apps/frontend/src/app/router.observability.test.tsx` | Manual QA against Sentry project or local browser verification | `workspace`, `role`, `route` tags match the documented route/workspace mapping |
| Canonical Sentry tags on admin critical routes (`/admin`, `/admin/staff`, `/admin/employee-keys`) | `apps/frontend/src/app/router.admin.test.tsx` | Manual QA against Sentry project or admin route smoke | admin routes emit `workspace=admin` plus the canonical route tag |
| Shared HTTP failure capture with request metadata | `apps/frontend/src/api/httpClient.test.ts` | Manual failure injection against local backend or Sentry QA project | Sentry event includes current route tags plus `http_method`, `http_status`, and request path metadata |
| Localized render-failure fallback boundary | `apps/frontend/src/app/observability/AppErrorBoundary.test.tsx` | Manual browser smoke with a forced render exception in QA build | crashing route renders RU/EN fallback UI and the exception is captured in Sentry |
| Frontend non-regression after observability hardening | `npm --prefix apps/frontend run test -- --run` | existing compose smoke remains unchanged | no route, auth, CORS, or typed-client regression |

## Baseline Verification Commands
- `./scripts/check-docs-structure.sh`
- `./scripts/check-openapi-freeze.sh`
- `uv run --project apps/backend ruff check apps/backend/src apps/backend/tests apps/backend/alembic`
- `uv run --project apps/backend pytest -q`
- `uv run --project apps/backend pytest -q apps/backend/tests/unit/candidates/test_cv_parsing_normalization.py apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/candidates/test_cv_parsing_jobs.py apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py`
- `npm --prefix apps/frontend run lint`
- `npm --prefix apps/frontend run test -- --run`
- `uv run --project apps/backend pytest apps/backend/tests/unit/test_cors.py apps/backend/tests/unit/auth/test_auth_settings.py -q`
- `python3 scripts/browser_auth_smoke.py --frontend-url http://localhost:5173/login --api-origin http://localhost:8000 --login <login> --password <password>`
- `python3 scripts/browser_candidate_apply_smoke.py --frontend-url http://localhost:5173/candidate --api-origin http://localhost:8000 --vacancy-id <vacancy_id> --vacancy-title <title>`
- `./scripts/smoke-compose.sh`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic upgrade head`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic downgrade -1`
- `DATABASE_URL=postgresql+psycopg://hrm:hrm@localhost:5432/<test_db> uv run --project apps/backend alembic upgrade head && ... downgrade -1 && ... upgrade head`
- `npm --prefix apps/frontend run lint && npm --prefix apps/frontend run test -- --run`
