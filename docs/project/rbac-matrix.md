# RBAC Role Matrix (Phase 1 Baseline)

## Last Updated
- Date: 2026-03-16
- Updated by: backend-engineer

This matrix is the access baseline for `TASK-01-01`, `TASK-01-02`, `TASK-01-03`,
`TASK-03-01`, `TASK-03-02`, `TASK-03-03`, `TASK-02-01`, `TASK-02-02`, `TASK-06-03`,
`TASK-07-01`, `TASK-07-02`, `TASK-07-03`, `TASK-07-04`, and `TASK-10-01`.
It also covers the admin-only audit evidence read surface introduced in `TASK-10-03`.
Enforcement source of truth:
- `apps/backend/src/hrm_backend/rbac.py`
- `apps/backend/src/hrm_backend/auth/`
- `apps/backend/src/hrm_backend/audit/`

## Roles
- `admin`
- `hr`
- `manager`
- `employee`
- `leader`
- `accountant`

## Permission Matrix

| Permission | admin | hr | manager | employee | leader | accountant |
| --- | --- | --- | --- | --- | --- | --- |
| `admin:staff:create` | yes | no | no | no | no | no |
| `admin:staff:list` | yes | no | no | no | no | no |
| `admin:staff:update` | yes | no | no | no | no | no |
| `admin:employee_key:create` | yes | yes | no | no | no | no |
| `admin:employee_key:list` | yes | yes | no | no | no | no |
| `admin:employee_key:revoke` | yes | yes | no | no | no | no |
| `vacancy:read` | yes | yes | no | no | yes | no |
| `vacancy:create` | yes | yes | no | no | no | no |
| `vacancy:update` | yes | yes | no | no | no | no |
| `pipeline:read` | yes | yes | no | no | yes | no |
| `pipeline:update` | yes | yes | no | no | no | no |
| `pipeline:transition` | yes | yes | no | no | no | no |
| `match_score:create` | yes | yes | no | no | no | no |
| `match_score:read` | yes | yes | no | no | no | no |
| `candidate_profile:create` | yes | yes | no | no | no | no |
| `candidate_profile:read` | yes | yes | no | no | no | no |
| `candidate_profile:update` | yes | yes | no | no | no | no |
| `candidate_profile:list` | yes | yes | no | no | no | no |
| `employee_profile:create` | yes | yes | no | no | no | no |
| `employee_profile:read` | yes | yes | no | no | no | no |
| `onboarding_dashboard:read` | yes | yes | yes | no | no | no |
| `onboarding_task:list` | yes | yes | no | no | no | no |
| `onboarding_task:update` | yes | yes | no | no | no | no |
| `onboarding_task:backfill` | yes | yes | no | no | no | no |
| `onboarding_template:create` | yes | yes | no | no | no | no |
| `onboarding_template:list` | yes | yes | no | no | no | no |
| `onboarding_template:read` | yes | yes | no | no | no | no |
| `onboarding_template:update` | yes | yes | no | no | no | no |
| `employee_portal:read` | no | no | no | yes | no | no |
| `employee_portal:update` | no | no | no | yes | no | no |
| `candidate_cv:upload` | yes | yes | no | no | no | no |
| `candidate_cv:read` | yes | yes | no | no | no | no |
| `candidate_cv:parsing_status` | yes | yes | no | no | no | no |
| `candidate_cv:parse` | yes | yes | no | no | no | no |
| `candidate_profile:read_all` | yes | yes | no | no | no | no |
| `interview:manage` | yes | yes | no | no | no | no |
| `manager_workspace:read` | no | no | yes | no | no | no |
| `notification:read` | no | no | yes | no | no | yes |
| `notification:update` | no | no | yes | no | no | yes |
| `analytics:read` | yes | yes | yes | yes | yes | yes |
| `audit:read` | yes | no | no | no | no | no |
| `accounting:read` | yes | no | no | no | no | yes |
| `kpi_snapshot:read` | yes | no | no | no | yes | no |
| `kpi_snapshot:rebuild` | yes | no | no | no | no | no |

