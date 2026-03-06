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

## Infrastructure Smoke Baseline (`TASK-12-01`)
- Canonical command: `./scripts/smoke-compose.sh`.
- The smoke script must verify:
  - compose service status and health for `backend`, `postgres`, `redis`, `minio`;
  - compose bootstrap prerequisites (`postgres-init`, `backend-migrate`) complete successfully before API checks;
  - backend `GET /health`;
  - frontend HTTP response;
  - MinIO live health endpoint;
  - backend auth login response contract.

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
| Public vacancy apply flow (anonymous) | `tests/unit/vacancies/test_pipeline_validator.py` + candidate validation units | `tests/integration/vacancies/test_vacancy_pipeline_api.py` | Apply creates candidate/doc/transition/parsing job |
| Vacancy lifecycle and canonical pipeline transitions | `tests/unit/vacancies/test_pipeline_validator.py` | `tests/integration/vacancies/test_vacancy_pipeline_api.py` | Valid chain passes, invalid chain returns `422` |
| Async CV parsing lifecycle and retry-safe behavior (Celery executor) | `tests/unit/candidates/test_cv_parsing_worker.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` | `queued/running/succeeded/failed` with bounded retries |
| RU/EN CV normalization and language detection (`TASK-03-05`) | `tests/unit/candidates/test_cv_parsing_normalization.py` | `tests/integration/candidates/test_cv_parsing_jobs.py` | `detected_language` and canonical profile fields are persisted after worker success |
| Evidence traceability + analysis read contract (`TASK-03-06`) | `tests/unit/candidates/test_cv_parsing_normalization.py` (field-level evidence snippets/offsets) | `tests/integration/candidates/test_candidate_api.py` + `tests/integration/candidates/test_cv_parsing_jobs.py` | `GET /api/v1/candidates/{candidate_id}/cv/analysis` returns structured profile + evidence; pre-ready path returns `409` |
| RBAC + audit coverage for recruitment endpoints | `tests/unit/rbac/test_rbac.py` | `tests/integration/security/test_audit_enforcement.py` + recruitment integration suites | `allowed/denied/success/failure` audit records in `audit_events` |

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

## Baseline Verification Commands
- `./scripts/check-docs-structure.sh`
- `uv run --project apps/backend ruff check apps/backend/src apps/backend/tests apps/backend/alembic`
- `uv run --project apps/backend pytest -q`
- `uv run --project apps/backend pytest -q apps/backend/tests/unit/candidates/test_cv_parsing_normalization.py apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/candidates/test_cv_parsing_jobs.py`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic upgrade head`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic downgrade -1`
- `DATABASE_URL=postgresql+psycopg://hrm:hrm@localhost:5432/<test_db> uv run --project apps/backend alembic upgrade head && ... downgrade -1 && ... upgrade head`
- `npm --prefix apps/frontend run lint && npm --prefix apps/frontend run test -- --run`
