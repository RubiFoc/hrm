# Epic Task Backlog

## Last Updated
- Date: 2026-03-05
- Updated by: coordinator

## Priority Model
- `P0`: critical for Phase 1 core delivery.
- `P1`: important for completing full business flows.
- `P2`: later optimization/expansion tasks.

## Execution Status Snapshot

| Track | Status | Evidence |
| --- | --- | --- |
| ADMIN-01 | done | Merged in `main` via PR #48 |
| ADMIN-02 | done/closed | GitHub issue #53 closed; merged in `main` via PR #51 (`bd96d86`) |
| ADMIN-03 | opened | GitHub issue #52 |

## Task Breakdown by Epic

| Task ID | Epic | Task | Phase | Priority | Depends On |
| --- | --- | --- | --- | --- | --- |
| TASK-01-01 | EPIC-01 | Define RBAC role matrix for HR, Candidate, Manager, Employee, Leader, Accountant | Phase 1 | P0 | - |
| TASK-01-02 | EPIC-01 | Implement authentication and session/token lifecycle | Phase 1 | P0 | TASK-01-01 |
| TASK-01-03 | EPIC-01 | Implement access policy middleware for API and background jobs | Phase 1 | P0 | TASK-01-02 |
| TASK-01-04 | EPIC-01 | Implement audit logging for sensitive data access | Phase 1 | P0 | TASK-01-03 |
| TASK-01-05 | EPIC-01 | Define and apply Belarus/Russia data storage and retention baseline | Phase 1 | P0 | TASK-01-01 |
| TASK-12-01 | EPIC-12 | Provision containerized platform with Docker and Docker Compose (backend, frontend, db, queue, object storage) | Phase 1 | P0 | - |
| TASK-11-01 | EPIC-11 | Initialize React.js + TypeScript frontend foundation (app shell, routing, project structure) | Phase 1 | P0 | TASK-01-01 |
| TASK-11-02 | EPIC-11 | Implement frontend engineering baseline with popular libraries (MUI, React Router, TanStack Query, React Hook Form, Zod) | Phase 1 | P0 | TASK-11-01 |
| TASK-11-03 | EPIC-11 | Implement auth-aware route guards and role-based navigation | Phase 1 | P0 | TASK-11-01, TASK-01-02 |
| TASK-11-04 | EPIC-11 | Implement shared UI component system, forms, validation, and accessibility baseline | Phase 1 | P0 | TASK-11-01 |
| TASK-11-05 | EPIC-11 | Implement HR vacancy and pipeline workspace UI | Phase 1 | P0 | TASK-11-03, TASK-02-02 |
| TASK-11-06 | EPIC-11 | Implement candidate self-service workspace UI (CV upload, profile confirmation, interview registration) | Phase 1 | P0 | TASK-11-03, TASK-03-02, TASK-05-01 |
| TASK-11-07 | EPIC-11 | Implement shortlist and match-scoring review UI with confidence visualization | Phase 1 | P0 | TASK-11-06, TASK-04-03 |
| TASK-11-08 | EPIC-11 | Implement interview scheduling UI with Google Calendar sync status | Phase 1 | P0 | TASK-11-05, TASK-11-06, TASK-05-02 |
| TASK-11-09 | EPIC-11 | Implement RU/EN localization infrastructure and translations for critical v1 flows | Phase 1 | P0 | TASK-11-02, TASK-11-05, TASK-11-06 |
| TASK-11-10 | EPIC-11 | Implement frontend observability with Sentry (error tracking, performance metrics, release markers) | Phase 1-2 | P1 | TASK-11-02 |
| TASK-11-11 | EPIC-11 | Implement Chrome compatibility checks and regression verification for critical v1 journeys | Phase 1 | P1 | TASK-11-05, TASK-11-06, TASK-11-08 |
| TASK-11-12 | EPIC-11 | Implement phase-2 role workspaces (manager, employee, accountant, leader) | Phase 2 | P1 | TASK-06-03, TASK-07-04, TASK-09-01 |
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
| TASK-03-04 | EPIC-03 | Implement candidate search and filter API for HR | Phase 1 | P1 | TASK-03-01 |
| TASK-04-01 | EPIC-04 | Implement Ollama adapter with model/version configuration | Phase 1 | P0 | TASK-03-03 |
| TASK-04-02 | EPIC-04 | Implement async match scoring pipeline (queue + worker) | Phase 1 | P0 | TASK-04-01 |
| TASK-04-03 | EPIC-04 | Implement score schema with confidence and explanation fields | Phase 1 | P0 | TASK-04-02 |
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
| 8 | TASK-03-01 | Candidate domain base model |
| 9 | TASK-02-01 | Vacancy base model for recruiting flow |
| 10 | TASK-02-02 | Pipeline states for lifecycle control |
| 11 | TASK-03-02 | CV intake needed for AI scoring |
| 12 | TASK-03-03 | Parsed CV status for asynchronous processing |
| 13 | TASK-04-01 | Mandatory integration with Ollama |
| 14 | TASK-04-02 | Actual scoring engine execution |
| 15 | TASK-04-03 | Explainable and reliable scoring output |
| 16 | TASK-02-03 | Timeline/history for recruiting decisions |
| 17 | TASK-05-01 | Interview orchestration start point |
| 18 | TASK-05-02 | Mandatory Google Calendar integration |
| 19 | TASK-05-03 | Structured interview quality control |
| 20 | TASK-05-04 | Fairness gate before hiring decision |
| 21 | TASK-08-01 | Start automation to hit KPI target |
| 22 | TASK-08-02 | Reliable automation execution |
| 23 | TASK-08-03 | Operational support and troubleshooting |
| 24 | TASK-08-04 | Automation KPI telemetry |
| 25 | TASK-10-01 | KPI data layer foundation |
| 26 | TASK-10-02 | Automation KPI report for target tracking |
| 27 | TASK-01-04 | Complete auditability of sensitive actions |
| 28 | TASK-03-04 | HR productivity via candidate filtering |
| 29 | TASK-04-04 | Human fallback for low AI confidence |
| 30 | TASK-02-04 | Manager visibility enrichment |
| 31 | TASK-06-01 | Offer lifecycle for conversion to employees |
| 32 | TASK-06-02 | Candidate to employee state transition |
| 33 | TASK-06-03 | Employee profile initialization |
| 34 | TASK-06-04 | Onboarding flow trigger |
| 35 | TASK-07-01 | Onboarding template baseline |
| 36 | TASK-07-02 | Task execution tracking |
| 37 | TASK-07-03 | Employee self-service onboarding |
| 38 | TASK-07-04 | HR/manager onboarding control |
| 39 | TASK-10-03 | Compliance and audit read interfaces |
| 40 | TASK-09-01 | Manager workspace full rollout |
| 41 | TASK-09-03 | Accountant workspace rollout |
| 42 | TASK-10-04 | Reporting export package |
| 43 | TASK-09-02 | Leader workspace finalization |
| 44 | TASK-09-04 | Notification optimization |

