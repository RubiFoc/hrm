# Epic Task Backlog

## Last Updated
- Date: 2026-03-27
- Updated by: business-analyst + coordinator

## Priority Model
- `P0`: critical for Phase 1 core delivery.
- `P1`: important for completing full business flows.
- `P2`: later optimization/expansion tasks.
- Current stage delivery target: stable local runtime on the current device.
- Production rollout is out of scope for the current stage and tracked as future gate work (`TASK-13-*`).

## Execution Status Snapshot

| Track | Status | Evidence |
| --- | --- | --- |
| ADMIN-01 | done | Merged in `main` via PR #48 |
| ADMIN-02 | done/closed | GitHub issue #53 closed; merged in `main` via PR #51 (`bd96d86`) |
| ADMIN-03 | done/closed | GitHub issue #52 closed; merged in `main` via PR #55 (`2c9c5b5`) |
| ADMIN-04 | done/closed | Frontend admin candidates/vacancies/pipeline/audit consoles now reuse existing recruitment and audit contracts, keep the slice non-destructive, and include XLSX audit export support. |
| TASK-01-01/02/03/04/05 | done/closed | GitHub issues #1, #2, #3, #4, and #24 were closed during backlog normalization; current repo/docs remain the source of truth for the implemented security foundation |
| TASK-11-13 | done/closed | GitHub issue #67 closed; merged in `main` via PR #68 and PR #69 (`d8ea39e`) |
| TASK-12-01 | implemented/local-compose-baseline | `docker-compose.yml`, Dockerfiles, `./scripts/smoke-compose.sh`, and CI compose browser smoke already verify the local stack (`frontend`, `backend`, `backend-worker`, `postgres`, `redis`, `minio`) plus bootstrap jobs |
| TASK-12-02 | done/closed | GitHub issue #85 closed; merged in `main` via PR #105 (`a67bb8c`) with Linux-safe host-gateway wiring for external-host Ollama, optional compose profile `ai-local` (`ollama` + `ollama-init` + persistent volume), and operator-facing `./scripts/smoke-scoring-compose.sh` while keeping baseline compose/browser smoke and scoring/public contracts unchanged |
| TASK-11-01/02/03/04 | done/closed | GitHub issues #25, #26, #27, and #28 were closed during backlog normalization; the current repo remains the source of truth for the implemented frontend foundation |
| TASK-03-01/02/03/05/06/07/08 | implemented/local-universal-profile-enrichment-slice | GitHub issue #90 is now closed; backend candidate profile, public apply, async parsing, native PDF/DOCX text extraction, RU/EN normalization, profession-agnostic structured CV enrichment (workplaces with held positions, education, normalized titles/dates, generic skills), evidence traceability, and public tracking endpoints are present in repo with unit/integration coverage |
| TASK-03-04 | done/closed | GitHub issue #91 closed; merged in `main` via PR #107 (`0d9c787`) with recruiter-facing `GET /api/v1/candidates` search/filter/pagination, active-CV enrichment, vacancy-context latest-stage filters, and server-filtered HR dashboard controls |
| TASK-02-01/02/03 | implemented/local-baseline | Backend vacancy CRUD, pipeline transitions, and ordered transition history endpoint are present in repo with integration coverage |
| TASK-02-04 | done/closed | GitHub issue #88 closed; merged in `main` via PR #128 (`3ad1c9e`) with manager-scoped vacancy overview + PII-redacted candidate snapshot visibility and offer status enrichment |
| TASK-08-03 | done/closed | GitHub issue #20 closed; merged in `main` via PR #131 |
| TASK-08-04 | implemented/local-automation-kpi-slice | Durable automation KPI metric events, monthly snapshot aggregation, leader labels, and docs/tests are implemented in repo |
| TASK-11-06 | implemented/local-baseline | Public candidate apply/tracking now runs on `/careers` with checked-in branding, a browseable open-role board backed by `GET /api/v1/public/vacancies`, shareable vacancy detail/apply pages on `/careers/:vacancyId`, checksum-based upload, sessionStorage tracking context, and job-based parsing/analysis polling; `/candidate/apply` now hosts the compatibility apply shell and `/candidate` redirects into it |
| TASK-11-05 | implemented/local-baseline | HR recruitment UX is now split across `/hr` overview, `/hr/vacancies`, `/hr/pipeline`, `/hr/interviews`, `/hr/offers`, and legacy `/hr/workbench`, covering staff vacancy CRUD, vacancy editing, candidate selection, pipeline transition append, and history timeline UX |
| TASK-11-09 | implemented/local-baseline | RU/EN strings cover login, candidate apply/tracking/analysis, admin, and HR workspace critical flows |
| TASK-11-11 | done/closed | Compose browser smoke covers staff login and public candidate apply journeys through headless Chrome on the shareable careers vacancy route; this baseline is already integrated into the compose smoke path. |
| TASK-04-01/02/03 | implemented/local-scoring-slice | Dedicated `hrm_backend/scoring` package, Ollama adapter, async scoring jobs/artifacts, and frozen scoring API contract are present in repo with unit and integration coverage |
| TASK-04-05 | implemented/local-scoring-slice | Score payloads and HR shortlist review now expose matched requirements, missing competencies, and evidence snippets from parsed CV analysis |
| TASK-04-06 | done/closed | GitHub issue #92 closed; merged in `main` via PR #111 (`eedcc0f`) with additive scoring quality harness tooling under `hrm_backend.scoring.evaluation`, deterministic fixture-mode `precision`/`recall` + `NDCG`/`MRR` + paraphrase robustness reporting, optional Ollama mode reuse, and backend unit/integration coverage |
| TASK-04-04 | done/closed | Merged in `main` via PR #109 (`c60b48b`) with additive low-confidence manual-review metadata, configurable `SCORING_LOW_CONFIDENCE_THRESHOLD`, and localized shortlist warning UX that preserves score details |
| TASK-11-07 | implemented/local-scoring-slice | Legacy HR workbench on `/hr/workbench` now includes shortlist review with `Run score`, polling, confidence/summary card, requirements delta, evidence, and localized `409/403/404/422` errors |
| TASK-11-10 | done/closed | Frontend Sentry now tags `/`, `/careers`, `/careers/:vacancyId`, `/hr`, `/hr/vacancies`, `/hr/pipeline`, `/hr/interviews`, `/hr/offers`, `/hr/workbench`, `/manager`, `/accountant`, `/employee`, `/leader`, `/candidate`, `/candidate/apply`, `/candidate/interview/:interviewToken`, `/login`, `/admin`, `/admin/staff`, `/admin/employee-keys`, `/admin/candidates`, `/admin/vacancies`, `/admin/pipeline`, `/admin/audit`, and `/admin/observability`; shared HTTP capture, render boundary, and release/env tracing config are present in repo with frontend unit coverage |
| TASK-11-12 | implemented/local-phase-2-role-workspaces-slice | Repo-backed manager/accountant workspaces on `/manager` and `/accountant`, employee workspace on `/employee`, leader workspace on `/leader`, and HR overview plus legacy `/hr/workbench` shell are implemented with route guards, typed OpenAPI clients, backend integration coverage, frontend router/page tests, and canonical Sentry route tags; the umbrella backlog item is now normalized closed. |
| TASK-11-14 | done/closed | Frontend-refresh closeout complete: the public company landing page on `/` ships with careers navigation and checked-in media assets. |
| TASK-11-15 | done/closed | Frontend-refresh closeout complete: staff workspaces are split onto dedicated role routes with role-based post-login redirects. |
| TASK-11-16 | done/closed | Frontend-refresh closeout complete: the refreshed visual system and careers upload surface ship with checked-in image assets. |
| TASK-11-17 | done/closed | Public company landing, careers, vacancy detail, candidate apply, and candidate interview pages now use leaner shells with secondary rail blocks removed and copy density reduced; `/` reads as a premium corporate homepage with a clear company overview, careers entrypoint, and footer. |
| TASK-13-01/02 | implemented/local-compliance-slice | Legal-controls matrix now maps article-level obligations to current repo-backed controls and evidence registry entries with owners, verification sources, and update triggers |
| TASK-05-01/02 | implemented/local-interview-slice | Interview slot planning, participant assignment, and Google Calendar sync/reconciliation baseline are implemented in repo on the existing route topology |
| TASK-11-08 | implemented/local-interview-slice | Interview scheduling and candidate registration are implemented against `docs/project/interview-planning-pass.md`, with HR controls on `/hr`, public token registration on `/candidate/interview/:interviewToken`, `/candidate` compatibility redirects, and free-mode Google Calendar sync via service account + shared interviewer calendars |
| TASK-05-03/04 | done/closed | GitHub issues #16 and #17 are closed; merged in `main` via PR #82 (`182875c`) with schedule-versioned feedback and the existing `interview -> offer` fairness gate |
| TASK-06-01 | implemented/local-offer-slice | Offer persistence, staff lifecycle APIs on the existing vacancy route tree, `/hr` offer workflow UI, and `offer -> hired/rejected` guards are present in repo with OpenAPI/frontend/backend coverage |
| TASK-06-02 | implemented/local-hire-conversion-slice | The existing `POST /api/v1/pipeline/transitions` flow now persists one durable `hire_conversions` handoff atomically with successful `offer -> hired`, while employee profile creation and onboarding execution remain deferred |
| TASK-06-03 | implemented/local-employee-profile-slice | Staff-only `POST/GET /api/v1/employees` now bootstrap one durable `employee_profiles` row from `hire_conversions`, validate frozen snapshots, and prepare the employee-domain trigger surface for onboarding |
| TASK-06-04 | implemented/local-onboarding-trigger-slice | Successful `POST /api/v1/employees` now atomically creates both `employee_profiles` and one durable `onboarding_runs` artifact, and employee read responses expose additive onboarding metadata |
| TASK-07-01 | implemented/local-onboarding-template-slice | Staff-only `POST/GET/PUT /api/v1/onboarding/templates` now manage durable checklist templates and items, including one active default template for later onboarding-task generation |
| TASK-07-02 | implemented/local-onboarding-task-slice | Employee bootstrap now atomically materializes `onboarding_tasks` from the active template, and staff can list/update/backfill tasks on `/api/v1/onboarding/runs/{onboarding_id}/tasks` |
| TASK-07-03 | implemented/local-employee-portal-slice | Employee-only `/employee` workspace plus `GET/PATCH /api/v1/employees/me/onboarding*` now expose self-service onboarding tasks with durable employee-profile identity linking and localized frontend coverage |
| TASK-07-04 | implemented/local-onboarding-dashboard-slice | `GET /api/v1/onboarding/runs*` now exposes HR/admin read-all plus manager-scoped onboarding progress visibility, with the dashboard embedded on `/hr` for HR and reused as the onboarding block inside `/manager` |
| TASK-09-01 | implemented/local-manager-workspace-slice | Manager users now land on `/manager` in a read-only hiring + onboarding workspace backed by manager-scoped vacancy APIs, explicit `vacancies.hiring_manager_staff_id` ownership, and the reused onboarding dashboard block, while HR/admin keep the recruitment workspace on `/hr` |
| TASK-09-02 | done/closed | GitHub issue #95 closed; merged in `main` via PR #126 (`06b605e`) with a read-only leader/admin KPI workspace on `/leader`, bounded lookback fallback to the latest available snapshot month, and CSV/XLSX export reuse |
| TASK-09-03 | done/closed | GitHub issue #96 closed; merged in `main` via PR #114 (`c237296`) with accountant workspace routing on `/accountant`, assignment-scoped `/api/v1/accounting/workspace*`, controlled CSV/XLSX exports, and solo-mode architecture self-review workflow alignment |
| TASK-09-04 | done/closed | GitHub issue #97 closed; merged in `main` via PR #116 (`966f3a8`) with recipient-scoped `/api/v1/notifications*`, embedded manager/accountant notifications UI on `/manager` and `/accountant`, fail-closed read/update scope, on-demand digests, regenerated OpenAPI/frontend types, and synced architecture/test docs |
| TASK-10-01 | done/closed | Merged in `main` via commit `bed745f` (`TASK-10-01: add KPI snapshot foundation`) with monthly KPI snapshot data model + aggregation pipeline, admin-only rebuild API, stored snapshot read surface, migration, reporting unit/integration coverage, and synchronized OpenAPI/frontend generated types |
| TASK-10-02 | done/closed | Leader/admin read-only KPI snapshots on `/leader` consume stored snapshots with bounded lookback fallback and export reuse; merged in `main` via PR #126 (`06b605e`). |
| TASK-10-03 | done/closed | Merged in `main` via PR #122 with admin-only `GET /api/v1/audit/events` query API, `audit:read` RBAC permission, unit/integration coverage, updated OpenAPI freeze, and refreshed frontend generated types |
| TASK-10-04 | done/closed | GitHub issue #99 closed; merged in `main` via PR #124 (`7a5ca87`) with controlled audit evidence export (`/api/v1/audit/events/export`) in CSV/JSONL/XLSX and KPI snapshot export (`/api/v1/reporting/kpi-snapshots/export`) attachments plus updated docs/diagrams and regenerated OpenAPI/frontend types |
| ADMIN-05 | done/closed | GitHub issue #87 closed; merged in `main` via PR #135 (`3eca7a1`) with a frontend-first admin observability dashboard on `/admin/observability` that reuses `/health`, audit preview, CV parsing status, and match-score status contracts. |
| TASK-13-03 | done/closed | Repo-backed release-gate compliance checklist now makes EPIC-13 pre-prod and production sign-off explicit, with current critical controls, evidence IDs, verification commands, legal/security preconditions, and blocker states captured in the docs set. |
| TASK-13-04 | done/closed | GitHub issue #62 is linked to PR #138; the repo-backed production legal evidence package now defines sign-off workflow, required attachments, evidence freshness rules, blocker handling, and `verified` exit criteria for critical controls without adding runtime/API changes. |
| COMPLIANCE-01 | done/closed | EPIC-13 compliance docs synced across legal-controls matrix, evidence registry, release checklist, and runbook; no runtime scope; Belarus-only gate retained (`CTRL-BY-01` in-progress, `CTRL-BY-02`/`CTRL-BY-03` implemented but unverified) |
| TASK-06-05 | done/clarified | BA clarification for employee profile/avatar policy is frozen in `docs/project/employee-profile-referral-compensation-pass.md`; issue #173 closed; `TASK-06-06` (#174) is unblocked. |
| TASK-06-07 | done/clarified | BA clarification for referral workflow is frozen in `docs/project/employee-profile-referral-compensation-pass.md`; issue #175 closed; repo-backed `TASK-06-08` implementation remains aligned with the frozen rules. |
| TASK-09-05 | done/clarified | BA clarification for compensation controls is frozen in `docs/project/employee-profile-referral-compensation-pass.md`; issue #181 closed; `TASK-09-06` is unblocked for implementation planning/execution. |
| TASK-06-08 | implemented/local-referral-slice | Employee referral intake now ships with referral linkage storage, dedupe/merge logic, referral review endpoints on existing pipeline stages, employee/HR/manager referral UI routes, consent gating for public apply, and updated docs/tests/contracts. |

