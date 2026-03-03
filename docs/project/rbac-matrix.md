# RBAC Role Matrix (Phase 1 Baseline)

## Last Updated
- Date: 2026-03-04
- Updated by: architect

This matrix is the initial access baseline for `TASK-01-01`.
API enforcement source of truth: `apps/backend/src/hrm_backend/rbac.py`.

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
- Role is read from request header `X-Role`.
- Missing role header: `401 Unauthorized`.
- Unknown role: `403 Forbidden`.
- Permission mismatch: `403 Forbidden`.

## Next Steps
- Replace header-based role resolution with authenticated identity claims in `TASK-01-02`.
- Expand permission set per domain modules as APIs are implemented.
