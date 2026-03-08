# Sprint M1 Plan and Task Ownership

## Last Updated
- Date: 2026-03-09
- Updated by: coordinator + architect

## Sprint Goal
Deliver Phase 1 MVP local baseline with working technical foundations, containerized platform bootstrap, admin control plane, public candidate apply/tracking flow, HR vacancy/pipeline workspace, and compliance baseline.
Current sprint acceptance target is stable local end-to-end operation on the current device (production rollout is out of scope for this stage).

## Reconciled Delivery Status (2026-03-09)

| Area | Status | Notes |
| --- | --- | --- |
| `TASK-03-01/02/03/05/06` | implemented/local-baseline | Backend candidate schema, upload, parsing, normalization, evidence traceability, and public tracking-by-job-id endpoints are present in repo |
| `TASK-02-01/02/03` | implemented/local-baseline | Backend vacancy CRUD, pipeline transitions, and ordered history endpoint are present in repo |
| `TASK-11-06` | implemented/local-baseline | `/candidate` now provides deep-link public apply, browser checksum calculation, session storage context, and tracking/analysis polling |
| `TASK-11-05` | implemented/local-baseline | `/` now provides staff vacancy CRUD, editing, candidate selection, transition append, and history timeline UX |
| `TASK-11-09` | implemented/local-baseline | RU/EN critical-flow strings are in place for login/admin/candidate/HR routes |
| `TASK-11-11` | implemented/local-baseline | Compose browser smoke covers both staff login and public candidate apply journeys |
| current baseline PR | next/merge-gate | Land the existing local diff as one cohesive PR with fixed scope and no additional feature creep |
| `TASK-04-01/02/03 + TASK-11-07` | next after merge | One vertical slice: dedicated scoring backend + shortlist review inside the current HR workspace |
| `TASK-11-10` | next after scoring | Finish Sentry baseline without changing route topology or auth/CORS behavior |
| `TASK-13-01/02` | parallel next | Compliance mapping/evidence ownership should progress now that the controls, tests, and smoke evidence exist |
| `TASK-11-08` | deferred/planning-blocked | Requires a dedicated planning pass for interview entity, registration, reschedule/cancel, and sync-conflict rules |

## Scope Normalization
- The original M1 sprint text stopped at FE-9, but the repo now contains a broader local acceptance baseline: `TASK-11-05`, `TASK-11-06`, `TASK-11-09`, and `TASK-11-11` are no longer future-only scope.
- Immediate follow-on work must not reopen auth, CORS, or transport architecture.
- The current local baseline is the merge target; do not expand scope before it lands.
- The next approved implementation track is explainable scoring + shortlist review as one backend+frontend slice.
- Interview scheduling (`TASK-11-08`) is deliberately deferred until after a short planning pass.

## Phase 0 Merge Gate
- The current baseline PR must keep exactly this scope:
  - public candidate apply/tracking by `parsing_job_id`;
  - HR vacancy/pipeline workspace on `/`;
  - browser smoke for staff login + public candidate apply;
  - local compose MinIO dev exception with `OBJECT_STORAGE_SSE_ENABLED=false`;
  - backlog/architecture/testing/runbook synchronization.
- Required pre-merge verification commands:
  - `./scripts/check-docs-structure.sh`
  - `./scripts/check-openapi-freeze.sh`
  - `npm --prefix apps/frontend run api:types:check`
  - `npm --prefix apps/frontend run lint`
  - `npm --prefix apps/frontend run test -- --run`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest -q apps/backend/tests/integration/candidates/test_candidate_api.py apps/backend/tests/integration/candidates/test_cv_parsing_jobs.py apps/backend/tests/integration/vacancies/test_vacancy_pipeline_api.py`
  - `UV_CACHE_DIR=/tmp/uv-cache uv run --project apps/backend pytest apps/backend/tests/unit/test_cors.py apps/backend/tests/unit/auth/test_auth_settings.py -q`
  - `docker compose up -d --build`
  - `./scripts/smoke-compose.sh`
- After merge, sync local `main` before starting the next implementation increment.

## Approved Immediate Follow-On Slice
- Implement `TASK-04-01`, `TASK-04-02`, `TASK-04-03`, and `TASK-11-07` as one vertical slice.
- Backend rules for the slice:
  - use a dedicated scoring package instead of mixing scoring into `candidates` or `vacancies`;
  - add async lifecycle `queued | running | succeeded | failed` in `match_scoring_jobs`;
  - persist a UI-ready score artifact keyed by `vacancy_id + candidate_id + active_document_id`;
  - reject scoring enqueue with `409` when parsed CV analysis is not ready.
- Frontend rules for the slice:
  - do not add a new route; extend the existing HR workspace on `/`;
  - add shortlist review only when both vacancy and candidate are selected;
  - keep compose browser smoke unchanged; scoring verification stays at unit/integration level because of Ollama/runtime nondeterminism.

## Team Roles
- architect
- business-analyst
- backend-engineer
- frontend-engineer
- data-ml-engineer
- qa-engineer
- devops-engineer

## Assignment by Workstream

| Workstream | Owner | TASK-* |
| --- | --- | --- |
| Platform containerization baseline | devops-engineer + backend-engineer + frontend-engineer | TASK-12-01 |
| Security and access baseline | architect + backend-engineer | TASK-01-01, TASK-01-02, TASK-01-03, TASK-01-04 |
| Compliance baseline | business-analyst + architect | TASK-01-05 |
| Compliance article-level mapping and evidence model | business-analyst + legal + architect | TASK-13-01, TASK-13-02 |
| Candidate and vacancy core domain | backend-engineer | TASK-03-01, TASK-02-01, TASK-02-02, TASK-02-03 |
| CV ingestion and parsing | backend-engineer + data-ml-engineer | TASK-03-02, TASK-03-03 |
| Ollama scoring pipeline | data-ml-engineer + backend-engineer | TASK-04-01, TASK-04-02, TASK-04-03 |
| Interview orchestration | backend-engineer | TASK-05-01, TASK-05-02, TASK-05-03, TASK-05-04 |
| Automation and KPI events | backend-engineer | TASK-08-01, TASK-08-02, TASK-08-03, TASK-08-04 |
| KPI data layer and snapshots | backend-engineer + data-ml-engineer | TASK-10-01, TASK-10-02 |
| Frontend platform and v1 flows | frontend-engineer | TASK-11-01, TASK-11-02, TASK-11-03, TASK-11-04, TASK-11-05, TASK-11-06, TASK-11-07, TASK-11-08, TASK-11-09 |
| Quality gates | qa-engineer | test strategy for all M1 tasks + release gate checks |
| CI/CD and environments | devops-engineer | CI baseline, environment configs, release pipeline |

## Sprint Approval
- Approved baseline: `M1` from `docs/project/tasks.md`.
- Start date: 2026-03-04.
- End date: rolling, as fast as possible with quality gates.

## Risks and Dependencies
- Docker image and compose baseline must be stable before multi-role feature streams scale.
- Legal controls matrix must progress in parallel for production readiness.
- External integrations (Ollama, Google Calendar) require stable staging credentials.
- Frontend localization (RU/EN) must be built into base routing and content model from first iteration.
- Production legal sign-off (`TASK-13-04`) is not a blocker for current local-stage acceptance, but remains mandatory before first production release.
