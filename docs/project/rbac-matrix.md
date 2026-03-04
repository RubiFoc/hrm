# RBAC Role Matrix (Phase 1 Baseline)

## Last Updated
- Date: 2026-03-04
- Updated by: backend-engineer

This matrix is the access baseline for `TASK-01-01`, `TASK-01-02`, and `TASK-01-03`.
Enforcement source of truth:
- `apps/backend/src/hrm_backend/rbac.py`
- `apps/backend/src/hrm_backend/auth/`
- `apps/backend/src/hrm_backend/audit/`

## Roles
- `hr`
- `candidate`
- `manager`
- `employee`
- `leader`
- `accountant`

## Permission Matrix

| Permission | hr | candidate | manager | employee | leader | accountant |
| --- | --- | --- | --- | --- | --- | --- |
| `vacancy:read` | yes | no | yes | no | yes | no |
| `vacancy:create` | yes | no | no | no | no | no |
| `pipeline:read` | yes | no | yes | no | yes | no |
| `pipeline:update` | yes | no | no | no | no | no |
| `candidate_profile:read_own` | no | yes | no | yes | no | no |
| `candidate_profile:update_own` | no | yes | no | yes | no | no |
| `candidate_profile:read_all` | yes | no | no | no | no | no |
| `interview:register` | no | yes | no | no | no | no |
| `interview:manage` | yes | no | yes | no | no | no |
| `analytics:read` | yes | no | yes | no | yes | yes |
| `accounting:read` | no | no | no | no | no | yes |

## Enforcement Rules
- Role is resolved from validated access token claim (`role`).
- Missing/invalid bearer token: `401 Unauthorized`.
- Unknown role claim: `403 Forbidden`.
- Permission mismatch: `403 Forbidden`.
- API permission checks are enforced through:
  - `require_permission(permission)` (FastAPI dependency wrapper)
  - centralized evaluator `evaluate_permission(role, permission)`
  - immutable audit write on every decision (`allowed` and `denied`)
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
- Expand permission set per domain modules as APIs are implemented.
