# RBAC Role Matrix (Phase 1 Baseline)

## Last Updated
- Date: 2026-03-05
- Updated by: backend-engineer

This matrix is the access baseline for `TASK-01-01`, `TASK-01-02`, `TASK-01-03`,
`TASK-03-01`, `TASK-03-02`, `TASK-03-03`, `TASK-02-01`, and `TASK-02-02`.
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
| `vacancy:read` | yes | yes | yes | no | yes | no |
| `vacancy:create` | yes | yes | no | no | no | no |
| `vacancy:update` | yes | yes | no | no | no | no |
| `pipeline:read` | yes | yes | yes | no | yes | no |
| `pipeline:update` | yes | yes | no | no | no | no |
| `pipeline:transition` | yes | yes | no | no | no | no |
| `candidate_profile:create` | yes | yes | no | no | no | no |
| `candidate_profile:read` | yes | yes | no | no | no | no |
| `candidate_profile:update` | yes | yes | no | no | no | no |
| `candidate_profile:list` | yes | yes | no | no | no | no |
| `candidate_cv:upload` | yes | yes | no | no | no | no |
| `candidate_cv:read` | yes | yes | no | no | no | no |
| `candidate_cv:parsing_status` | yes | yes | no | no | no | no |
| `candidate_cv:parse` | yes | yes | no | no | no | no |
| `candidate_profile:read_all` | yes | yes | no | no | no | no |
| `interview:manage` | yes | yes | yes | no | no | no |
| `analytics:read` | yes | yes | yes | yes | yes | yes |
| `accounting:read` | yes | no | no | no | no | yes |

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
