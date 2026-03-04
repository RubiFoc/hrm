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

## Test Package Layout (Backend)
- Keep test tree aligned with application package boundaries and split by level.
- Required structure:

```text
apps/backend/tests/
  unit/
    auth/
    core/
    rbac/
    ...
  integration/
    auth/
    core/
    rbac/
    ...
```

## Change-Based Verification Matrix
| Change Type | Required Checks |
| --- | --- |
| Bugfix | Unit regression + integration regression + adjacent behavior check |
| New feature | Unit happy/negative + integration contract path |
| Refactor | Unit non-regression + integration non-regression |

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

## Baseline Verification Commands
- `./scripts/check-docs-structure.sh`
- `uv run --project apps/backend ruff check apps/backend/src apps/backend/tests apps/backend/alembic`
- `uv run --project apps/backend pytest -q`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic upgrade head`
- `DATABASE_URL=sqlite+pysqlite:///tmp/hrm_alembic_security.db uv run --project apps/backend alembic downgrade -1`