## Requested High-Priority Intake (2026-03-23)

These requests were added as new `P0` items; status below is synced to the current docs baseline.
Business-analyst discovery is mandatory before implementation.
Planning baseline source of truth: `docs/project/employee-profile-referral-compensation-pass.md`.
BA decisions were confirmed by stakeholder on 2026-03-23; `TASK-06-05` was finalized as
`clarified/frozen` on 2026-03-27, and `TASK-09-05` was finalized as `clarified/frozen` on
2026-03-27.

| Request | Backlog Status | New High-Priority Tasks |
| --- | --- | --- |
| Employee profiles with avatars in MinIO and cross-employee profile visibility | clarification done/frozen; implementation pending | `TASK-06-05` (done, issue #173) -> `TASK-06-06` (ready/open, issue #174) |
| Employee referral recommendations for vacancies | clarification done/frozen; implementation local | `TASK-06-07` (done/frozen) -> `TASK-06-08` (implemented/local) |
| Manager compensation controls (salary raises, payroll/bonus table, vacancy salary bands, manager/HR visibility) | clarification done/frozen; implementation pending | `TASK-09-05` (done/frozen) -> `TASK-09-06` (ready/open) |

## 2026-03-12 Delivery Control Notes
- `TASK-12-01` containerized platform baseline is already implemented in repo: `docker compose config`, `docker compose up -d --build`, and `./scripts/smoke-compose.sh` pass against the current stack, and CI reuses the same compose browser smoke baseline.
- `TASK-12-02` is now implemented in repo as an opt-in runtime hardening slice: default compose still targets external-host Ollama via `OLLAMA_BASE_URL`, Linux hosts now get `host.docker.internal:host-gateway`, and self-contained AI verification runs through `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build` plus `./scripts/smoke-scoring-compose.sh`.
- Baseline compose acceptance remains unchanged after `TASK-12-02`: `./scripts/smoke-compose.sh` still verifies login + public apply only and does not require compose-local Ollama.
- Mandatory post-merge closeout for `TASK-12-02` is complete: GitHub issue `#85` closed automatically from PR #105 (`a67bb8c`), and this backlog snapshot is synchronized to the merged `main` state.
- Security foundation work (`TASK-01-01/02/03/04/05`) is materially implemented in repo and supporting docs; this backlog normalization removes it from the effective open count.
- Frontend foundation work (`TASK-11-01/02/03/04`) is materially implemented in repo and supporting tests; remaining frontend backlog is follow-on admin/reporting.
- GitHub issue sync is normalized to the current backlog state: stale implemented-task issues were closed, and missing normalized-open tasks were added as issues #85-#100.
- Backend implementation is ahead of the original planning docs for `TASK-03-01/02/03/05/06` and `TASK-02-01/02/03`; these items are no longer backlog-only work.
- `TASK-03-07` is now implemented in repo: backend parsing extracts text natively from PDF and DOCX before RU/EN normalization and evidence mapping, while current analysis/scoring contracts stay compatible.
- `TASK-03-08` is now implemented in repo and GitHub issue `#90` is closed: parsed CV profiles
  are enriched additively with profession-agnostic workplace history, held positions, education,
  normalized titles/dates, and generic skills while keeping parsing/analysis/scoring contracts
  stable.
- `TASK-03-04` post-merge closeout is complete: GitHub issue `#91` closed automatically from PR
  #107 (`0d9c787`), and this backlog snapshot is synchronized to the merged `main` state while
  keeping the existing route tree and runtime topology unchanged.
- The scoring/shortlist-review slice (`TASK-04-01/02/03 + TASK-11-07`) is now implemented in repo as one vertical delivery unit.
- `TASK-04-04` post-merge closeout is complete: the low-confidence fallback slice is merged in `main` via PR #109 (`c60b48b`), and this backlog snapshot is synchronized to the merged state while keeping the existing route tree and runtime topology unchanged.
- `TASK-04-06` post-merge closeout is complete: GitHub issue `#92` was already closed before PR #111 (`eedcc0f`) merged, and this backlog snapshot is synchronized to the merged `main` state after verifying issue state, PR merge, and branch cleanup.
- Scoring explainability (`TASK-04-05`) and the additive quality harness (`TASK-04-06`) are now implemented in repo without changing runtime routes, lifecycle states, or public scoring contracts.
- The compliance follow-on slices (`TASK-13-01/02`) are now implemented in repo as documentation and evidence-model work only; no runtime/API/routing changes were introduced.
- `TASK-13-03` is now implemented in repo as a docs/process-only release gate; no runtime/API/routing changes were introduced.
- `TASK-13-04` is now implemented in repo as a docs/process-only production sign-off slice: the package manifest makes repo-backed evidence, non-repo attachments, blocker handling, and `verified` exit criteria explicit without adding runtime/API changes.
- The dedicated planning pass for `TASK-11-08` is implemented in repo as one backend+frontend interview slice without reopening auth, CORS, or the public candidate transport model.
- Interview planning and Google Calendar sync baseline (`TASK-05-01/02`) are now implemented in repo; remaining interview backlog starts after the already-landed scheduling/registration and fairness slices.
- The structured interview feedback and fairness gate slice (`TASK-05-03/04`) is now implemented in repo on top of the scheduling baseline, without reopening auth, CORS, route topology, or candidate transport.
- `TASK-06-01` is now implemented in repo as the next dependent slice: one persisted offer lifecycle (`draft`, `sent`, `accepted`, `declined`) on the existing vacancy route tree and `/` workspace, while the existing fairness gate remains the only `interview -> offer` blocker.
- `TASK-06-02` is now implemented on the existing transition endpoint as one atomic follow-on slice: accepted `offer -> hired` transitions create a durable `hire_conversions` handoff for downstream employee-domain work without adding a new route tree or public contract.
- `TASK-06-03` is now implemented as the next employee-domain slice: HR/admin can create and read bootstrapped `employee_profiles` from the frozen hire-conversion handoff on a dedicated staff route.
- `TASK-06-04` is now implemented as the minimal onboarding-trigger follow-on slice: the existing employee bootstrap API atomically persists one `onboarding_runs` row from the created `employee_profile` and returns additive onboarding metadata without adding a new route tree.
- `TASK-07-01` is now implemented as the next onboarding slice: HR/admin can create, read, list, and replace onboarding checklist templates on a dedicated staff onboarding route, while task assignment/execution remains deferred.
- `TASK-07-02` is now implemented as the task-materialization slice: successful `POST /api/v1/employees` fails closed without an active template, otherwise atomically writes `employee_profiles + onboarding_runs + onboarding_tasks`, and HR/admin can read, patch, and backfill tasks on the existing onboarding route tree.
- `TASK-07-03` is now implemented as the employee self-service follow-on slice: authenticated employees use the new `/employee` workspace plus `GET/PATCH /api/v1/employees/me/onboarding*`, while the backend resolves and durably links the employee profile from the existing auth session without reopening the auth or CORS model.
- `TASK-07-04` is now implemented as the HR/manager visibility follow-on slice: `/api/v1/onboarding/runs*` exposes read-only onboarding progress data, HR/admin see all runs inside `/hr`, and managers reuse the same dashboard block inside `/manager` without widening task-mutation permissions.
- `TASK-09-01` is now implemented as the additive manager workspace follow-on slice: managers use `/manager` for one read-only hiring + onboarding workspace, vacancy hiring visibility is scoped by explicit `vacancies.hiring_manager_staff_id`, and onboarding visibility stays task-assignment-scoped through the existing onboarding APIs.
- `TASK-09-03` is now implemented as the additive accountant workspace follow-on slice: accountants use `/accountant` for one read-only finance workspace, visibility stays limited to accountant-assigned onboarding tasks, and controlled CSV/XLSX exports reuse the same filtered row model without adding generic reporting infrastructure.
- `TASK-09-03` post-merge closeout is complete: GitHub issue `#96` is closed, PR #114 (`c237296`) is merged in `main`, and this backlog snapshot is synchronized to the merged state.
- `TASK-09-04` post-merge closeout is complete: GitHub issue `#97` is closed, PR #116 (`966f3a8`) is merged in `main`, and this backlog snapshot is synchronized to the merged state while keeping the notifications slice additive, fail-closed, and in-app only.
- `TASK-10-01` post-merge closeout is complete: the monthly KPI snapshot foundation is synchronized to merged `main` evidence via commit `bed745f` (`TASK-10-01: add KPI snapshot foundation`) with no additional runtime/API changes required in this closeout pass.
- `TASK-10-04` is now implemented as a minimal export package: admin-only audit evidence export (`GET /api/v1/audit/events/export`) in CSV/JSONL/XLSX and leader/admin KPI snapshot export (`GET /api/v1/reporting/kpi-snapshots/export`) with business audit events written after content assembly to avoid self-inclusion.
- `TASK-10-04` post-merge closeout is complete: GitHub issue `#99` is closed, PR #124 (`7a5ca87`) is merged in `main`, and this backlog snapshot is synchronized to the merged state.
- `TASK-11-12` is now implemented in repo as the phase-2 role workspace bundle: manager/accountant workspaces are present on `/manager` and `/accountant`, employee workspace is on `/employee`, leader workspace is on `/leader`, and the HR overview plus legacy `/hr/workbench` shell are present alongside the split HR pages, with route guards, typed OpenAPI clients, frontend router/page tests, and canonical Sentry route tags.
- `TASK-11-10/11` are now implemented and formally closed as the frontend observability and Chrome-browser verification slice.
- `TASK-11-14/15/16` are now implemented and formally closed as the urgent frontend-refresh slice: the app now has a public company landing page on `/`, a branded careers surface on `/careers`, checked-in image assets, split HR route pages with a legacy workbench path, dedicated role pages after login, and a refreshed visual system.
- `TASK-11-17` is now implemented and formally closed as the public copy-density cleanup slice: the public company landing, careers, candidate, and role-shell pages now read as a premium corporate surface with leaner shells and a clearer homepage, careers entrypoint, and footer.
- The remaining follow-on work after the onboarding-dashboard and manager-workspace slices is limited to notifications, reporting, and admin/ops backlog, not baseline scheduling, registration, feedback transport, or candidate-facing offer decisions.
- Existing auth/CORS/public candidate transport assumptions stay unchanged across the observability and compliance follow-on slices.

## Active Queue After Current Slice

- `TASK-12-01` is no longer active queue work; compose baseline acceptance is already satisfied in repo and the remaining step is tracker/issue closure alignment.
- `TASK-05-03/04` is no longer active queue work; the implemented source of truth remains `docs/project/interview-feedback-fairness-pass.md`.
- `TASK-06-01` is no longer active queue work; the implemented source of truth is the current repo-backed offer lifecycle on the existing vacancy route tree.
- `TASK-06-02` is no longer active queue work; the implemented source of truth is the repo-backed atomic `offer -> hired` conversion handoff on the existing transition endpoint.
- `TASK-06-03` is no longer active queue work; the implemented source of truth is the repo-backed staff employee bootstrap flow on `/api/v1/employees`.
- `TASK-06-04` is no longer active queue work; the implemented source of truth is the repo-backed atomic onboarding trigger on the same employee bootstrap endpoint.
- `TASK-07-01` is no longer active queue work; the implemented source of truth is the repo-backed onboarding checklist template API on `/api/v1/onboarding/templates`.
- `TASK-07-02` is no longer active queue work; the implemented source of truth is the repo-backed onboarding task generation/backfill/update API on `/api/v1/onboarding/runs/{onboarding_id}/tasks`.
- `TASK-07-03` is no longer active queue work; the implemented source of truth is the repo-backed employee self-service onboarding portal on `/employee` plus `/api/v1/employees/me/onboarding*`.
- `TASK-07-04` is no longer active queue work; the implemented source of truth is the repo-backed onboarding progress dashboard on `/api/v1/onboarding/runs*`, embedded for HR on `/hr` and reused inside `/manager`.
- `TASK-09-01` is no longer active queue work; the implemented source of truth is the repo-backed manager workspace on `/manager` plus manager-scoped vacancy read endpoints on the existing `/api/v1/vacancies` namespace.
- `ADMIN-04` is no longer active queue work; the implemented source of truth is the repo-backed admin control plane on `/admin/candidates`, `/admin/vacancies`, `/admin/pipeline`, and `/admin/audit` with non-destructive recruitment and audit contract reuse.
- `ADMIN-05` is no longer active queue work; the implemented source of truth is the repo-backed admin observability dashboard on `/admin/observability` with read-only health, audit preview, and job-status lookup reuse.
- `TASK-09-03` is no longer active queue work; the implemented source of truth is the repo-backed accountant workspace on `/accountant` plus assignment-scoped finance read/export endpoints on `/api/v1/accounting/workspace*`.
- `TASK-09-04` is no longer active queue work; the implemented source of truth is the repo-backed recipient-scoped notification API on `/api/v1/notifications*` plus the embedded manager/accountant notifications blocks on `/manager` and `/accountant`.
- `TASK-10-01` post-merge closeout is complete: the repo-backed monthly KPI snapshot foundation is closed with merged evidence `bed745f` and follow-on leader/admin read exposure tracked by `TASK-10-02`.
- `TASK-10-02` post-merge closeout is complete: leader/admin KPI snapshot reads on `/leader` are stored-snapshot-only with admin-only rebuild; merged in `main` via PR #126 (`06b605e`).
- `TASK-08-04` is no longer active queue work; the implemented source of truth is the repo-backed automation metric event stream and monthly KPI aggregation path.
- `TASK-10-04` is no longer active queue work; the implemented source of truth is the bounded export attachments on `GET /api/v1/audit/events/export` and `GET /api/v1/reporting/kpi-snapshots/export`.
- `TASK-11-10/11` are no longer active queue work; the frontend observability and browser verification closeout is formally complete and the implemented source of truth is the current repo-backed Sentry tagging and browser smoke coverage.
- `TASK-11-14/15/16` are no longer active queue work; the frontend-refresh closeout is formally complete and the implemented source of truth is the current repo-backed public company landing, role-route split, and refreshed visual system.
- The remaining candidate-domain follow-on work after `TASK-03-08` and `TASK-04-06` is limited to
  later ops/reporting slices, not baseline parsed-profile structure or scoring-quality tooling.

## Remaining Backlog Snapshot

- Remaining backlog items are repopulated below so the repo reflects both still-open work and repo-implemented slices that have not been formally closed yet.
- P0:
  - `TASK-12-01`
  - `TASK-03-01/02/03/05/06/07`
  - `TASK-02-01/02/03`
  - `TASK-08-01/02/04`
  - `TASK-04-01/02/03/05`
  - `TASK-05-01/02`
  - `TASK-11-05/06/07/08/09`
  - `TASK-13-01/02`
  - `TASK-06-06`
  - `TASK-09-06`
- P1:
  - `TASK-03-08`
  - `TASK-06-01/02/03/04`
  - `TASK-07-01/02/03/04`
  - `TASK-09-01`
- `TASK-11-12` stays excluded because its umbrella backlog item is already normalized closed.
- P2: none

- Current open backlog by delivery wave:
  - P0: `TASK-12-01`, `TASK-03-01/02/03/05/06/07`, `TASK-02-01/02/03`, `TASK-08-01/02/04`, `TASK-04-01/02/03/05`, `TASK-05-01/02`, `TASK-11-05/06/07/08/09`, `TASK-13-01/02`, `TASK-06-06`, `TASK-09-06`
  - P1: `TASK-03-08`, `TASK-06-01/02/03/04`, `TASK-07-01/02/03/04`, `TASK-09-01`
  - P2: none

## GitHub Issue Queue

- P0:
  - Closed `TASK-06-05` (issue #173): BA clarification for employee public profile +
    avatar storage policy is frozen in docs.
  - Open/track `TASK-06-06` (issue #174): employee profile visibility + avatar upload/read
    implementation on existing employee domain/workspaces; dependency `TASK-06-05` is satisfied.
  - Closed `TASK-06-07` (issue #175): BA clarification for referral workflow is frozen in docs; repo-backed
    `TASK-06-08` implementation remains the runtime source of truth.
  - Closed `TASK-06-08`: employee referral recommendation flow implementation is in repo and the GitHub issue is closed post-merge.
  - Closed `TASK-09-05` (issue #181): BA clarification for compensation management baseline is frozen in docs.
  - Open/track `TASK-09-06`: manager/HR compensation tooling implementation (raise actions, salary/bonus table, vacancy salary bands, employee-to-band visibility); dependency `TASK-09-05` is satisfied.
- P1:
  - RU-scope issues `#142`, `#143`, and `#145` should be closed as de-scoped after ADR-0059.

- Execution rule for follow-on interview work: keep the implemented `/hr`, `/candidate/apply`, and `/candidate/interview/:interviewToken` topology, plus the public company/careers entrypoints on `/` and `/careers`, unchanged unless a separate ADR reopens that scope.

## Task Breakdown by Epic

| Task ID | Epic | Task | Phase | Priority | Depends On |
| --- | --- | --- | --- | --- | --- |
| TASK-01-01 | EPIC-01 | Define RBAC role matrix for HR, Candidate, Manager, Employee, Leader, Accountant | Phase 1 | P0 | - |
| TASK-01-02 | EPIC-01 | Implement authentication and session/token lifecycle | Phase 1 | P0 | TASK-01-01 |
| TASK-01-03 | EPIC-01 | Implement access policy middleware for API and background jobs | Phase 1 | P0 | TASK-01-02 |
| TASK-01-04 | EPIC-01 | Implement audit logging for sensitive data access | Phase 1 | P0 | TASK-01-03 |
| TASK-01-05 | EPIC-01 | Define and apply Belarus data storage and retention baseline | Phase 1 | P0 | TASK-01-01 |
| TASK-13-01 | EPIC-13 | Map article-level Belarus legal obligations to controls in legal-controls matrix | Phase 1 | P0 | TASK-01-05 |
| TASK-13-02 | EPIC-13 | Define evidence registry and ownership model for each critical legal control | Phase 1 | P0 | TASK-13-01 |
| TASK-13-03 | EPIC-13 | Add release-gate compliance checklist for critical controls and legal sign-off preconditions | Phase 1-2 | P1 | TASK-13-02 |
| TASK-13-04 | EPIC-13 | Prepare production legal evidence package and sign-off workflow | Phase 2 | P1 | TASK-13-03 |
| TASK-12-01 | EPIC-12 | Provision containerized platform with Docker and Docker Compose (backend, frontend, db, queue, object storage) | Phase 1 | P0 | - |
| TASK-12-02 | EPIC-12 | Add optional local Ollama compose profile and Linux-safe connectivity baseline for self-contained AI scoring verification | Phase 1 | P1 | TASK-12-01, TASK-04-01 |
| TASK-11-01 | EPIC-11 | Initialize React.js + TypeScript frontend foundation (app shell, routing, project structure) | Phase 1 | P0 | TASK-01-01 |
| TASK-11-02 | EPIC-11 | Implement frontend engineering baseline with popular libraries (MUI, React Router, TanStack Query, React Hook Form, Zod) | Phase 1 | P0 | TASK-11-01 |
| TASK-11-03 | EPIC-11 | Implement auth-aware route guards and role-based navigation | Phase 1 | P0 | TASK-11-01, TASK-01-02 |
| TASK-11-04 | EPIC-11 | Implement shared UI component system, forms, validation, and accessibility baseline | Phase 1 | P0 | TASK-11-01 |
| TASK-11-05 | EPIC-11 | Implement HR vacancy and pipeline workspace UI (after candidate intake baseline) | Phase 1 | P0 | TASK-11-03, TASK-02-02 |
| TASK-11-06 | EPIC-11 | Implement candidate self-service workspace UI (CV upload, profile confirmation) | Phase 1 | P0 | TASK-11-03, TASK-03-02 |
| TASK-11-07 | EPIC-11 | Implement shortlist and match-scoring review UI inside the dedicated HR workspace on `/hr` with confidence visualization | Phase 1 | P0 | TASK-11-06, TASK-04-03 |
| TASK-11-08 | EPIC-11 | Implement interview scheduling and candidate interview-registration UI with Google Calendar sync status after a dedicated planning pass for interview product rules | Phase 1 | P0 | TASK-11-05, TASK-11-06, TASK-05-02 |
| TASK-11-09 | EPIC-11 | Implement RU/EN localization infrastructure and translations for critical v1 flows | Phase 1 | P0 | TASK-11-02, TASK-11-05, TASK-11-06 |
| TASK-11-10 | EPIC-11 | Implement frontend observability with Sentry (error tracking, performance metrics, release markers) | Phase 1-2 | P1 | TASK-11-02 |
| TASK-11-11 | EPIC-11 | Implement Chrome compatibility checks and regression verification for critical v1 journeys | Phase 1 | P1 | TASK-11-05, TASK-11-06 |
| TASK-11-12 | EPIC-11 | Implement phase-2 role workspaces (manager, employee, accountant, leader) | Phase 2 | P1 | TASK-06-03, TASK-07-04, TASK-09-01 |
| TASK-11-13 | EPIC-11 | Implement staff login window and session bootstrap UX | Phase 1 | P0 | TASK-01-02, TASK-11-03 |
| TASK-11-14 | EPIC-11 | Add public company landing page with careers navigation and branded media assets | Phase 1-2 | P0 | TASK-11-01, TASK-11-04, TASK-11-06 |
| TASK-11-15 | EPIC-11 | Split staff workspaces onto dedicated role routes (`/hr`, `/hr/vacancies`, `/hr/pipeline`, `/hr/interviews`, `/hr/offers`, `/hr/workbench`, `/manager`, `/accountant`) with role-based post-login redirects | Phase 1-2 | P0 | TASK-11-03, TASK-11-12, TASK-11-13 |
| TASK-11-16 | EPIC-11 | Refresh frontend visual system and careers upload surface with checked-in image assets | Phase 1-2 | P0 | TASK-11-04, TASK-11-06, TASK-11-09 |
| TASK-11-17 | EPIC-11 | Closed public copy-density cleanup slice for the premium company landing, careers, candidate, and role-shell pages | Phase 1-2 | done/closed | TASK-11-09, TASK-11-14, TASK-11-15, TASK-11-16 |
| ADMIN-01 | ADMIN-EPIC-01 | Implement admin auth guard and admin shell (frontend/backend contract) | Phase 1 | P0 | TASK-01-02, TASK-11-03 |
| ADMIN-02 | ADMIN-EPIC-01 | Implement staff management APIs/UI (create/update/disable) | Phase 1 | P0 | ADMIN-01 |
| ADMIN-03 | ADMIN-EPIC-01 | Implement employee registration key management APIs/UI (generate/revoke/list) | Phase 1 | P0 | ADMIN-01 |
| ADMIN-04 | ADMIN-EPIC-01 | Implement admin CRUD consoles for candidates/vacancies/pipeline/audit | Phase 1-2 | P1 | ADMIN-02, ADMIN-03, TASK-02-02, TASK-03-03 |
| ADMIN-05 | ADMIN-EPIC-01 | Implement admin observability dashboards (audit + job status) | Phase 1-2 | P1 | ADMIN-04 |
| TASK-02-01 | EPIC-02 | Implement vacancy CRUD and lifecycle states | Phase 1 | P0 | TASK-01-03 |
| TASK-02-02 | EPIC-02 | Implement recruitment pipeline stage management | Phase 1 | P0 | TASK-02-01 |
| TASK-02-03 | EPIC-02 | Implement candidate stage transition history and timeline | Phase 1 | P0 | TASK-02-02 |
| TASK-02-04 | EPIC-02 | Implement manager vacancy view and candidate list visibility rules | Phase 1 | P1 | TASK-02-03 |
| TASK-03-01 | EPIC-03 | Implement candidate profile schema and CRUD endpoints | Phase 1 | P0 | TASK-01-03 |
| TASK-03-02 | EPIC-03 | Implement CV/document upload with encrypted object storage | Phase 1 | P0 | TASK-03-01 |
| TASK-03-03 | EPIC-03 | Implement async CV parsing job and status tracking | Phase 1 | P0 | TASK-03-02 |
| TASK-03-05 | EPIC-03 | Implement bilingual RU/EN CV normalization into canonical candidate profile schema | Phase 1 | P0 | TASK-03-03 |
| TASK-03-06 | EPIC-03 | Persist evidence links from extracted facts to source CV fragments (sentence/paragraph) | Phase 1 | P0 | TASK-03-05 |
| TASK-03-07 | EPIC-03 | Implement native PDF/DOCX text extraction before normalization and evidence mapping | Phase 1 | P0 | TASK-03-03 |
| TASK-03-08 | EPIC-03 | Expand canonical CV profile extraction to profession-agnostic workplace entries with held positions, education, normalized titles/dates, and generic skills | Phase 1 | P1 | TASK-03-07, TASK-03-06 |
| TASK-03-04 | EPIC-03 | Implement candidate search and filter API for HR | Phase 1 | P1 | TASK-03-01 |
| TASK-04-01 | EPIC-04 | Implement Ollama adapter with model/version configuration for the dedicated scoring package | Phase 1 | P0 | TASK-03-03 |
| TASK-04-02 | EPIC-04 | Implement async match scoring pipeline (`match_scoring_jobs` + worker + persisted score artifact) | Phase 1 | P0 | TASK-04-01 |
| TASK-04-03 | EPIC-04 | Implement recruiter-facing score schema with confidence, summary, requirement deltas, and evidence fields | Phase 1 | P0 | TASK-04-02 |
| TASK-04-05 | EPIC-04 | Implement explainable match output with matched requirements, missing competencies, and evidence snippets | Phase 1 | P0 | TASK-04-03, TASK-03-06 |
| TASK-04-06 | EPIC-04 | Implement AI quality harness (precision/recall, NDCG/MRR, paraphrase robustness checks) | Phase 1 | P1 | TASK-04-05 |
| TASK-04-04 | EPIC-04 | Implement low-confidence fallback to manual HR review | Phase 1 | P1 | TASK-04-03 |
| TASK-05-01 | EPIC-05 | Implement interview slot planning and participant assignment | Phase 1 | P0 | TASK-02-03, TASK-03-01 |
| TASK-05-02 | EPIC-05 | Implement Google Calendar sync adapter and reconciliation logic | Phase 1 | P0 | TASK-05-01 |
| TASK-05-03 | EPIC-05 | Implement mandatory structured interview feedback form | Phase 1 | P0 | TASK-05-01 |
| TASK-05-04 | EPIC-05 | Implement fairness rubric validation before decision stage | Phase 1 | P0 | TASK-05-03 |
| TASK-08-01 | EPIC-08 | Implement automation rule model and trigger evaluation engine | Phase 1 | P0 | TASK-01-03, TASK-02-03 |
| TASK-08-02 | EPIC-08 | Implement automation executor with retries and idempotency | Phase 1 | P0 | TASK-08-01 |
| TASK-08-03 | EPIC-08 | Implement automation execution logs and error traceability | Phase 1 | P0 | TASK-08-02 |
| TASK-08-04 | EPIC-08 | Implement automation metric event stream for KPI calculation | Phase 1 | P0 | TASK-08-03 |
| TASK-06-01 | EPIC-06 | Implement offer workflow (draft, sent, accepted, declined) | Phase 2 | P1 | TASK-05-04 |
| TASK-06-02 | EPIC-06 | Implement candidate-to-employee conversion workflow | Phase 2 | P1 | TASK-06-01 |
| TASK-06-03 | EPIC-06 | Implement initial employee profile creation and validation | Phase 2 | P1 | TASK-06-02 |
| TASK-06-04 | EPIC-06 | Trigger onboarding workflow on successful conversion | Phase 2 | P1 | TASK-06-03 |
| TASK-06-05 | EPIC-06 | BA clarification pass for employee public profile (clarified/frozen on 2026-03-27): avatar storage in MinIO, profile visibility across employees, privacy/moderation constraints, and acceptance metrics | Phase 2 | P0 | TASK-06-03 |
| TASK-06-06 | EPIC-06 | Implement employee public profile cards with avatar upload/read in MinIO and cross-employee profile viewing controls | Phase 2 | P0 | TASK-06-05 |
| TASK-06-07 | EPIC-06 | BA clarification pass for referral workflow (clarified/frozen on 2026-03-27): recommendation flow, role permissions, anti-abuse rules, reward/accounting policy, and legal/audit boundaries | Phase 2 | P0 | TASK-06-03 |
| TASK-06-08 | EPIC-06 | Implement employee referral recommendations for vacancies (recommend friend, lifecycle statuses, manager/HR review visibility) | Phase 2 | P0 | TASK-06-07, TASK-02-01 |
| TASK-07-01 | EPIC-07 | Implement onboarding checklist template management | Phase 2 | P1 | TASK-06-04 |
| TASK-07-02 | EPIC-07 | Implement onboarding task assignment and SLA tracking | Phase 2 | P1 | TASK-07-01 |
| TASK-07-03 | EPIC-07 | Implement employee onboarding task portal | Phase 2 | P1 | TASK-07-02 |
| TASK-07-04 | EPIC-07 | Implement HR/manager onboarding progress dashboard | Phase 2 | P1 | TASK-07-03 |
| TASK-09-01 | EPIC-09 | Implement manager workspace for team hiring/onboarding visibility | Phase 2 | P1 | TASK-07-04 |
| TASK-09-02 | EPIC-09 | Implement leader workspace for KPI and operational overview | Phase 2 | P1 | TASK-10-02 |
| TASK-09-03 | EPIC-09 | Implement accountant workspace with controlled export access | Phase 2 | P1 | TASK-06-03 |
| TASK-09-04 | EPIC-09 | Implement role-specific notifications and summary digests | Phase 2 | P2 | TASK-09-01 |
| TASK-09-05 | EPIC-09 | BA clarification pass for compensation management (clarified/frozen on 2026-03-27): raise permissions, approval chain, salary-band governance by vacancy, payroll/bonus table scope, and security controls | Phase 2 | P0 | TASK-09-03 |
| TASK-09-06 | EPIC-09 | Implement manager/HR compensation controls: raise updates, payroll+bonus table visibility, vacancy salary bands, and employee-to-band display in manager/HR workspace | Phase 2 | P0 | TASK-09-05, TASK-09-03 |
| TASK-10-01 | EPIC-10 | Implement KPI data model and aggregation pipeline | Phase 1-2 | P0 | TASK-08-04 |
| TASK-10-02 | EPIC-10 | Expose stored monthly KPI snapshots to leaders (read-only) | Phase 1-2 | P0 | TASK-10-01 |
| TASK-10-03 | EPIC-10 | Implement audit query API and compliance evidence view | Phase 1-2 | P1 | TASK-01-04 |
| TASK-10-04 | EPIC-10 | Implement export package for audits and management reporting | Phase 2 | P1 | TASK-10-02, TASK-10-03 |

## Global Prioritized Queue

Historical planning queue retained for lineage; implemented items from the execution snapshot above are not active backlog work.

| Order | Task ID | Why Now |
| --- | --- | --- |
| 0 | TASK-12-01 | Delivered in repo; retained as historical sequencing reference for the compose baseline |
| 1 | TASK-01-01 | Foundation for all role-based behavior |
| 2 | TASK-01-02 | System entrypoint security baseline |
| 3 | TASK-01-03 | Access enforcement for all endpoints |
| 4 | TASK-01-05 | Compliance baseline needed before scale |
| 5 | ADMIN-01 | Admin shell unblocks privileged control plane work |
| 6 | ADMIN-02 | Staff lifecycle must be operationalized early |
| 7 | ADMIN-03 | Employee key lifecycle is required for staff self-registration |
| 8 | TASK-11-13 | Immediate frontend login UX needed for local/day-to-day staff workflow validation |
| 9 | TASK-03-01 | Candidate domain base model immediately after admin baseline |
| 10 | TASK-03-02 | Candidate must be able to upload CV early (PDF/DOCX intake) |
| 11 | TASK-03-03 | Async parsing status is required for candidate self-service UX |
| 12 | TASK-03-05 | RU/EN canonical normalization is required by CV-analysis scope |
| 13 | TASK-03-06 | Evidence traceability is required for explainable hiring decisions |
| 14 | TASK-04-01 | Mandatory Ollama adapter for AI scoring module |
| 15 | TASK-04-02 | Scoring execution pipeline on parsed candidate profile |
| 16 | TASK-04-03 | Confidence + explanation schema for HR decision support |
| 17 | TASK-04-05 | Match/mismatch explainability with evidence snippets |
| 18 | TASK-04-06 | Quality harness for extraction/ranking and robustness |
| 19 | TASK-02-01 | HR vacancy module starts after candidate CV intake baseline |
| 20 | TASK-02-02 | Pipeline control for HR operations |
| 21 | TASK-02-03 | Timeline/history for recruiting decisions |
| 22 | TASK-03-04 | HR productivity via candidate filtering |
| 23 | TASK-05-01 | Interview orchestration start point |
| 24 | TASK-05-02 | Mandatory Google Calendar integration |
| 25 | TASK-05-03 | Structured interview quality control |
| 26 | TASK-05-04 | Fairness gate before hiring decision |
| 27 | TASK-08-01 | Start automation to hit KPI target |
| 28 | TASK-08-02 | Reliable automation execution |
| 29 | TASK-08-03 | Operational support and troubleshooting |
| 30 | TASK-08-04 | Delivered in repo; retained as historical sequencing reference for automation KPI telemetry |
| 31 | TASK-10-01 | KPI data layer foundation |
| 32 | TASK-10-02 | Leader read exposure for stored KPI snapshots |
| 33 | TASK-01-04 | Complete auditability of sensitive actions |
| 34 | TASK-04-04 | Human fallback for low AI confidence |
| 35 | TASK-02-04 | Manager visibility enrichment |
| 36 | TASK-06-01 | Offer lifecycle for conversion to employees |
| 37 | TASK-06-02 | Candidate to employee state transition |
| 38 | TASK-06-03 | Employee profile initialization |
| 39 | TASK-06-04 | Onboarding flow trigger |
| 40 | TASK-07-01 | Onboarding template baseline |
| 41 | TASK-07-02 | Task execution tracking |
| 42 | TASK-07-03 | Employee self-service onboarding |
| 43 | TASK-07-04 | HR/manager onboarding control |
| 44 | TASK-10-03 | Compliance and audit read interfaces |
| 45 | TASK-09-01 | Manager workspace full rollout |
| 46 | TASK-09-03 | Accountant workspace rollout |
| 47 | TASK-10-04 | Reporting export package |
| 48 | TASK-09-02 | Leader workspace finalization |
| 49 | TASK-09-04 | Notification optimization |
| 50 | TASK-06-05 | BA-first clarification for employee public profiles and avatar governance (completed/frozen) |
| 51 | TASK-06-06 | Employee profile avatars in MinIO with cross-employee visibility |
| 52 | TASK-06-07 | BA-first clarification for referral business rules (completed/frozen) |
| 53 | TASK-06-08 | Employee referral recommendation flow rollout |
| 54 | TASK-09-05 | BA-first clarification for compensation authority and data scope (completed/frozen) |
| 55 | TASK-09-06 | Manager/HR compensation controls with salary bands and payroll/bonus table |

## Parallel Compliance Queue (No Change to Feature Sequence)
This queue must be executed in parallel while preserving feature rollout order:
admin -> candidate CV intake -> HR module.

| Compliance Order | Task ID | Why Now |
| --- | --- | --- |
| C-1 | TASK-13-01 | Lock article-level legal mapping early to avoid control rework later |
| C-2 | TASK-13-02 | Assign evidence owners and artifacts before feature surface expands |
| C-3 | TASK-13-03 | Make release-governance checks deterministic for pre-prod gate |
| C-4 | TASK-13-04 | Produce auditable legal sign-off package before production go-live |

## Frontend Prioritized Queue (React.js)
Use this queue together with the global queue when planning phase implementation.

| Frontend Order | Task ID | Why Now |
| --- | --- | --- |
| FE-1 | TASK-11-14 | Closed frontend-refresh slice: public company landing page on `/` with careers navigation and branded media assets |
| FE-2 | TASK-11-15 | Closed frontend-refresh slice: split HR routes on `/hr`, `/hr/vacancies`, `/hr/pipeline`, `/hr/interviews`, `/hr/offers`, and `/hr/workbench`, plus `/manager` and `/accountant`, with role-based post-login redirects |
| FE-3 | TASK-11-16 | Closed frontend-refresh slice: refreshed visual system and branded careers upload surface with checked-in image assets |
| FE-4 | TASK-11-13 | Critical login window for local verification and daily staff workflow entry |
| FE-5 | TASK-11-01 | Mandatory React.js foundation for all user-facing flows |
| FE-6 | TASK-11-02 | Engineering baseline prevents frontend quality drift |
| FE-7 | TASK-11-03 | Security and role boundaries must be enforced in UI early |
| FE-8 | TASK-11-04 | Shared components and accessibility reduce rework |
| FE-9 | ADMIN-01 | Admin shell baseline for privileged workspace |
| FE-10 | ADMIN-02 | Staff management UI for operational onboarding |
| FE-11 | ADMIN-03 | Employee key management UI for staff registration flow |
| FE-12 | TASK-11-06 | Delivered in local baseline: public careers job board, shareable vacancy detail/apply page, tracking, and analysis read UX with `/candidate/apply` and `/candidate/interview/:interviewToken` compatibility shells behind `/candidate` |
| FE-13 | TASK-11-09 | Delivered in local baseline for login/public/company/HR critical flows |
| FE-14 | TASK-11-05 | Delivered in local baseline: staff vacancy CRUD and pipeline workspace now split across `/hr`, `/hr/vacancies`, `/hr/pipeline`, and `/hr/workbench` |
| FE-15 | TASK-11-11 | Closed frontend baseline: Chrome browser smoke for login + public candidate apply on `/candidate/apply` and the shareable careers vacancy route |
| FE-16 | TASK-11-07 | Delivered in local scoring slice: shortlist review block inside `/hr/workbench` with scoring polling and explainable payload rendering |
| FE-17 | TASK-11-10 | Closed frontend observability slice: Sentry hardening for critical routes, shared HTTP failure capture, render boundary, and release/env tracing config |
| FE-18 | TASK-11-08 | Delivered interview slice: planning-baseline scheduling on `/hr/interviews` with legacy `/hr/workbench` compatibility and token registration on `/candidate/interview/:interviewToken` without candidate auth |
| FE-19 | TASK-11-17 | Closed frontend copy-density cleanup slice for the refreshed public company, careers, candidate, and role-shell pages |

## Milestone Cut Suggestion
- `M1` (Phase 1 MVP): infra/security + ADMIN-01/02/03 + candidate CV intake/parsing/normalization + candidate self-service upload/tracking + HR vacancy/pipeline workspace baseline + RU/EN critical flows + browser smoke.
- `M2` (Immediate post-baseline slice): `TASK-04-01/02/03 + TASK-11-07` as one scoring/shortlist-review deliverable, with `TASK-13-01/02/03` proceeding immediately after or in parallel.
- `M2` planning gate: completed in `docs/project/interview-planning-pass.md`; use that document as the baseline for interview scheduling/registration implementation.
- `M3` (Phase 2 core): interview scheduling/fairness controls + offer-to-hire + onboarding workflows + phase-2 role workspace baseline.
- `M4` (Phase 2 expansion): manager/leader/accountant rollout + reporting exports + notification optimization + final legal sign-off package.
- Note: until first production launch planning starts, acceptance focus is local end-to-end operation on the current device.

## M1 Sprint Start Approval
- Date: 2026-03-04
- Approved by: coordinator, architect, business-analyst
- Scope: `M1` (tasks 1-24 + TASK-12-01 + FE-1..FE-10)
- Ownership matrix: `docs/project/sprint-m1-plan.md`
- Note: on 2026-03-09 the queue constraint that kept `TASK-11-08` planning-blocked was resolved by the dedicated planning pass and this implementation slice; further interview work must stay outside the accepted scheduling/registration scope of this change.

### M1 Owners (Grouped by TASK-*)
- architect + backend-engineer: TASK-01-01, TASK-01-02, TASK-01-03, TASK-01-04
- business-analyst + architect: TASK-01-05
- devops-engineer: TASK-12-01
- backend-engineer: TASK-03-01, TASK-02-01, TASK-02-02, TASK-02-03, TASK-05-01, TASK-05-02, TASK-05-03, TASK-05-04, TASK-08-01, TASK-08-02, TASK-08-03, TASK-08-04, TASK-10-01
- backend-engineer + data-ml-engineer: TASK-03-02, TASK-03-03, TASK-10-02
- data-ml-engineer + backend-engineer: TASK-04-01, TASK-04-02, TASK-04-03
- frontend-engineer: TASK-11-13, TASK-11-01, TASK-11-02, TASK-11-03, TASK-11-04, TASK-11-05, TASK-11-06, TASK-11-07, TASK-11-08, TASK-11-09
- qa-engineer: quality gates and test coverage for all M1 TASK-*
- devops-engineer: CI/CD and environment readiness for all M1 TASK-*