## Frontend Prioritized Queue (React.js)
Use this queue together with the global queue when planning phase implementation.

| Frontend Order | Task ID | Why Now |
| --- | --- | --- |
| FE-1 | TASK-11-01 | Mandatory React.js foundation for all user-facing flows |
| FE-2 | TASK-11-02 | Engineering baseline prevents frontend quality drift |
| FE-3 | TASK-11-03 | Security and role boundaries must be enforced in UI early |
| FE-4 | TASK-11-04 | Shared components and accessibility reduce rework |
| FE-5 | TASK-11-05 | HR vacancy/pipeline is core phase-1 business flow |
| FE-6 | TASK-11-06 | Candidate self-service journey is required for v1 scope |
| FE-7 | TASK-11-07 | Match review UI is required to operationalize AI scoring |
| FE-8 | TASK-11-08 | Interview scheduling UI closes recruitment loop |
| FE-9 | TASK-11-09 | RU/EN localization is a fixed v1 requirement |
| FE-10 | TASK-11-10 | Sentry observability needed for reliable production support |
| FE-11 | TASK-11-11 | Chrome compatibility gate for v1 rollout |
| FE-12 | TASK-11-12 | Phase-2 role workspace rollout |
| FE-13 | ADMIN-01 | Admin shell baseline for privileged workspace |
| FE-14 | ADMIN-02 | Staff management UI for operational onboarding |
| FE-15 | ADMIN-03 | Employee key management UI for staff registration flow |
| FE-16 | ADMIN-04 | Unified admin CRUD consoles |
| FE-17 | ADMIN-05 | Admin observability and audit dashboards |

## Milestone Cut Suggestion
- `M1` (Phase 1 MVP): tasks 1-24 + TASK-12-01 + FE-1..FE-9.
- `M2` (Phase 1 hardening): tasks 25-27 + FE-10..FE-11.
- `M3` (Phase 2 core): tasks 28-36 + FE-12.
- `M4` (Phase 2 expansion): tasks 37-41.

## M1 Sprint Start Approval
- Date: 2026-03-04
- Approved by: coordinator, architect, business-analyst
- Scope: `M1` (tasks 1-24 + TASK-12-01 + FE-1..FE-9)
- Ownership matrix: `docs/project/sprint-m1-plan.md`

### M1 Owners (Grouped by TASK-*)
- architect + backend-engineer: TASK-01-01, TASK-01-02, TASK-01-03, TASK-01-04
- business-analyst + architect: TASK-01-05
- devops-engineer: TASK-12-01
- backend-engineer: TASK-03-01, TASK-02-01, TASK-02-02, TASK-02-03, TASK-05-01, TASK-05-02, TASK-05-03, TASK-05-04, TASK-08-01, TASK-08-02, TASK-08-03, TASK-08-04, TASK-10-01
- backend-engineer + data-ml-engineer: TASK-03-02, TASK-03-03, TASK-10-02
- data-ml-engineer + backend-engineer: TASK-04-01, TASK-04-02, TASK-04-03
- frontend-engineer: TASK-11-01, TASK-11-02, TASK-11-03, TASK-11-04, TASK-11-05, TASK-11-06, TASK-11-07, TASK-11-08, TASK-11-09
- qa-engineer: quality gates and test coverage for all M1 TASK-*
- devops-engineer: CI/CD and environment readiness for all M1 TASK-*
