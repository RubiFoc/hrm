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
