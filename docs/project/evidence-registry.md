# Evidence Registry

## Last Updated
- Date: 2026-03-23
- Updated by: coordinator

## Registry Model
- `Evidence ID`: stable identifier for cross-references from `legal-controls-matrix.md`.
- `Control IDs`: legal controls supported by the artifact.
- `Owner`: who must refresh the evidence when the trigger fires.
- `Artifact`: only real in-repo code/docs/scripts/tests or repeatable commands.
- `Verification Source`: command or procedure that proves the artifact is current.
- `Update Trigger`: concrete change that requires the row to be refreshed.
- EPIC-13 release checks must treat any `planned` or `in-progress` critical control as a hard blocker; do not substitute a missing artifact with a placeholder evidence row.
- `docs/project/production-legal-evidence-package.md` is the canonical package manifest that consumes these evidence rows for production sign-off.

## Evidence Entries

| Evidence ID | Control IDs | Owner | Artifact | Verification Source | Update Trigger |
| --- | --- | --- | --- | --- | --- |
| EVID-001 | CTRL-BY-03 | backend-engineer + architect | `apps/backend/src/hrm_backend/rbac.py`, `apps/backend/src/hrm_backend/audit/`, `apps/backend/alembic/versions/20260304_000002_audit_events.py`, `docs/project/rbac-matrix.md`, `docs/project/auth-session-lifecycle.md`, `docs/project/export-package-audit-kpi.md` | `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q apps/backend/tests/unit/audit apps/backend/tests/unit/rbac/test_rbac.py apps/backend/tests/integration/security/test_audit_enforcement.py apps/backend/tests/integration/audit/test_audit_event_api.py apps/backend/tests/integration/auth/test_auth_stack.py` | Any RBAC permission, audit payload, auth session, or audit migration change |
| EVID-002 | CTRL-BY-01 | backend-engineer + frontend-engineer | `docs/api/openapi.frozen.json`, `apps/frontend/src/api/generated/openapi-types.ts` | `./scripts/check-openapi-freeze.sh`, `npm --prefix apps/frontend run api:types:check` | Any public API contract or generated type change (including automation rule CRUD endpoints) |
| EVID-003 | CTRL-BY-01 | frontend-engineer | `apps/frontend/src/pages/CandidatePage.tsx`, `apps/frontend/src/pages/LoginPage.tsx`, `apps/frontend/src/api/auth.ts` | `npm --prefix apps/frontend run test -- --run src/pages/CandidatePage.test.tsx src/pages/LoginPage.test.tsx src/api/auth.test.ts` | Any field added/removed on login or candidate-apply flows |
| EVID-004 | CTRL-BY-03 | qa-engineer + devops-engineer | `./scripts/smoke-compose.sh`, `scripts/browser_auth_smoke.py`, `scripts/browser_candidate_apply_smoke.py` | `docker compose up -d --build`, `./scripts/smoke-compose.sh` | Any compose topology, critical browser flow, or CORS/runtime change |
| EVID-006 | CTRL-BY-03 | devops-engineer + backend-engineer | `.env.example`, `docker-compose.yml`, `docs/operations/runbook.md` | `./scripts/check-docs-structure.sh`, compose config review, `./scripts/smoke-compose.sh` | Any object-storage, encryption, compose env, or runbook change |
| EVID-007 | CTRL-BY-02 | backend + hr-ops | `docs/operations/runbook.md` (Subject Rights Requests section) | `./scripts/check-docs-structure.sh`, runbook review for owner/SLA and log template | Any change to subject-rights workflow, SLA, intake channel, or owner |

## Coverage Gaps (No Current Evidence Artifact)
- None. All critical controls have repo-backed evidence artifacts registered above.

## Production Package Scope (TASK-13-04)
- Canonical package manifest: `docs/project/production-legal-evidence-package.md`.
- Repo-backed critical-control evidence available today:
  - `CTRL-BY-03`: `EVID-001`, `EVID-004`, `EVID-006`
  - `CTRL-BY-01`: `EVID-002`, `EVID-003`
  - `CTRL-BY-02`: `EVID-007`
- Non-repo approvals and missing-gap attachments must stay outside this registry until they exist as real artifacts; do not create synthetic evidence rows for missing artifacts.

## Usage Rules
- Use this registry together with `docs/project/legal-controls-matrix.md`; do not treat it as a substitute for legal review.
- When a verification command changes, update the matching `Evidence ID` row in the same change.
- When an artifact path is removed or renamed, either replace the evidence with a new real artifact or move the control back to a gap state.
- The EPIC-13 release checklist must reference the current blocker rows for the critical controls; blockers are not waivers.
- The production evidence package must reference this registry for repo-backed inputs and `docs/project/production-legal-evidence-package.md` for non-repo attachments, freshness rules, and blocker handling.