Public endpoint outside RBAC matrix:
- `POST /api/v1/vacancies/{vacancy_id}/applications` is anonymous (`actor_sub=null` in audit context).

## Enforcement Rules
- Role is resolved from validated access token claim (`role`).
- Missing/invalid bearer token: `401 Unauthorized`.
- Unknown role claim: `403 Forbidden`.
- Permission mismatch: `403 Forbidden`.
- API permission checks are enforced through:
  - `require_permission(permission)` (FastAPI dependency wrapper)
  - centralized evaluator `evaluate_permission(role, permission)`
  - immutable audit write on every decision (`allowed` and `denied`)
- Ownership checks for candidate profile/CV resources are enforced at domain-service level.
  For current policy, `admin/hr` are allowed and non-privileged staff roles receive explicit
  `denied` audit events when attempting staff-only candidate endpoints.
- Manager workspace hiring read routes are limited to the `manager` role through the dedicated
  permission `manager_workspace:read`:
  - `GET /api/v1/vacancies/manager-workspace`
  - `GET /api/v1/vacancies/{vacancy_id}/manager-workspace/candidates`
  Visibility is fail-closed on `vacancies.hiring_manager_staff_id=<current manager subject>`, and
  the candidate snapshot payload is PII-redacted (stage + interview schedule + offer status only).
- Employee profile bootstrap/read routes are staff-only and currently limited to `admin/hr`.
  Employee self-access is intentionally deferred until later employee/onboarding slices.
- Onboarding dashboard read routes are limited to `admin`, `hr`, and `manager`:
  - `GET /api/v1/onboarding/runs`
  - `GET /api/v1/onboarding/runs/{onboarding_id}`
  Manager access is read-only and additionally scoped at the service layer to runs where at least one
  task has `assigned_role=manager` or `assigned_staff_id=<current subject>`.
- Onboarding task list/update/backfill routes are staff-only and currently limited to `admin/hr`.
  Manager users can observe onboarding progress only through the dedicated read routes above.
- Onboarding checklist template management routes are staff-only and currently limited to `admin/hr`.
  Manager-facing template management remains out of scope.
- KPI snapshot read routes are leader/admin in v1, while rebuild remains admin-only:
  - `GET /api/v1/reporting/kpi-snapshots`
  - `GET /api/v1/reporting/kpi-snapshots/export`
  - `POST /api/v1/reporting/kpi-snapshots/rebuild` (admin-only)
- Audit event query API is admin-only in v1:
  - `GET /api/v1/audit/events`
  - `GET /api/v1/audit/events/export`
- Employee self-service onboarding routes are limited to the `employee` role:
  - `GET /api/v1/employees/me/onboarding`
  - `PATCH /api/v1/employees/me/onboarding/tasks/{task_id}`
  Admin/HR continue to use the staff onboarding task routes for assignment, backfill, and SLA updates.
- Background permission checks are enforced through:
  - `enforce_background_permission(...)`
  - the same centralized evaluator `evaluate_permission(...)`
  - immutable audit write with `source=job` on every decision

## API and Background Enforcement Path

| Path | Entry Point | Decision Engine | Deny/Error Contract |
| --- | --- | --- | --- |
| API route | `require_permission(...)` | `evaluate_permission(...)` | `HTTP 401/403` |
| Background job | `enforce_background_permission(...)` | `evaluate_permission(...)` | `BackgroundAccessDeniedError` |

## Audit Linkage
- Every RBAC decision writes one `audit_events` record.
- `action` equals permission key (for example `vacancy:create`).
- `result` is `allowed` or `denied`.
- `correlation_id` is populated from `X-Request-ID` (API) or job correlation ID (background).

## Next Steps
- Add manager/leader vacancy update permissions when phase-2 workflows are enabled.
