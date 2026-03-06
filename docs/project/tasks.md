# Epic Task Backlog

## Last Updated
- Date: 2026-03-06
- Updated by: coordinator + frontend-engineer

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
| TASK-11-13 | planned | GitHub issue #67 opened with `P0` priority for login UX unblocking |
| COMPLIANCE-01 | planned | EPIC-13 article-level legal mapping and evidence pack track |

## Task Breakdown by Epic

| Task ID | Epic | Task | Phase | Priority | Depends On |
| --- | --- | --- | --- | --- | --- |
| TASK-01-01 | EPIC-01 | Define RBAC role matrix for HR, Candidate, Manager, Employee, Leader, Accountant | Phase 1 | P0 | - |
| TASK-01-02 | EPIC-01 | Implement authentication and session/token lifecycle | Phase 1 | P0 | TASK-01-01 |
| TASK-01-03 | EPIC-01 | Implement access policy middleware for API and background jobs | Phase 1 | P0 | TASK-01-02 |
| TASK-01-04 | EPIC-01 | Implement audit logging for sensitive data access | Phase 1 | P0 | TASK-01-03 |
| TASK-01-05 | EPIC-01 | Define and apply Belarus/Russia data storage and retention baseline | Phase 1 | P0 | TASK-01-01 |
| TASK-13-01 | EPIC-13 | Map article-level Belarus/Russia legal obligations to controls in legal-controls matrix | Phase 1 | P0 | TASK-01-05 |
| TASK-13-02 | EPIC-13 | Define evidence registry and ownership model for each critical legal control | Phase 1 | P0 | TASK-13-01 |
| TASK-13-03 | EPIC-13 | Add release-gate compliance checklist for critical controls and legal sign-off preconditions | Phase 1-2 | P1 | TASK-13-02 |
| TASK-13-04 | EPIC-13 | Prepare production legal evidence package and sign-off workflow | Phase 2 | P1 | TASK-13-03 |
| TASK-12-01 | EPIC-12 | Provision containerized platform with Docker and Docker Compose (backend, frontend, db, queue, object storage) | Phase 1 | P0 | - |
| TASK-11-01 | EPIC-11 | Initialize React.js + TypeScript frontend foundation (app shell, routing, project structure) | Phase 1 | P0 | TASK-01-01 |
| TASK-11-02 | EPIC-11 | Implement frontend engineering baseline with popular libraries (MUI, React Router, TanStack Query, React Hook Form, Zod) | Phase 1 | P0 | TASK-11-01 |
| TASK-11-03 | EPIC-11 | Implement auth-aware route guards and role-based navigation | Phase 1 | P0 | TASK-11-01, TASK-01-02 |
| TASK-11-04 | EPIC-11 | Implement shared UI component system, forms, validation, and accessibility baseline | Phase 1 | P0 | TASK-11-01 |
| TASK-11-05 | EPIC-11 | Implement HR vacancy and pipeline workspace UI (after candidate intake baseline) | Phase 1 | P0 | TASK-11-03, TASK-02-02 |
| TASK-11-06 | EPIC-11 | Implement candidate self-service workspace UI (CV upload, profile confirmation) | Phase 1 | P0 | TASK-11-03, TASK-03-02 |
| TASK-11-07 | EPIC-11 | Implement shortlist and match-scoring review UI with confidence visualization | Phase 1 | P0 | TASK-11-06, TASK-04-03 |
| TASK-11-08 | EPIC-11 | Implement interview scheduling and candidate interview-registration UI with Google Calendar sync status | Phase 1 | P0 | TASK-11-05, TASK-11-06, TASK-05-02 |
| TASK-11-09 | EPIC-11 | Implement RU/EN localization infrastructure and translations for critical v1 flows | Phase 1 | P0 | TASK-11-02, TASK-11-05, TASK-11-06 |
| TASK-11-10 | EPIC-11 | Implement frontend observability with Sentry (error tracking, performance metrics, release markers) | Phase 1-2 | P1 | TASK-11-02 |
| TASK-11-11 | EPIC-11 | Implement Chrome compatibility checks and regression verification for critical v1 journeys | Phase 1 | P1 | TASK-11-05, TASK-11-06, TASK-11-08 |
| TASK-11-12 | EPIC-11 | Implement phase-2 role workspaces (manager, employee, accountant, leader) | Phase 2 | P1 | TASK-06-03, TASK-07-04, TASK-09-01 |
| TASK-11-13 | EPIC-11 | Implement staff login window and session bootstrap UX | Phase 1 | P0 | TASK-01-02, TASK-11-03 |
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
| TASK-03-04 | EPIC-03 | Implement candidate search and filter API for HR | Phase 1 | P1 | TASK-03-01 |
| TASK-04-01 | EPIC-04 | Implement Ollama adapter with model/version configuration | Phase 1 | P0 | TASK-03-03 |
| TASK-04-02 | EPIC-04 | Implement async match scoring pipeline (queue + worker) | Phase 1 | P0 | TASK-04-01 |
| TASK-04-03 | EPIC-04 | Implement score schema with confidence and explanation fields | Phase 1 | P0 | TASK-04-02 |
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
| TASK-07-01 | EPIC-07 | Implement onboarding checklist template management | Phase 2 | P1 | TASK-06-04 |
| TASK-07-02 | EPIC-07 | Implement onboarding task assignment and SLA tracking | Phase 2 | P1 | TASK-07-01 |
| TASK-07-03 | EPIC-07 | Implement employee onboarding task portal | Phase 2 | P1 | TASK-07-02 |
| TASK-07-04 | EPIC-07 | Implement HR/manager onboarding progress dashboard | Phase 2 | P1 | TASK-07-03 |
| TASK-09-01 | EPIC-09 | Implement manager workspace for team hiring/onboarding visibility | Phase 2 | P1 | TASK-07-04 |
| TASK-09-02 | EPIC-09 | Implement leader workspace for KPI and operational overview | Phase 2 | P1 | TASK-10-02 |
| TASK-09-03 | EPIC-09 | Implement accountant workspace with controlled export access | Phase 2 | P1 | TASK-06-03 |
| TASK-09-04 | EPIC-09 | Implement role-specific notifications and summary digests | Phase 2 | P2 | TASK-09-01 |
| TASK-10-01 | EPIC-10 | Implement KPI data model and aggregation pipeline | Phase 1-2 | P0 | TASK-08-04 |
| TASK-10-02 | EPIC-10 | Implement monthly automation KPI snapshot and dashboard | Phase 1-2 | P0 | TASK-10-01 |
| TASK-10-03 | EPIC-10 | Implement audit query API and compliance evidence view | Phase 1-2 | P1 | TASK-01-04 |
| TASK-10-04 | EPIC-10 | Implement export package for audits and management reporting | Phase 2 | P1 | TASK-10-02, TASK-10-03 |

