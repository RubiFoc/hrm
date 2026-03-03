# RBAC Role Matrix (Phase 1 Baseline)

## Last Updated
- Date: 2026-03-04
- Updated by: backend-engineer

This matrix is the access baseline for `TASK-01-01` and `TASK-01-02`.
API enforcement source of truth:
- `apps/backend/src/hrm_backend/rbac.py`
- `apps/backend/src/hrm_backend/auth.py`

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

## Next Steps
- Enforce access policy centrally for API and background jobs in `TASK-01-03`.
- Expand permission set per domain modules as APIs are implemented.
