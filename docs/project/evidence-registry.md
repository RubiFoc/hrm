# Evidence Registry

## Last Updated
- Date: 2026-03-13
- Updated by: backend-engineer

## Registry Model
- `Evidence ID`: stable identifier for cross-references from `legal-controls-matrix.md`.
- `Control IDs`: legal controls supported by the artifact.
- `Owner`: who must refresh the evidence when the trigger fires.
- `Artifact`: only real in-repo code/docs/scripts/tests or repeatable commands.
- `Verification Source`: command or procedure that proves the artifact is current.
- `Update Trigger`: concrete change that requires the row to be refreshed.

## Evidence Entries

| Evidence ID | Control IDs | Owner | Artifact | Verification Source | Update Trigger |
| --- | --- | --- | --- | --- | --- |
| EVID-001 | CTRL-BY-03, CTRL-RU-02, CTRL-RU-05 | backend-engineer + architect | `apps/backend/src/hrm_backend/rbac.py`, `apps/backend/src/hrm_backend/audit/`, `apps/backend/alembic/versions/20260304_000002_audit_events.py`, `docs/project/rbac-matrix.md`, `docs/project/auth-session-lifecycle.md` | `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q apps/backend/tests/unit/audit apps/backend/tests/unit/rbac/test_rbac.py apps/backend/tests/integration/security/test_audit_enforcement.py apps/backend/tests/integration/audit/test_audit_event_api.py apps/backend/tests/integration/auth/test_auth_stack.py` | Any RBAC permission, audit payload, auth session, or audit migration change |
| EVID-002 | CTRL-BY-01, CTRL-RU-01 | backend-engineer + frontend-engineer | `docs/api/openapi.frozen.json`, `apps/frontend/src/api/generated/openapi-types.ts` | `./scripts/check-openapi-freeze.sh`, `npm --prefix apps/frontend run api:types:check` | Any public API contract or generated type change |
| EVID-003 | CTRL-BY-01, CTRL-RU-01 | frontend-engineer | `apps/frontend/src/pages/CandidatePage.tsx`, `apps/frontend/src/pages/LoginPage.tsx`, `apps/frontend/src/api/auth.ts` | `npm --prefix apps/frontend run test -- --run src/pages/CandidatePage.test.tsx src/pages/LoginPage.test.tsx src/api/auth.test.ts` | Any field added/removed on login or candidate-apply flows |
| EVID-004 | CTRL-BY-03, CTRL-RU-05 | qa-engineer + devops-engineer | `./scripts/smoke-compose.sh`, `scripts/browser_auth_smoke.py`, `scripts/browser_candidate_apply_smoke.py` | `docker compose up -d --build`, `./scripts/smoke-compose.sh` | Any compose topology, critical browser flow, or CORS/runtime change |
| EVID-005 | CTRL-RU-02 | frontend-engineer | `apps/frontend/src/app/observability/sentry.ts`, `apps/frontend/src/app/observability/AppErrorBoundary.tsx`, `apps/frontend/src/main.tsx` | `npm --prefix apps/frontend run test -- --run src/api/httpClient.test.ts src/app/router.observability.test.tsx src/app/observability/AppErrorBoundary.test.tsx` | Any critical-route list, Sentry env contract, or shared HTTP-capture change |
| EVID-006 | CTRL-BY-03 | devops-engineer + backend-engineer | `.env.example`, `docker-compose.yml`, `docs/operations/runbook.md` | `./scripts/check-docs-structure.sh`, compose config review, `./scripts/smoke-compose.sh` | Any object-storage, encryption, compose env, or runbook change |
| EVID-007 | CTRL-RU-01, CTRL-RU-02 | backend-engineer + frontend-engineer | `apps/backend/tests/integration/candidates/test_candidate_api.py`, `apps/backend/tests/integration/scoring/test_match_scoring_api.py`, `apps/frontend/src/pages/HrDashboardPage.test.tsx` | `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/scoring/test_match_scoring_api.py`, `npm --prefix apps/frontend run test -- --run src/pages/HrDashboardPage.test.tsx` | Any candidate-analysis, scoring contract, shortlist review, or evidence payload change |

## Coverage Gaps (No Current Evidence Artifact)

| Control ID | Missing Artifact | Owner | Due Trigger |
| --- | --- | --- | --- |
| CTRL-BY-02 | Runbook procedure for access/correction/deletion or stop-processing requests | backend + hr-ops | Before any public subject-rights workflow or production readiness review |
| CTRL-RU-03 | Runbook/ticket workflow for data-subject requests under 152-ФЗ | backend + hr-ops | Before any production readiness review |
| CTRL-RU-04 | Infra/data-residency ADR and deployment evidence for RU localization | architect + devops | Before storing production RU citizen data |
| CTRL-RU-06 | ISPDn class checklist and attestation pack | security + business-analyst | Before first production release |

## Usage Rules
- Use this registry together with `docs/project/legal-controls-matrix.md`; do not treat it as a substitute for legal review.
- When a verification command changes, update the matching `Evidence ID` row in the same change.
- When an artifact path is removed or renamed, either replace the evidence with a new real artifact or move the control back to a gap state.