## Global Prioritized Queue

| Order | Task ID | Why Now |
| --- | --- | --- |
| 0 | TASK-12-01 | Highest priority to standardize local/dev/runtime environment and unblock parallel delivery |
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
| 30 | TASK-08-04 | Automation KPI telemetry |
| 31 | TASK-10-01 | KPI data layer foundation |
| 32 | TASK-10-02 | Automation KPI report for target tracking |
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
| FE-1 | TASK-11-13 | Critical login window for local verification and daily staff workflow entry |
| FE-2 | TASK-11-01 | Mandatory React.js foundation for all user-facing flows |
| FE-3 | TASK-11-02 | Engineering baseline prevents frontend quality drift |
| FE-4 | TASK-11-03 | Security and role boundaries must be enforced in UI early |
| FE-5 | TASK-11-04 | Shared components and accessibility reduce rework |
| FE-6 | ADMIN-01 | Admin shell baseline for privileged workspace |
| FE-7 | ADMIN-02 | Staff management UI for operational onboarding |
| FE-8 | ADMIN-03 | Employee key management UI for staff registration flow |
| FE-9 | TASK-11-06 | Candidate self-service CV upload must be available before HR workspace |
| FE-10 | TASK-11-09 | RU/EN localization for candidate/admin critical flows |
| FE-11 | TASK-11-07 | Match review UI for explainable scoring rollout |
| FE-12 | TASK-11-05 | HR vacancy/pipeline workspace after candidate baseline |
| FE-13 | TASK-11-08 | Interview scheduling and registration UI |
| FE-14 | TASK-11-10 | Sentry observability needed for reliable production support |
| FE-15 | TASK-11-11 | Chrome compatibility gate for v1 rollout |
| FE-16 | ADMIN-04 | Unified admin CRUD consoles |
| FE-17 | ADMIN-05 | Admin observability and audit dashboards |
| FE-18 | TASK-11-12 | Phase-2 role workspace rollout |

## Milestone Cut Suggestion
- `M1` (Phase 1 MVP): infra/security + ADMIN-01/02/03 + candidate CV intake/parsing/normalization + candidate self-service upload.
- `M2` (Phase 1 hardening): explainable scoring quality harness + HR module (vacancy/pipeline) + interview scheduling + localization/observability hardening + compliance release-gate checklist.
- `M3` (Phase 2 core): offer-to-hire + onboarding workflows + phase-2 role workspace baseline.
- `M4` (Phase 2 expansion): manager/leader/accountant rollout + reporting exports + notification optimization + final legal sign-off package.
- Note: until first production launch planning starts, acceptance focus is local end-to-end operation on the current device.

## M1 Sprint Start Approval
- Date: 2026-03-04
- Approved by: coordinator, architect, business-analyst
- Scope: `M1` (tasks 1-24 + TASK-12-01 + FE-1..FE-10)
- Ownership matrix: `docs/project/sprint-m1-plan.md`
- Note: on 2026-03-06 backlog priority was refined to admin -> candidate CV intake -> HR module; active planning should follow the updated global/frontend queues above.

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
