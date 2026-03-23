# Architecture Decisions

Use this log for decisions that change interfaces, data models, deployment topology, or operational risk.

## Decision Log
| ID | Date | Status | Title | Owner | Impacted Areas |
| --- | --- | --- | --- | --- | --- |
| ADR-0001 | 2026-03-03 | accepted | Establish documentation-first LLM workflow | architect | docs, process |
| ADR-0002 | 2026-03-03 | accepted | Adopt modular monolith with phased domain rollout | architect | architecture, delivery |
| ADR-0003 | 2026-03-03 | accepted | Make diagrams and best-practice checks mandatory | architect | architecture, engineering process |
| ADR-0004 | 2026-03-03 | accepted | Standardize frontend stack on React.js + TypeScript | architect | frontend architecture, delivery |
| ADR-0005 | 2026-03-04 | accepted | Standardize local platform runtime on Docker Compose | architect | infra, operations, developer experience |
| ADR-0006 | 2026-03-04 | accepted | Adopt signed access tokens with rotating refresh sessions for MVP auth | architect + backend-engineer | backend security, RBAC integration |
| ADR-0007 | 2026-03-04 | accepted | Adopt stateless JWT auth with Redis denylist and fail-closed policy | architect + backend-engineer | backend security, auth runtime |
| ADR-0008 | 2026-03-04 | accepted | Introduce shared backend `core` package for cross-domain primitives | architect + backend-engineer | backend architecture, maintainability |
| ADR-0009 | 2026-03-04 | accepted | Centralize RBAC evaluation for API/background paths and add immutable audit events | architect + backend-engineer | backend security, compliance evidence, observability |
| ADR-0010 | 2026-03-04 | accepted | Model candidate profile as typed core fields plus JSONB extension and backend multipart CV upload | architect + backend-engineer | recruitment domain, object storage, API contracts |
| ADR-0011 | 2026-03-04 | accepted | Use append-only pipeline transitions with strict canonical stage graph | architect + backend-engineer | recruitment domain, workflow integrity, auditability |
| ADR-0012 | 2026-03-04 | accepted | Implement DB-backed asynchronous CV parsing jobs with retry-safe worker lifecycle | architect + backend-engineer | recruitment domain, async processing, operations |
| ADR-0013 | 2026-03-04 | accepted | Move to staff-only password authentication with employee registration keys and `admin` role | architect + backend-engineer | auth, RBAC, API contracts |
| ADR-0014 | 2026-03-04 | accepted | Replace candidate auth flow with public vacancy application endpoint | architect + backend-engineer | recruitment API, RBAC, audit model |
| ADR-0015 | 2026-03-04 | accepted | Use Celery as execution engine for CV parsing with DB job table as source of truth | architect + backend-engineer | async runtime, operations, reliability |
| ADR-0016 | 2026-03-04 | accepted | Remove legacy auth login payload and temporary settings compatibility shims | architect + backend-engineer | auth API contract, backend shared config imports |
| ADR-0017 | 2026-03-05 | accepted | Add layered anti-abuse controls for public vacancy application endpoint | architect + backend-engineer | recruitment API, observability, operations |
| ADR-0018 | 2026-03-05 | accepted | Normalize API ID contracts to UUID at boundary level | architect + backend-engineer | candidate/vacancy/pipeline contracts, OpenAPI |
| ADR-0019 | 2026-03-05 | accepted | Freeze OpenAPI contract and enforce drift checks in CI | architect + backend-engineer | API governance, CI/CD, frontend integration |
| ADR-0020 | 2026-03-05 | accepted | Introduce ADMIN-01 frontend route guard and admin shell with Sentry tags | architect + frontend-engineer | frontend routing, access control UX, observability |
| ADR-0021 | 2026-03-05 | accepted | Add ADMIN-02 staff management list/update APIs with strict admin safety guard | architect + backend-engineer + frontend-engineer | admin API contracts, RBAC, audit trail, frontend admin workspace |
| ADR-0022 | 2026-03-05 | accepted | Extract admin governance flows into dedicated `admin` backend package | architect + backend-engineer | backend package boundaries, maintainability, test topology |
| ADR-0023 | 2026-03-05 | accepted | Add ADMIN-03 employee registration key lifecycle management (list/revoke + admin UI) | architect + backend-engineer + frontend-engineer | admin API contracts, auth key lifecycle, RBAC, audit trail, frontend admin workspace |
| ADR-0024 | 2026-03-06 | accepted | Persist RU/EN-normalized CV analysis with evidence traceability and expose analysis API | architect + backend-engineer + frontend-engineer | candidate domain model, parsing pipeline, API contract, frontend candidate workspace |
| ADR-0025 | 2026-03-06 | accepted | Track public candidate parsing by job ID and make browser smoke validate the full Phase 1 intake baseline | architect + backend-engineer + frontend-engineer | candidate workflow, compose runtime, browser verification, API contract |
| ADR-0026 | 2026-03-09 | accepted | Land the Phase 1 baseline as one PR and make scoring the next vertical slice | architect + backend-engineer + frontend-engineer | delivery sequencing, scoring package boundary, API contracts, testing scope |
| ADR-0027 | 2026-03-09 | accepted | Implement scoring as a dedicated backend package with DB-backed jobs/artifacts and shortlist review on `/` | architect + backend-engineer + frontend-engineer | scoring architecture, HR workspace UX, compose worker topology, OpenAPI contract |
| ADR-0028 | 2026-03-09 | accepted | Harden frontend observability with canonical Sentry route tags and shared failure capture | architect + frontend-engineer | frontend observability, route semantics, error telemetry |
| ADR-0029 | 2026-03-09 | accepted | Freeze interview scheduling and candidate registration as a public-token workflow on existing routes | architect + backend-engineer + frontend-engineer | interview product rules, public token model, Google Calendar sync semantics, route topology |
| ADR-0030 | 2026-03-10 | accepted | Freeze interviewer feedback as schedule-versioned interview data and enforce fairness gate on the existing `interview -> offer` transition | architect + backend-engineer + frontend-engineer | interview feedback data model, HR workspace UX, pipeline transition semantics, OpenAPI contract |
| ADR-0031 | 2026-03-10 | accepted | Persist durable `hire_conversion` handoff on the existing `offer -> hired` transition | architect + backend-engineer | employee domain boundary, pipeline transition semantics, employee bootstrap sequencing |
| ADR-0032 | 2026-03-10 | accepted | Bootstrap employee profiles from durable `hire_conversions` on a dedicated staff API | architect + backend-engineer | employee API contract, route topology, RBAC, onboarding sequencing |
| ADR-0033 | 2026-03-10 | accepted | Trigger onboarding atomically on successful employee profile bootstrap | architect + backend-engineer | employee bootstrap transaction boundary, onboarding persistence, employee API contract |
| ADR-0034 | 2026-03-10 | accepted | Manage onboarding checklist templates on a dedicated staff onboarding API | architect + backend-engineer | onboarding template data model, route topology, RBAC, later task generation |
| ADR-0035 | 2026-03-11 | accepted | Materialize onboarding tasks from the active template and keep staff operations on onboarding runs | architect + backend-engineer | onboarding task data model, bootstrap transaction boundary, RBAC, API contract |
| ADR-0036 | 2026-03-11 | accepted | Expose employee self-service onboarding on `/employee` with durable profile identity linking | architect + backend-engineer + frontend-engineer | employee auth-to-profile mapping, self-service API contract, frontend route topology, RBAC |
| ADR-0037 | 2026-03-11 | accepted | Expose onboarding progress dashboards on the existing `/` route and keep manager visibility read-only and assignment-scoped | architect + backend-engineer + frontend-engineer | onboarding progress read model, manager visibility policy, frontend route topology, RBAC |
| ADR-0038 | 2026-03-11 | accepted | Perform native PDF/DOCX text extraction before CV normalization while keeping parsing and scoring contracts stable | architect + backend-engineer | candidate parsing pipeline, evidence traceability, worker/runtime dependencies, scoring preconditions |
| ADR-0039 | 2026-03-11 | accepted | Enrich parsed CV profiles with profession-agnostic workplaces, held positions, education, normalized titles/dates, and generic skills | architect + backend-engineer | candidate parsing pipeline, parsed-profile semantics, evidence mapping, product framing |
| ADR-0040 | 2026-03-12 | accepted | Keep default Ollama runtime external-host compatible while adding an opt-in compose-local `ai-local` profile and separate scoring smoke | architect + backend-engineer | compose topology, scoring runtime, operator verification |
| ADR-0041 | 2026-03-12 | accepted | Introduce explicit vacancy ownership and dedicated manager workspace reads on `/` | architect + backend-engineer + frontend-engineer | manager workspace visibility policy, vacancy ownership signal, frontend route semantics |
| ADR-0042 | 2026-03-13 | accepted | Add accountant workspace + dual-format controlled export as a thin finance adapter over onboarding data | architect + backend-engineer + frontend-engineer | finance adapter boundary, controlled exports, frontend route semantics, observability |
| ADR-0043 | 2026-03-13 | accepted | Add recipient-scoped in-app notifications and on-demand digests for manager/accountant workspaces | architect + backend-engineer + frontend-engineer | notification package boundary, recipient visibility policy, frontend embedded workspaces, OpenAPI contract |
| ADR-0044 | 2026-03-13 | accepted | Introduce monthly KPI snapshot foundation with on-demand rebuild | architect + backend-engineer | reporting package, KPI data model, analytics access policy |
| ADR-0045 | 2026-03-13 | accepted | Expose KPI snapshot reads to leaders while keeping rebuild admin-only | architect + backend-engineer | reporting access policy, RBAC, API read surface |
| ADR-0046 | 2026-03-13 | accepted | Add admin-only audit evidence query API over append-only `audit_events` | architect + backend-engineer | audit package read surface, RBAC, operations/runbook, OpenAPI contract |
| ADR-0047 | 2026-03-16 | accepted | Add controlled audit + KPI snapshot export attachments (bounded, no new jobs/tables) | architect + backend-engineer | audit/reporting exports, API contracts, compliance evidence |
| ADR-0048 | 2026-03-16 | accepted | Introduce automation rule model and deterministic trigger evaluator (planning only) | architect + backend-engineer | automation package boundary, domain seams, RBAC, OpenAPI contract |
| ADR-0049 | 2026-03-16 | accepted | Execute automation `notification.emit` actions via idempotent in-app notification executor | architect + backend-engineer | automation execution semantics, notification persistence, fail-closed guarantees |
| ADR-0050 | 2026-03-16 | accepted | Add durable automation execution logs and ops read APIs (non-PII) | architect + backend-engineer | automation observability, DB schema, ops API, RBAC |
| ADR-0051 | 2026-03-19 | accepted | Add durable automation KPI metric events and monthly share aggregation | architect + backend-engineer | automation reporting, KPI aggregation, leader workspace, OpenAPI contract |
| ADR-0052 | 2026-03-19 | accepted | Deliver ADMIN-04 as a frontend-first admin control-plane slice over existing recruitment and audit contracts | architect + backend-engineer + frontend-engineer | frontend admin route topology, route tags, audit export UX, compliance-safe control plane |
| ADR-0053 | 2026-03-19 | accepted | Add read-only admin observability dashboard on existing `/admin/observability` route | architect + frontend-engineer | frontend admin UX, observability, support operations |
| ADR-0054 | 2026-03-19 | accepted | Reopen frontend route topology for public company landing, careers, and dedicated role pages | architect + frontend-engineer | frontend routing, public UX, observability, design system |
| ADR-0055 | 2026-03-20 | accepted | Split the HR workspace into focused nested routes while preserving the legacy workbench | architect + frontend-engineer | frontend routing, HR workspace UX, route tags, documentation |
| ADR-0056 | 2026-03-20 | accepted | Add a public vacancy board endpoint for careers while keeping the guided apply flow on `/careers` | architect + frontend-engineer | recruitment API, public careers UX, OpenAPI contract, frontend typed client |
| ADR-0057 | 2026-03-20 | accepted | Split public careers into board and shareable vacancy detail routes | architect + frontend-engineer | frontend routing, public careers UX, smoke verification, route tags |
| ADR-0058 | 2026-03-20 | accepted | Split public candidate transport into dedicated apply and interview routes with `/candidate` compatibility redirects | architect + frontend-engineer | frontend routing, public candidate UX, observability, browser smoke, documentation |
| ADR-0059 | 2026-03-23 | accepted | De-scope Russia jurisdiction and keep Belarus-only compliance scope | coordinator | compliance scope, legal controls, release gate |

## ADR-0059
- Context: The project is delivered from a Belarus-local environment and will not operate a dedicated Russia service.
- Decision: Remove Russia jurisdiction requirements from the compliance baseline and keep Belarus-only legal scope for the current product stage.
- Consequences:
  - Russia-specific controls, evidence, and release-gate blockers are removed from the compliance docs.
  - Belarus controls remain the only compliance scope and continue to govern release gating.
  - If Russia scope is reintroduced later, a new ADR and refreshed legal controls matrix will be required.
## ADR-0001
- Context: Project is at bootstrap stage and lacks durable knowledge artifacts.
- Decision: Standardize docs structure under `docs/`, enforce updates per task, and keep agent workflow under `.ai/`.
- Consequences: Slight overhead per change, significantly lower context loss and easier LLM onboarding.

## ADR-0002
- Context: The product has broad v1 scope, multiple role groups, and mandatory integrations (Ollama, Google Calendar), while delivery should start quickly and remain maintainable.
- Decision: Start with a modular monolith architecture using clear domain modules and async workers, then deliver by phases:
  1. HR + Candidates
  2. Managers + Employees + Accountants + Leaders
- Consequences:
  - Faster initial delivery and lower operational complexity than early microservices.
  - Strong need for strict module boundaries and interface contracts to avoid monolith coupling.
  - Clear extraction path for high-load or high-volatility services in later stages.

## ADR-0003
- Context: Architecture knowledge can drift from implementation when diagrams and engineering standards are optional.
- Decision:
  - Maintain a canonical diagram set in `docs/architecture/diagrams.md`.
  - Require diagram updates for architecture/data-flow/critical workflow changes.
  - Require best-practice checks from `docs/engineering/best-practices.md` in every development task.
  - Require architect sign-off for architecture-level changes.
- Consequences:
  - Better alignment between architecture intent and implementation.
  - Slight documentation overhead per task.
  - Higher consistency and maintainability for LLM-assisted development.

## ADR-0004
- Context: The product requires rapid delivery across multiple role workspaces while maintaining maintainable frontend patterns.
- Decision:
  - Use React.js + TypeScript as mandatory frontend technology baseline.
  - Use popular ready-made frontend libraries for UI and application scaffolding.
  - Support RU/EN localization in v1.
  - Use Google Chrome as the v1 browser support target.
  - Use Sentry for frontend monitoring and error telemetry.
  - Keep mobile app out of scope; ship responsive web only.
  - Manage frontend requirements in `docs/project/frontend-requirements.md`.
  - Add dedicated frontend epic/tasks with priority in delivery planning.
- Consequences:
  - Consistent frontend architecture and faster onboarding for contributors.
  - Reduced technology fragmentation risk.
  - Frontend stack changes require explicit ADR review.

## ADR-0005
- Context: The project needs a deterministic local runtime that aligns backend, frontend, and mandatory infrastructure dependencies for rapid parallel delivery.
- Decision:
  - Use Docker Compose as the default local platform runtime.
  - Provide containerized services for backend, frontend, PostgreSQL, Redis queue, and MinIO object storage.
  - Keep environment configuration centralized via `.env.example` and runtime `.env`.
  - Require runbook and diagram updates when compose topology changes.
- Consequences:
  - Faster onboarding and fewer environment drift issues.
- Higher confidence for shared smoke checks and incident triage.
- Added maintenance responsibility for container image and compose configuration.

## ADR-0006
- Status note: superseded by ADR-0007 for final auth storage model.
- Context: `TASK-01-02` requires replacing header-based role input with authenticated identity claims and defining token/session lifecycle for Phase 1.
- Decision:
  - Use signed short-lived bearer access tokens for API authorization.
  - Use rotating refresh tokens bound to server-side session records.
  - Enforce session revocation via logout and reject revoked/expired sessions during bearer validation.
  - Keep session storage in-memory for MVP bootstrap; plan migration to persistent shared storage before production.
- Consequences:
  - RBAC enforcement now relies on validated token claims instead of request headers.
  - Security baseline improves (refresh replay prevention, explicit session revocation).
  - Current implementation is not horizontally scalable until session store is externalized.

## ADR-0007
- Context: Project requires stateless JWT model where valid tokens are not persisted server-side, while revocation and rotation safety must remain enforceable.
- Decision:
  - Use PyJWT for both access and refresh tokens (`HS256`).
  - Keep storage stateless for valid tokens; persist only denied identifiers in Redis.
  - Use denylist keys for token id (`jti`) and session id (`sid`).
  - Keep mandatory refresh rotation by denylisting old refresh `jti` until token expiration.
  - On logout, denylist current access `jti` and session `sid` for refresh-window duration.
  - Apply fail-closed behavior: deny auth validation when Redis denylist is unavailable.
- Consequences:
  - Stateless token model aligns with JWT architecture goals.
  - Redis availability becomes a hard dependency for auth checks under fail-closed policy.
  - Revocation and replay protection remain enforceable without storing active sessions.

## ADR-0008
- Context: Domain packages need extraction-friendly boundaries, but some technical primitives (ORM base, env parsers, shared HTTP errors, time helpers) are reused across domains and should not be duplicated.
- Decision:
  - Create shared backend package `hrm_backend/core`.
  - Keep cross-domain primitives in `core` (`models`, `config`, `errors`, `utils`).
  - Domain packages import shared primitives from `core` and keep only domain-specific logic locally.
  - Use temporary compatibility re-exports where needed to avoid breaking imports during transition.
- Consequences:
  - Lower duplication and simpler onboarding for new domains.
  - Clearer separation between domain logic and shared technical foundation.
  - Requires review discipline to keep domain-specific business logic out of `core`.

## ADR-0009
- Context: `TASK-01-03` and `TASK-01-04` require one enforcement policy path for API and background operations, plus immutable evidence for sensitive auth/access actions.
- Decision:
  - Introduce centralized RBAC evaluator interface:
    - `PolicyDecision`
    - `evaluate_permission(role, permission)`
    - `enforce_background_permission(...)`
    - keep `require_permission(...)` as FastAPI compatibility wrapper.
  - Persist audit events in PostgreSQL append-only table `audit_events` with migration-managed schema.
  - Record audit events for:
    - auth sensitive operations (`login`, `refresh`, `logout`, `me`);
    - RBAC decisions on both API (`source=api`) and background (`source=job`) paths.
  - Propagate request correlation ID (`X-Request-ID`) through middleware and persist as `correlation_id` in audit storage.
- Consequences:
  - API and background paths use the same policy semantics and permission matrix.
  - Security/compliance evidence is queryable and immutable at storage contract level.
  - Additional write load and storage growth from audit events must be managed by retention/archival policy.

## ADR-0010
- Context: `TASK-03-01` and `TASK-03-02` require candidate profile CRUD with extensible schema plus secure CV upload into MinIO.
- Decision:
  - Add table `candidate_profiles` with typed core fields:
    `first_name`, `last_name`, `email`, `phone`, `location`, `current_title`,
    and extensible `extra_data` (`JSONB`).
  - Add table `candidate_documents` for CV metadata and active-document linkage.
  - Keep CV ingestion mode as `multipart/form-data` through backend API.
  - Validate CV upload by MIME, max size, and SHA-256 checksum before object write.
  - Persist CV binaries in MinIO bucket and keep metadata in PostgreSQL.
- Consequences:
  - Candidate profile model supports stable typed querying without blocking future schema extensions.
  - Backend remains enforcement point for RBAC, ownership, and upload validation.
  - Object storage keys become critical references and must stay consistent with DB metadata rows.

## ADR-0011
- Context: `TASK-02-01` and `TASK-02-02` need vacancy CRUD and deterministic candidate pipeline progression.
- Decision:
  - Add table `vacancies` for vacancy lifecycle state.
  - Add append-only table `pipeline_transitions` to store candidate stage history.
  - Enforce strict canonical transition graph:
    `None -> applied -> screening -> shortlist -> interview -> offer -> (hired|rejected)`.
  - Derive current stage from latest append-only transition event for `(vacancy_id, candidate_id)`.
- Consequences:
  - Transition history is immutable and auditable.
  - Invalid or skipped states are blocked consistently by one validator.
  - Additional read step is required to resolve current stage before each new transition.

## ADR-0012
- Context: `TASK-03-03` requires asynchronous CV parsing with explicit lifecycle and retry-safe behavior.
- Decision:
  - Add table `cv_parsing_jobs` with lifecycle states:
    `queued`, `running`, `succeeded`, `failed`.
  - On each CV upload, enqueue one parsing job linked to document metadata.
  - Keep processing outside request thread and persist status transitions atomically.
  - Retries are bounded by `CV_PARSING_MAX_ATTEMPTS`; terminal `succeeded` jobs are never reprocessed.
  - Expose current parsing status via candidate API endpoint.
- Consequences:
  - Heavy parsing work is decoupled from API latency path.
  - Operational visibility improves through explicit job table state and failure reasons.
  - Runtime needs dedicated worker process and queue configuration.

## ADR-0013
- Context: passwordless `subject_id/role` login was insufficient for production-like staff identity controls and did not support controlled employee onboarding.
- Decision:
  - Introduce staff account model (`staff_accounts`) with `login`, `email`, `password_hash`, role, and active flag.
  - Use Argon2id for password hashing and enforce baseline password policy.
  - Add one-time employee registration keys (`employee_registration_keys`) with TTL and single-use semantics.
  - Add role `admin` with full platform CRUD and manual CLI bootstrap for first admin.
  - Keep JWT `sub/sid/jti` as UUID values.
- Consequences:
  - Staff identity lifecycle becomes auditable and centrally managed.
  - Registration/login contracts are changed and require client updates.
  - Legacy compatibility layer is removed in ADR-0016.

## ADR-0014
- Context: candidate role-based authentication was removed from backend scope; candidates should be able to apply without account creation.
- Decision:
  - Remove `candidate` from RBAC role matrix and auth flows.
  - Add anonymous endpoint `POST /api/v1/vacancies/{vacancy_id}/applications` with multipart CV submission.
  - Public apply flow creates/updates candidate profile, stores CV metadata/object, appends `None -> applied` transition, and enqueues parsing job.
  - Persist audit events for public flow with technical/null actor identity and correlation id.
- Consequences:
  - Candidate intake UX becomes simpler and does not depend on auth session state.
  - Staff-only endpoints remain protected by RBAC and ownership policy.
  - Increased need for abuse controls/rate limiting on public apply path.

## ADR-0015
- Context: polling loop worker model created operational drift and lacked standardized queue execution controls.
- Decision:
  - Use Celery with Redis broker/result backend for CV parsing execution.
  - Keep `cv_parsing_jobs` table as source of truth for job status lifecycle.
  - Enqueue by `job_id`; task claims DB job (`queued/failed -> running`) and writes terminal `succeeded/failed`.
  - Keep retry-safe behavior bounded by `CV_PARSING_MAX_ATTEMPTS`; never reprocess terminal `succeeded`.
- Consequences:
  - Async execution gains standard queue controls (routing, timeout, retries, worker scaling).
  - Compose/runtime must include dedicated `backend-worker` service.
  - Operational runbook and smoke checks must cover worker health path.

## ADR-0016
- Context: The temporary auth backward-compatibility layer (`subject_id + role` login and settings shim paths) kept non-canonical contracts alive after staff-account migration.
- Decision:
  - Remove `subject_id + role` legacy mode from `POST /api/v1/auth/login`.
  - Keep only `identifier + password` login payload and account-backed authentication path.
  - Remove deprecated settings shim modules:
    - `hrm_backend.auth.utils.settings`
    - `hrm_backend.core.config.settings`
  - Keep canonical settings entrypoint `hrm_backend.settings`.
- Consequences:
  - Login API contract is simplified and explicit.
  - Internal imports are normalized to one settings source of truth.
  - Legacy clients that still send `subject_id + role` must migrate before upgrade.

## ADR-0017
- Context: Public vacancy application endpoint is anonymous and vulnerable to spam and abuse without explicit guardrails.
- Decision:
  - Add Redis-backed rate limiting on three scopes:
    - `ip`
    - `ip+vacancy`
    - `email+vacancy`
  - Add anti-spam policy checks:
    - honeypot field (`website`)
    - duplicate checksum detection (`vacancy_id + checksum_sha256`)
    - cooldown window for repeated submissions per `email+vacancy`.
  - Extend audit failure reason codes for `vacancy:apply_public`.
  - Emit structured monitoring signals for success/blocked outcomes.
- Consequences:
  - Public apply path gains deterministic abuse controls and clearer diagnostics.
  - Endpoint contract now includes `409/429` paths and rate-limit headers.
  - Operations must monitor blocked-rate anomalies and maintain Redis availability.

## ADR-0018
- Context: Remaining API contracts still represented entity identifiers as plain strings, which allowed non-UUID payloads on boundary paths and produced inconsistent OpenAPI typing.
- Decision:
  - Normalize candidate/vacancy/pipeline/CV-status API schemas and route boundaries to UUID types.
  - Accept UUID in path/body contracts and return `422` for invalid non-UUID identifiers.
  - Keep storage layer unchanged (string UUID columns) and convert UUID -> string only at DAO/model boundary.
- Consequences:
  - OpenAPI now exposes uniform `format: uuid` for normalized ID fields.
  - Contract validation becomes stricter for clients still sending legacy non-UUID values.
  - Service signatures become type-safe without forcing DB storage migration in this phase.

## ADR-0019
- Context: Backend and frontend integration velocity depends on stable API contracts; drift between runtime schema and client expectations caused avoidable regressions.
- Decision:
  - Store frozen OpenAPI contract in-repo at `docs/api/openapi.frozen.json`.
  - Add generation script (`scripts/generate-openapi-frozen.sh`) and drift check (`scripts/check-openapi-freeze.sh`).
  - Enforce contract drift check in CI.
  - Generate frontend TypeScript API types from frozen spec via `openapi-typescript`.
- Consequences:
  - Contract changes become explicit and reviewable.
  - CI fails early when runtime schema diverges from frozen contract.
  - Frontend typed API artifacts stay aligned with reviewed backend contract.

## ADR-0020
- Context: Admin workspace rollout requires minimum vertical slice with explicit deny behavior and route-level observability before wider admin feature development.
- Decision:
  - Add frontend `/admin` route guarded by role check (`admin` only).
  - Implement redirect path for unauthorized (`unauthorized`) and forbidden (`forbidden`) access outcomes.
  - Deliver RU/EN admin shell placeholder layout for ADMIN-01.
  - Emit Sentry tags (`workspace`, `role`, `route`) on admin route access.
- Consequences:
  - Admin entry flow is deterministic and testable for both allowed and denied paths.
  - Observability baseline exists before deeper admin features (ADMIN-02/03).
  - Frontend routing contract expands with dedicated access-denied flow.

## ADR-0021
- Context: `ADMIN-02` requires operational staff governance from admin workspace while preventing lock-out and privilege-loss incidents.
- Decision:
  - Add admin staff management endpoints:
    - `GET /api/v1/admin/staff` with server-driven pagination and filters (`search`, `role`, `is_active`).
    - `PATCH /api/v1/admin/staff/{staff_id}` with partial updates limited to `role` and `is_active`.
  - Extend RBAC with `admin:staff:list` and `admin:staff:update` permissions granted to `admin` only.
  - Enforce strict guard in service layer:
    - forbid self-demotion and self-disable;
    - forbid deactivation/demotion of the last active `admin`.
  - Standardize failure reason-code contract in API error details:
    `staff_not_found`, `empty_patch`, `unsupported_role`,
    `self_modification_forbidden`, `last_admin_protection`, `validation_failed`.
  - Extend frontend admin workspace with `/admin/staff` route, server-driven table, filters, update actions, and localized error mapping for `404/409/422`.
- Consequences:
  - Staff role/activity governance is available as one vertical slice (backend + frontend + contract).
  - Admin safety invariants are enforced centrally in business logic.
  - Audit evidence is expanded with `admin.staff:list` and `admin.staff:update` success/failure traces.
  - `ADMIN-03` (employee key lifecycle UI/API expansion) remains isolated as next phase.

## ADR-0022
- Context: Admin governance flows were implemented in `hrm_backend/auth`, which broke bounded-context separation and conflicted with the package structure baseline used by other domains (for example `candidates`).
- Decision:
  - Extract admin HTTP/business/persistence layers to dedicated package `hrm_backend/admin`.
  - Keep package structure aligned with extraction-ready baseline:
    `models`, `schemas`, `services`, `dao`, `routers`, `utils`, `dependencies`, plus explicit `infra` adapters.
  - Keep API contracts unchanged (`/api/v1/admin/*`, reason-code behavior, RBAC requirements), but route orchestration through `admin` service/DAO layers.
  - Keep `hrm_backend/auth` scoped to auth/session lifecycle only (`register/login/refresh/logout/me`).
- Consequences:
  - Domain boundaries are explicit and consistent with engineering standards.
  - Admin feature development no longer couples to auth service internals.
  - Test topology now follows package flow (`tests/unit/admin`, `tests/integration/admin`).

## ADR-0023
- Context: `ADMIN-03` requires full lifecycle management for employee registration keys in one vertical slice (backend + frontend + contract + docs) while keeping `ADMIN-02` unchanged.
- Decision:
  - Extend admin API with:
    - `GET /api/v1/admin/employee-keys` (pagination + filters: `target_role`, `status`, `created_by_staff_id`, `search`);
    - `POST /api/v1/admin/employee-keys/{key_id}/revoke`.
  - Keep `POST /api/v1/admin/employee-keys` backward-compatible.
  - Extend employee key persistence model with revocation metadata:
    - `revoked_at`
    - `revoked_by_staff_id` (FK to `staff_accounts`).
  - Standardize lifecycle statuses for admin list response:
    - `active`
    - `used`
    - `expired`
    - `revoked`.
  - Use conflict-based revoke semantics with reason codes:
    - `key_not_found` (`404`)
    - `key_already_used` (`409`)
    - `key_already_expired` (`409`)
    - `key_already_revoked` (`409`)
    - `validation_failed` (`422`).
  - Extend RBAC with `admin:employee_key:list` and `admin:employee_key:revoke` granted to `admin` and `hr`.
  - Extend frontend admin workspace with `/admin/employee-keys` screen (table, filters, pagination, create/revoke actions, RU/EN errors, Sentry route tag).
- Consequences:
  - Employee-key governance is now fully operational from admin APIs/UI without breaking existing create-key clients.
  - Registration flow explicitly rejects revoked keys.
  - Admin audit trail expands with `admin.employee_key:list` and `admin.employee_key:revoke` success/failure events and reason codes.

## ADR-0024
- Context: `TASK-03-05` and `TASK-03-06` require bilingual RU/EN CV normalization and explainable traceability from extracted facts to source CV fragments, while preserving existing candidate API compatibility.
- Decision:
  - Extend `candidate_documents` storage model with analysis artifacts:
    - `parsed_profile_json`
    - `evidence_json`
    - `detected_language`
    - `parsed_at`.
  - Expand parsing pipeline (`parse_cv_document`) to return:
    - canonical normalized profile;
    - detected language (`ru`, `en`, `mixed`, `unknown`);
    - evidence objects (`field`, `snippet`, `start_offset`, `end_offset`, `page`).
  - Persist parse result atomically in worker success path before marking parsing job as `succeeded`.
  - Keep existing endpoints backward-compatible and extend contracts with:
    - `GET /api/v1/candidates/{candidate_id}/cv/analysis`
    - extra fields in `CVParsingStatusResponse` (`analysis_ready`, `detected_language`).
  - Extend frontend candidate workspace with CV Analysis block (status, detected language, evidence snippets) and RU/EN localization for analysis states/errors.
- Consequences:
  - Candidate CV parsing output is now explainable and queryable without re-parsing raw documents.
  - API consumers can poll readiness and fetch analysis payload in a backward-compatible flow.
  - Data retention scope increases for CV-derived artifacts, requiring alignment with compliance retention policy before production rollout.

## ADR-0025
- Context: Candidate authentication is intentionally out of scope for Phase 1, but the frontend still needs a real self-service journey with browser-level regression protection. Polling protected candidate endpoints by `candidate_id` was incompatible with the anonymous public apply model.
- Decision:
  - Keep the candidate flow anonymous and use the public deep-link contract:
    `/candidate?vacancyId=<uuid>&vacancyTitle=<display-only>`.
  - Expose anonymous read endpoints keyed by `parsing_job_id`:
    - `GET /api/v1/public/cv-parsing-jobs/{job_id}`
    - `GET /api/v1/public/cv-parsing-jobs/{job_id}/analysis`
  - Persist browser tracking context in `sessionStorage` under `hrm_candidate_application_context`.
  - Treat compose runtime as Phase 1 verification baseline by including `backend-worker` and expanding `./scripts/smoke-compose.sh` to validate:
    - staff login browser flow;
    - deterministic open-vacancy creation through staff API;
    - public candidate apply browser flow through the real React UI.
- Consequences:
  - Anonymous candidate tracking no longer depends on staff-only candidate endpoints or a resurrected candidate auth model.
  - Browser smoke now catches regressions in deep-link routing, `VITE_API_BASE_URL` wiring, public apply submission, and job-based tracking before merge.
  - Compose smoke depends on local Chrome/Chromium availability; parsing completion is best-effort, but submit plus successful public status read is the minimum required success signal.

## ADR-0026
- Context: The current repository diff already forms a coherent local baseline slice. Expanding that diff further would blur acceptance scope, while starting interview scheduling next would force implementation against under-specified product rules. The next safe increment is the handoff from parsed CV analysis into recruiter-facing shortlist review.
- Decision:
  - Land the current Phase 1 baseline as one PR with fixed scope:
    - public candidate apply/tracking by `parsing_job_id`;
    - HR vacancy/pipeline workspace on `/`;
    - browser smoke for staff login + public candidate apply;
    - local compose MinIO dev exception with `OBJECT_STORAGE_SSE_ENABLED=false`;
    - backlog/architecture/testing/runbook synchronization.
  - Use the documented Phase 1 merge gate in `docs/testing/strategy.md` before merge, then sync local `main` before the next increment starts.
  - Make the next implementation slice one vertical delivery unit: `TASK-04-01`, `TASK-04-02`, `TASK-04-03`, and `TASK-11-07`.
  - Create a dedicated backend scoring package (`hrm_backend/scoring`) with extraction-ready subpackages instead of mixing scoring logic into `candidates` or `vacancies`.
  - Add DB-backed async scoring lifecycle through `match_scoring_jobs` with states:
    `queued`, `running`, `succeeded`, `failed`.
  - Persist a score artifact keyed by `vacancy_id + candidate_id + active_document_id`.
  - Freeze the minimal API contract for the slice:
    - `POST /api/v1/vacancies/{vacancy_id}/match-scores`
    - `GET /api/v1/vacancies/{vacancy_id}/match-scores`
    - `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`
  - Reject score enqueue with `409` when parsed CV analysis is not ready; do not add silent fallbacks.
  - Extend the existing HR workspace on `/` with a shortlist review block; do not add a new scoring route.
  - Keep compose browser smoke limited to login + public candidate apply. Scoring verification stays at unit/integration level until Ollama/runtime nondeterminism is isolated.
  - Defer `TASK-11-08` until a dedicated planning pass resolves interview entity boundaries, registration/identity model, reschedule/cancel semantics, and calendar sync conflict behavior.
- Consequences:
  - The current local baseline can merge without scope creep.
  - Scoring contracts, storage, and package boundaries become explicit before UI work is wired.
  - Auth, CORS, public-candidate transport, and compose smoke assumptions remain stable across the next slice.
  - Interview scheduling remains intentionally blocked on unresolved product decisions instead of being implemented on guesswork.

## ADR-0027
- Context: The post-baseline scoring slice is now implemented locally and needed one cohesive architecture instead of scattered vacancy/candidate add-ons. The delivery needed a stable API contract, explicit async lifecycle, and a shortlist UI that works against the real backend contract without changing route topology.
- Decision:
  - Implement a dedicated backend package `hrm_backend/scoring` with extraction-ready subpackages for models, DAO, services, dependencies, routers, utils, and infrastructure adapters.
  - Persist async lifecycle in `match_scoring_jobs` and persist explainable UI payloads in `match_score_artifacts`.
  - Keep the public API surface limited to:
    - `POST /api/v1/vacancies/{vacancy_id}/match-scores`
    - `GET /api/v1/vacancies/{vacancy_id}/match-scores`
    - `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`
  - Reject enqueue with `409` when the active candidate document does not yet contain parsed CV analysis.
  - Reuse the existing Celery app/runtime, but register a separate `match_scoring` queue consumed by the same compose worker process.
  - Extend `HrDashboardPage` on `/` with a shortlist review block instead of introducing a new frontend route.
  - Keep scoring verification at unit/integration level and continue excluding Ollama/browser scoring from compose smoke.
- Consequences:
  - Scoring logic is isolated from `candidates` and `vacancies`, which keeps future extraction paths open.
  - Recruiter-facing shortlist review now consumes a frozen backend contract with typed frontend wrappers.
  - Compose runtime grows by one additional queue, but route/auth/CORS/public-candidate transport assumptions stay unchanged.

## ADR-0028
- Context: After shortlist review landed, frontend observability was still partial: admin route tags existed, but the main HR, candidate, and login routes were not tagged uniformly, shared HTTP failures were not captured centrally, and render failures had no top-level localized fallback. The next safe increment had to harden Sentry without changing routes, auth, CORS, or API contracts.
- Decision:
  - Keep the existing route topology unchanged:
    - `/`
    - `/candidate`
    - `/login`
    - `/admin`
    - `/admin/staff`
    - `/admin/employee-keys`
  - Emit canonical Sentry tags (`workspace`, `role`, `route`) on each critical-route entry:
    - `/` -> role-resolved `workspace` tag for the current staff workspace (`hr`, `manager`, or later additive staff workspaces such as `accountant`)
    - `/candidate` -> `workspace=candidate`
    - `/login` -> `workspace=auth`
    - `/admin*` -> `workspace=admin`
  - Add centralized HTTP failure capture in the shared frontend HTTP client so failed requests report:
    - current `workspace`, `role`, `route`
    - `http_method`
    - `http_status` when available
    - request path as event metadata.
  - Wrap the frontend app shell in a top-level Sentry error boundary with RU/EN fallback UI for render failures.
  - Configure release/environment/tracing through frontend env variables:
    `VITE_SENTRY_DSN`, `VITE_SENTRY_ENVIRONMENT`, `VITE_SENTRY_RELEASE`, `VITE_SENTRY_TRACES_SAMPLE_RATE`.
- Consequences:
  - Critical frontend routes now emit one consistent Sentry tag model instead of admin-only tagging.
  - Browser request failures and render crashes become visible in Sentry without changing business contracts.
  - Route topology, typed API wrappers, auth behavior, and CORS assumptions stay unchanged while observability coverage increases.

## ADR-0029
- Context: Interview scheduling was the next business gap after scoring/observability/compliance, but implementation remained blocked by missing product rules around entity lifecycle, candidate identity, reschedule/cancel semantics, and Google Calendar conflicts. The repository also has no candidate auth or notification service, so the interview slice needed an implementation-safe baseline that works with existing route and transport constraints.
- Decision:
  - Freeze the planning baseline in `docs/project/interview-planning-pass.md` before interview implementation starts, then implement the slice against that frozen scope without reopening auth, CORS, or route topology.
  - Keep one non-terminal interview per `vacancy_id + candidate_id`; use `schedule_version` on the same row for reschedules.
  - Keep candidate access anonymous through a public opaque invitation token stored hashed in the backend and bound to `interview_id + schedule_version`.
  - Keep the existing route topology:
    - HR interview controls extend `/`
    - candidate interview registration extends `/candidate` through `?interviewToken=<token>` at the time of this decision; the later candidate-route split in ADR-0058 moved it to `/candidate/interview/:interviewToken`
  - Do not introduce candidate auth, new CORS rules, or a new route tree in the interview slice.
  - Separate business interview state from calendar execution state:
    - interview `status`: `pending_sync`, `awaiting_candidate_confirmation`, `confirmed`, `reschedule_requested`, `cancelled`
    - `calendar_sync_status`: `queued`, `running`, `synced`, `conflict`, `failed`
  - Implement Google Calendar sync in the next slice as staff-calendar orchestration only:
    - use a service-account JSON key
    - map interviewer staff UUIDs to calendars configured in environment
    - require each interviewer calendar to be manually shared with the service account
    - do not rely on Google guest invitations or `attendees[]`
  - Keep candidate invitation delivery manual through `candidate_invite_url` until a notification service exists.
  - Freeze the minimal public/backend API set around:
    - HR create/list/get/reschedule/cancel/resend-invite endpoints
    - public token read/confirm/request-reschedule/cancel endpoints
  - Auto-append one `shortlist -> interview` pipeline transition on first successful interview sync when needed.
- Consequences:
  - Interview implementation can proceed without the implementer making hidden product decisions.
  - Existing anonymous candidate transport assumptions remain intact.
  - Free-mode calendar access is operationally simple but depends on manual sharing and explicit staff-to-calendar configuration.
  - Notification delivery is intentionally deferred, so the slice remains feasible in local-stage scope.

## ADR-0030
- Context: Interview scheduling and candidate registration are now implemented, but the next interview-domain work remained under-specified around who can submit structured feedback, how reschedules affect feedback validity, and where the fairness guard should live before `offer`. Reopening auth, route topology, or adding a parallel decision API would create avoidable scope creep.
- Decision:
  - Freeze the planning baseline in `docs/project/interview-feedback-fairness-pass.md` before implementation of `TASK-05-03/04`.
  - Keep interviewer feedback as interview-domain data rather than pipeline metadata:
    - one current feedback row per `interview_id + schedule_version + interviewer_staff_id`
    - previous schedule-version feedback remains audit history but does not satisfy the fairness gate
  - Keep the existing route topology:
    - HR feedback UX extends `/`
    - candidate route `/candidate` remains unchanged and never exposes interviewer feedback at the time of this decision; the later candidate-route split in ADR-0058 moved public candidate transport to `/candidate/apply` and `/candidate/interview/:interviewToken`
  - Keep the existing transition endpoint `POST /api/v1/pipeline/transitions`; when `to_stage=offer`, run the fairness gate there instead of adding a parallel offer-decision API.
  - Limit the fairness gate in this slice to current-version completeness and payload validity:
    - all assigned interviewers must submit feedback for the active `schedule_version`
    - mandatory rubric scores and qualitative notes must be present
    - recommendation disagreement is surfaced to HR but does not auto-block `offer`
  - Freeze the minimal backend API set around:
    - `GET /api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback`
    - `PUT /api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback/me`
  - Keep auth, CORS behavior, public candidate transport, and compose smoke scope unchanged for this slice.
- Consequences:
  - The next interview slice can be implemented without hidden product or API decisions.
  - Implementation now persists `interview_feedback` rows, extends the `/` workspace with panel summary + `feedback/me`, and enforces the accepted `409` fairness-gate reason codes on the existing `interview -> offer` transition.
  - Feedback remains traceable to the real interview schedule and interviewer assignment.
  - Pipeline semantics stay centralized in the existing transition flow, which reduces route and audit fragmentation.
  - More sophisticated fairness policy, interviewer reminders, and candidate-facing visibility remain explicitly deferred.

## ADR-0031
- Context: `TASK-06-01` already fixed the offer lifecycle on the existing vacancy route tree and kept `offer -> hired` on `POST /api/v1/pipeline/transitions`, but the downstream employee-domain boundary remained undefined. Adding a separate conversion endpoint, creating employee profiles immediately, or triggering onboarding inside the same slice would reopen route topology and sequencing decisions unnecessarily.
- Decision:
  - Keep `POST /api/v1/pipeline/transitions` as the only command surface for `offer -> hired`.
  - Keep the existing offer gate unchanged:
    - `offer.status=accepted` is still required for `hired`
    - public `409 offer_not_accepted` / `409 offer_not_declined` semantics remain unchanged
  - On successful `offer -> hired`, persist one durable `hire_conversion` row atomically with the `pipeline_transitions` write.
  - Store the handoff as a frozen employee-domain bootstrap artifact keyed by `vacancy_id + candidate_id`, including:
    - `offer_id`
    - `hired_transition_id`
    - candidate bootstrap snapshot
    - accepted-offer snapshot
    - `status=ready`
    - `converted_at`
    - `converted_by_staff_id`
  - Keep route topology, auth, CORS behavior, and public candidate transport unchanged.
  - Defer actual employee profile creation to `TASK-06-03`.
  - Defer onboarding trigger/execution to `TASK-06-04`.
- Consequences:
  - Recruitment keeps ownership of the hiring command while the employee domain receives one deterministic persisted handoff.
  - The `offer -> hired` flow is now durable without introducing a new public contract.
  - Employee bootstrap sequencing is explicit: hire conversion first, employee profile second, onboarding third.
  - The slice remains small and reversible because it does not start employee CRUD or onboarding execution prematurely.

## ADR-0032
- Context: `TASK-06-02` already persists one durable `hire_conversion` handoff, but the employee domain still lacked an explicit bootstrap command and read surface. Automatically creating employee records during `offer -> hired` would collapse two slices into one, while reusing the vacancy transition endpoint for employee CRUD would blur domain ownership and error contracts.
- Decision:
  - Introduce a dedicated staff-facing employee route tree:
    - `POST /api/v1/employees`
    - `GET /api/v1/employees/{employee_id}`
  - Keep the create input minimal and contextual to existing HR workflow state:
    - `vacancy_id`
    - `candidate_id`
    - resolve the durable `hire_conversion` internally instead of exposing `conversion_id` as a command input
  - Create one `employee_profiles` row only from a persisted ready-state `hire_conversion`.
  - Validate frozen candidate and accepted-offer snapshots before persistence; malformed handoff data returns `422 hire_conversion_invalid`.
  - Enforce one employee profile per hire conversion:
    - duplicate bootstrap returns `409 employee_profile_already_exists`
    - missing handoff returns `404 hire_conversion_not_found`
    - missing employee read returns `404 employee_profile_not_found`
  - Limit access to `admin` and `hr` via new permissions:
    - `employee_profile:create`
    - `employee_profile:read`
  - Do not trigger onboarding in this slice.
- Consequences:
  - Employee bootstrap now has a stable API contract and persistence boundary without changing candidate/public flows.
  - Route-topology change is explicit and documented rather than implicit drift.
  - `TASK-06-04` can start onboarding from an existing employee profile instead of directly from the hiring transition.
  - Employee self-service, manager visibility, and richer employee lifecycle states remain deferred.

## ADR-0033
- Context: `TASK-06-03` introduced an explicit employee bootstrap endpoint, but onboarding still had no durable start marker. Adding a separate onboarding-start command would widen the route surface, while starting onboarding directly from `hire_conversions` would bypass the new employee-domain source of truth.
- Decision:
  - Keep `POST /api/v1/employees` as the only command surface for employee bootstrap and onboarding start.
  - Start onboarding from the persisted `employee_profile`, not directly from `hire_conversion` resolution.
  - Persist one durable `onboarding_runs` row atomically with `employee_profiles` on successful bootstrap.
  - Keep the onboarding-start artifact minimal in this slice:
    - `onboarding_id`
    - `employee_id` (unique)
    - copied `hire_conversion_id`
    - `status=started`
    - `started_at`
    - `started_by_staff_id`
  - Extend `EmployeeProfileResponse` additively with:
    - `onboarding_id`
    - `onboarding_status`
  - Keep duplicate bootstrap semantics unchanged:
    - `409 employee_profile_already_exists`
    - no onboarding-specific duplicate write contract is introduced
  - Defer onboarding checklist templates, task assignment, employee portal, manager dashboard, and notifications to `TASK-07-*`.
- Consequences:
  - Employee bootstrap and onboarding start now share one transaction boundary, so onboarding persistence failure rolls back the employee profile insert.
  - The employee API remains the stable trigger surface and does not add a parallel onboarding route tree.
  - Later onboarding slices can consume `onboarding_runs` as their durable source input without rereading mutable recruitment state.
  - Contract churn stays minimal because onboarding visibility is additive on the existing employee response.

## ADR-0034
- Context: `TASK-06-04` now persists durable `onboarding_runs`, but later onboarding-task slices still lacked a configurable checklist source of truth. Reusing `POST /api/v1/employees` for template management would mix employee bootstrap with operational configuration, while jumping straight to task generation would hardcode checklist content too early.
- Decision:
  - Introduce a dedicated staff-only onboarding template route tree:
    - `POST /api/v1/onboarding/templates`
    - `GET /api/v1/onboarding/templates`
    - `GET /api/v1/onboarding/templates/{template_id}`
    - `PUT /api/v1/onboarding/templates/{template_id}`
  - Keep template management inside the existing `hrm_backend/employee` package because it is still part of the employee/onboarding domain boundary.
  - Persist one template row plus durable child checklist items:
    - `onboarding_templates`
    - `onboarding_template_items`
  - Keep the template item shape minimal for this slice:
    - stable item `code`
    - `title`
    - optional `description`
    - `sort_order`
    - `is_required`
  - Enforce operational guardrails:
    - unique template `name`
    - unique item `code` and `sort_order` within one template
    - activating one template automatically deactivates previously active templates
  - Limit access to `admin` and `hr` via:
    - `onboarding_template:create`
    - `onboarding_template:list`
    - `onboarding_template:read`
    - `onboarding_template:update`
  - Defer task generation, SLA/assignment logic, employee portal, manager dashboard, and notifications to later slices.
- Consequences:
  - `TASK-07-02` can generate onboarding tasks from one active, staff-managed checklist baseline instead of hardcoded defaults.
  - Employee bootstrap and onboarding template management stay separated at the API level, which keeps write contracts easier to reason about.
  - The onboarding domain now has durable configuration state without committing yet to task lifecycle semantics.

## ADR-0035
- Context: `TASK-07-01` introduced durable active onboarding templates, but onboarding runs still had no materialized task rows, no staff assignment/SLA surface, and no way to backfill legacy runs created before task generation existed.
- Decision:
  - Extend the existing employee bootstrap command on `POST /api/v1/employees` so successful bootstrap now atomically persists:
    - `employee_profiles`
    - `onboarding_runs`
    - `onboarding_tasks`
  - Resolve onboarding tasks from the current active onboarding template; if no active template exists, fail employee bootstrap with `422 onboarding_template_not_configured` and roll back the whole transaction.
  - Persist one durable onboarding task row per generated template item with:
    - owning `onboarding_id`
    - copied `template_id` and `template_item_id` for provenance
    - frozen task snapshot fields (`code`, `title`, `description`, `sort_order`, `is_required`)
    - workflow fields (`status`, `assigned_role`, `assigned_staff_id`, `due_at`, `completed_at`)
  - Keep `onboarding_runs.status` unchanged as `started`; task progress remains on `onboarding_tasks` until later portal/dashboard slices define aggregate run lifecycle semantics.
  - Introduce a staff-only onboarding task route tree under the existing onboarding namespace:
    - `GET /api/v1/onboarding/runs/{onboarding_id}/tasks`
    - `PATCH /api/v1/onboarding/runs/{onboarding_id}/tasks/{task_id}`
    - `POST /api/v1/onboarding/runs/{onboarding_id}/tasks/backfill`
  - Use explicit backfill for legacy onboarding runs with zero tasks instead of automatic lazy generation.
  - Limit task routes to `admin` and `hr` via:
    - `onboarding_task:list`
    - `onboarding_task:update`
    - `onboarding_task:backfill`
  - Keep employee/manager self-service onboarding views, template-driven due-date calculation, notifications, and progress dashboards deferred to later slices.
- Consequences:
  - New employee bootstrap now has one explicit transaction boundary from hire conversion resolution through task materialization.
  - Later onboarding slices can build portal/dashboard UX on durable task rows instead of rereading template state.
  - Backfill stays explicit and auditable for pre-existing onboarding runs instead of introducing hidden side effects on reads.
  - The onboarding API surface grows only within the existing `/api/v1/onboarding/...` namespace and does not reopen auth, CORS, or public candidate transport decisions.

## ADR-0036
- Context: `TASK-07-02` already materialized durable onboarding tasks and staff operations, but the product still lacked an employee-facing portal and a stable way to resolve the authenticated `employee` subject to one `employee_profile`. Reopening the auth model, introducing a parallel identity service, or exposing public onboarding routes would add disproportionate scope for the next slice.
- Decision:
  - Introduce an employee-only self-service onboarding surface on the existing employee route tree:
    - `GET /api/v1/employees/me/onboarding`
    - `PATCH /api/v1/employees/me/onboarding/tasks/{task_id}`
  - Extend frontend route topology with one employee workspace:
    - `/employee`
    - post-login redirect for `employee` role changes from `/` to `/employee`
  - Add one durable optional identity bridge on `employee_profiles`:
    - `staff_account_id -> staff_accounts.staff_id`
  - Resolve employee self-service identity in two steps:
    - first by direct `staff_account_id` link
    - otherwise by exact e-mail reconciliation from the authenticated staff account to `employee_profiles.email`, then persist the durable link for later requests
  - Fail closed when identity cannot be resolved safely:
    - `404 employee_profile_not_found`
    - `409 employee_profile_identity_conflict`
  - Limit employee self-service task updates to `status` only, and only when the task is actionable for the current employee:
    - `assigned_role` is `null` or `employee`
    - `assigned_staff_id` is `null` or the current authenticated subject
    - otherwise return `409 onboarding_task_not_actionable_by_employee`
  - Keep admin/HR onboarding assignment/backfill/SLA operations on the existing staff onboarding routes.
  - Keep auth, CORS, public candidate transport, onboarding template model, and staff task APIs unchanged in this slice.
- Consequences:
  - The employee domain now owns a complete self-service onboarding read/update contract without reopening the auth subsystem.
  - Identity reconciliation becomes explicit and durable after the first successful portal read or update.
  - Ambiguous employee-to-auth matches fail closed and are visible as an operational data-cleanup issue instead of a silent cross-account data leak.
  - Manager dashboard, richer employee profile editing, alternative identity matching rules, and notifications remain deferred to later slices.

## ADR-0037
- Context: `TASK-07-03` completed employee self-service onboarding, but staff users still lacked a consolidated progress read surface and managers had no sanctioned workspace entrypoint for their onboarding responsibilities. Creating a new route tree for managers or widening manager access to existing task mutation APIs would overshoot the intended read-only dashboard slice.
- Decision:
  - Keep the existing `/` route as the only staff workspace entrypoint in this slice:
    - `hr`/`admin` retain the recruitment workspace on `/` and receive onboarding progress as an embedded block
    - `manager` uses `/` as a standalone onboarding progress dashboard
  - Introduce read-only onboarding dashboard APIs on the existing onboarding namespace:
    - `GET /api/v1/onboarding/runs`
    - `GET /api/v1/onboarding/runs/{onboarding_id}`
  - Build the dashboard read model directly from durable `employee_profiles`, `onboarding_runs`, and `onboarding_tasks` instead of a separate reporting table in this slice.
  - Allow `admin` and `hr` to read all onboarding runs.
  - Allow `manager` to read onboarding runs only when at least one materialized task satisfies either:
    - `assigned_role=manager`
    - `assigned_staff_id=<current manager subject>`
  - Keep manager access read-only:
    - no `PATCH /api/v1/onboarding/runs/{onboarding_id}/tasks/{task_id}`
    - no `POST /api/v1/onboarding/runs/{onboarding_id}/tasks/backfill`
  - Add dedicated read permission `onboarding_dashboard:read` for `admin`, `hr`, and `manager`.
  - Update frontend observability so `/` emits:
    - `workspace=hr` for the HR/admin recruitment workspace
    - `workspace=manager` for the manager onboarding dashboard
  - Keep auth, CORS, employee portal routes, candidate/public transport, and the existing task/template APIs unchanged.
- Consequences:
  - Staff now have one durable onboarding progress surface without introducing a separate manager-only routing tree.
  - Manager visibility remains tightly scoped to explicit task assignments, which avoids accidental team-wide data exposure before `TASK-09-01` defines broader manager workspace rules.
  - The dashboard reuses transactional onboarding tables directly, so later reporting or aggregation optimizations can be deferred until real load justifies them.
  - Full manager/team hiring workspace, richer cross-run analytics, notifications, and broader visibility policies remain deferred to `TASK-09-01+`.

## ADR-0038
- Context: `TASK-03-07` requires the documented PDF/DOCX CV support at the API boundary to match the actual backend parsing behavior. The existing parser accepted PDF/DOCX uploads but normalized raw `bytes.decode("utf-8", errors="ignore")`, which made extraction format-blind and weakened explainability for real documents.
- Decision:
  - Introduce a mime-aware extraction layer ahead of RU/EN normalization and evidence mapping.
  - Use native PDF text extraction through `pypdf`.
  - Use native DOCX text extraction by reading OOXML zip parts and extracting paragraph text from `word/document.xml` plus related text-bearing parts.
  - Fail closed when a PDF/DOCX payload is broken or yields empty extracted text; keep the existing parsing job lifecycle (`queued`, `running`, `succeeded`, `failed`) and retry behavior unchanged.
  - Keep external candidate/scoring contracts unchanged:
    - parsing status payload shape stays the same;
    - analysis response payload shape stays the same;
    - scoring still requires `parsed_profile_json + evidence_json + parsed_at`.
  - Keep evidence offsets anchored to the extracted text passed into normalization; populate `page` for PDF evidence when the extractor can resolve the matched offsets to a page.
  - Cover the slice with real PDF/DOCX fixtures in unit and integration tests and update browser smoke to submit a valid PDF fixture instead of plain text bytes labeled as PDF.
- Consequences:
  - Backend CV parsing now matches the documented PDF/DOCX product scope without changing public routes or schema contracts.
  - The worker/runtime gains one new pure-Python dependency (`pypdf`) and explicit DOCX XML handling, but avoids OCR or heavier native toolchains in this slice.
  - Explainability improves for PDF documents because evidence can now preserve source page numbers when available.
  - Image-only PDFs and blank DOCX files still fail closed until a future OCR/richer extraction slice explicitly broadens scope.

## ADR-0039
- Context: The earlier CV normalization baseline extracted only lightweight fields and used an
  IT-biased skill vocabulary. The product scope, however, is general HRM hiring across professions,
  so parsed CV artifacts needed to represent universal employment history instead of developer-only
  resumes.
- Decision:
  - Keep the existing extraction layer, worker lifecycle, routes, and DB columns unchanged.
  - Enrich `parsed_profile_json` additively with profession-agnostic structure:
    - workplace history with employer plus held position;
    - education entries;
    - normalized titles derived from workplace positions;
    - normalized dates/ranges;
    - generic skills extracted from section-aware lists, with old IT synonym mapping retained only
      as fallback compatibility.
  - Preserve explainability by mapping the new structured fields back to source snippets with
    offsets and PDF page numbers when available.
  - Keep scoring/public contracts backward-compatible by treating the richer parsed profile as
    additive JSON rather than introducing a new API or migration.
- Consequences:
  - Parsed CV artifacts now better match the stated cross-industry hiring scope of the product.
  - Existing parsing status, analysis response envelope, and scoring preconditions remain stable.
  - Later search/ranking slices can build on richer workplace and education data without reopening
    storage or route topology.

## ADR-0040
- Context: `TASK-12-02` needed a self-contained local AI verification path, but the existing
  compose baseline and scoring/public contracts were already stable and could not regress. The
  repository also had to stay compatible with host-installed Ollama instances and Linux hosts.
- Decision:
  - Keep the default backend scoring target unchanged:
    `OLLAMA_BASE_URL=http://host.docker.internal:11434`.
  - Add `extra_hosts: ["host.docker.internal:host-gateway"]` to `backend` and `backend-worker`
    so the external-host Ollama path remains Linux-safe.
  - Add an optional compose profile `ai-local` with:
    - `ollama` service using a persistent volume and `/api/tags` healthcheck;
    - `ollama-init` one-shot bootstrap that pulls `MATCH_SCORING_MODEL_NAME` and exits `0`.
  - Do not publish the Ollama port in compose, so the profile does not conflict with an existing
    host Ollama runtime.
  - Keep API routes, score payload contracts, route topology, and the baseline compose smoke
    unchanged.
  - Add a separate operator-facing verification path:
    `OLLAMA_BASE_URL=http://ollama:11434 docker compose --profile ai-local up -d --build`
    followed by `./scripts/smoke-scoring-compose.sh`.
- Consequences:
  - Default local development and CI keep the existing compose/browser smoke behavior.
  - Linux users no longer depend on Docker Desktop-style `host.docker.internal` handling for the
    external-host scoring path.
  - Real compose-local scoring verification becomes reproducible without widening mandatory CI or
    browser smoke scope.
  - First `ai-local` bootstrap can take longer and consume persistent disk because the model pull is
    explicit and cached in `ollama_data`.

## ADR-0041
- Context: `TASK-07-04` delivered manager-scoped onboarding visibility on `/`, but the manager
  experience still lacked useful hiring visibility. Existing explicit linkages such as
  manager-assigned onboarding tasks or interview participation were not sufficient to derive a
  stable vacancy-scoped workspace without risking accidental company-wide reads. Reusing HR vacancy,
  pipeline, or interview-management permissions for the manager UI would also blur RBAC semantics.
- Decision:
  - Introduce one additive vacancy-level ownership signal:
    nullable `vacancies.hiring_manager_staff_id`.
  - Keep manager hiring visibility fail-closed:
    only vacancies where `hiring_manager_staff_id=<current manager subject>` are visible in the
    manager workspace.
  - Add dedicated permission `manager_workspace:read` and stop relying on broad HR recruitment
    permissions for manager workspace reads.
  - Expose the read-only manager workspace through the existing vacancy namespace:
    - `GET /api/v1/vacancies/manager-workspace`
    - `GET /api/v1/vacancies/{vacancy_id}/manager-workspace/candidates`
  - Keep manager onboarding visibility separate and reused through the existing
    `/api/v1/onboarding/runs*` read model.
  - Keep the manager workspace on the existing `/` route, preserve `workspace=manager` Sentry
    tags, and do not add vacancy/pipeline/candidate/onboarding mutation capabilities in this slice.
  - Keep auth, CORS, and public candidate transport unchanged.
- Consequences:
  - Managers now have one useful read-only workspace for hiring plus onboarding without inheriting
    HR operator privileges.
  - HR/admin must explicitly populate `hiring_manager_staff_id` on vacancies to make hiring data
    visible to a manager; unassigned vacancies remain invisible by design.
  - Hiring visibility and onboarding visibility now use different explicit scopes (`vacancy
    ownership` vs `task assignment`), which keeps the policy auditable and understandable.
  - Future leader/team-wide visibility or richer ownership models can build on this additive signal
    instead of widening the current manager scope implicitly.

## ADR-0042
- Context: `TASK-09-03` required one accountant-facing workspace with controlled export access, but
  the product already had stable onboarding persistence and no approved generic reporting/export
  infrastructure. Reusing the HR workspace, widening onboarding dashboard visibility, or
  introducing async export jobs would overshoot the intended slice and weaken fail-closed
  visibility.
- Decision:
  - Keep the existing `/` route topology and resolve `accountant` users to a dedicated accountant
    workspace page on `/`.
  - Introduce a thin backend finance adapter package `hrm_backend/finance` instead of extending HR
    vacancy routes or adding finance-owned persistence tables.
  - Expose read-only accountant APIs:
    - `GET /api/v1/accounting/workspace`
    - `GET /api/v1/accounting/workspace/export?format=csv|xlsx`
  - Reuse the existing `accounting:read` permission for both list and export reads.
  - Keep visibility fail-closed:
    - a run is visible only when at least one onboarding task has `assigned_role=accountant`
    - or `assigned_staff_id=<current accountant subject>`
    - rows outside this scope remain invisible in UI and both export formats
  - Build the accountant row model directly from durable `employee_profiles`, `onboarding_runs`,
    and `onboarding_tasks` without a separate reporting table, migration, or async export job.
  - Support two synchronous attachment formats with one shared column contract:
    - RFC4180-style UTF-8 CSV
    - native `.xlsx`
  - Keep frontend observability canonical on `/` by emitting `workspace=accountant`,
    `role=accountant`, and `route=/`.
  - Keep auth, CORS, employee self-service routes, manager workspace rules, and generic reporting
    infrastructure unchanged in this slice.
- Consequences:
  - Accountants now have one dedicated read-only workspace and export surface without inheriting HR
    recruitment controls.
  - Export scope is auditable and deterministic because UI and CSV/XLSX attachments reuse the same
    filtered row model and ordering.
  - Finance reporting remains intentionally narrow: no batch exports, object storage artifacts, or
    reusable reporting engine are introduced before a later export/reporting ADR explicitly widens
    scope.
  - The employee domain stays the source of truth for onboarding state, while the finance adapter
    remains a thin read boundary layered on top of it.

## ADR-0043
- Context: `TASK-09-04` required role-specific notifications after manager/accountant workspaces
  were already implemented, but the system still had no approved outbound notification
  infrastructure, scheduler, event bus, or template-editor scope. The existing reliable seams were
  narrow and explicit: vacancy ownership in `vacancy_service.py` and onboarding assignment changes
  in `onboarding_task_service.py`.
- Decision:
  - Introduce a thin backend package `hrm_backend/notifications` for recipient-scoped in-app
    notification persistence plus on-demand digest reads.
  - Keep v1 delivery intentionally narrow:
    - in-app only;
    - mandatory recipient roles limited to `manager` and `accountant`;
    - digest computed synchronously on `GET /api/v1/notifications/digest`;
    - no email, SMS, webhooks, outbox, scheduler, or template-editor scope.
  - Expose protected APIs:
    - `GET /api/v1/notifications?status=unread|all&limit&offset`
    - `POST /api/v1/notifications/{notification_id}/read`
    - `GET /api/v1/notifications/digest`
  - Keep reads and updates fail-closed:
    - list/read-state changes are limited to `recipient_staff_id=<current subject>`;
    - `POST /read` returns `404 notification_not_found` outside recipient scope.
  - Emit notifications only from explicit assignment seams:
    - vacancy ownership changes to `vacancies.hiring_manager_staff_id`;
    - onboarding task assignment changes on `assigned_role` / `assigned_staff_id`.
  - Fan out role-based onboarding notifications only to active manager/accountant accounts and
    dedupe by recipient plus event fingerprint to avoid duplicate in-app rows on repeated writes.
  - Keep candidate invite delivery manual-only and leave interview invitation transport unchanged.
  - Solo-maintainer architectural self-review:
    this ADR records that the slice stays additive, keeps current `/` route semantics, avoids new
    async infrastructure, and preserves explicit fail-closed visibility boundaries.
- Consequences:
  - Managers and accountants now get one embedded in-app notification block on `/` without adding a
    separate notifications route tree.
  - Notification storage remains operationally simple because reads come from one `notifications`
    table and digests are computed on demand from current vacancy/task state.
  - Future outbound delivery channels, template systems, broader role coverage, or async delivery
    infrastructure can be layered later without reopening the current read/update contract.

## ADR-0044
- Status note: leader/admin snapshot read access is updated in ADR-0045.
- Context: `TASK-10-01` requires KPI reporting without relying on the deferred automation engine and without adding schedulers or event-bus dependencies.
- Decision:
  - Introduce a reporting package with monthly KPI snapshots stored in `kpi_snapshots`.
  - Rebuild snapshots explicitly via server-side service call (and admin-only API surface in v1).
  - Aggregate only from existing durable domain tables (vacancies, pipeline transitions, interviews, offers, hire conversions, onboarding runs/tasks).
  - Keep one global monthly scope in v1 (no team/department dimensions) and materialize zero rows for months with no data.
  - If no snapshot exists for a requested month, return an empty deterministic payload instead of live aggregation.
- Consequences:
  - KPI reporting is deterministic, idempotent, and does not require async schedulers or event streams.
  - Leader-facing reads are deferred to a follow-up slice; current API is admin-only to keep exposure tight.
  - Automation-specific KPI coverage remains explicitly out of scope until the automation engine is implemented.

## ADR-0045
- Context: `TASK-10-02` needs leader/admin visibility over existing monthly KPI snapshots without introducing
  automation metrics, schedulers, or live aggregation fallback.
- Decision:
  - Keep `kpi_snapshot:rebuild` admin-only.
  - Allow leaders to read `/api/v1/reporting/kpi-snapshots` for stored monthly snapshots.
  - Keep read paths deterministic: missing months return an empty payload; no live aggregation fallback.
  - Defer automation-specific KPI tracking until `TASK-08-*` delivers the automation engine.
- Consequences:
  - Leaders can access monthly KPI snapshots without widening rebuild authority.
  - Read operations remain fast and predictable because they are served only from stored snapshots.
  - Missing months stay empty until an admin rebuilds the snapshot.
  - Automation KPI coverage remains deferred and requires a later ADR when automation tracking lands.

## ADR-0046
- Context: `TASK-10-03` needs a read-only application query surface for existing audit evidence; audit events are already persisted reliably, but operators and future admin UI currently have no HTTP API for deterministic reads.
- Decision:
  - Add admin-only audit query API:
    - `GET /api/v1/audit/events`
    - guarded by RBAC permission `audit:read` (no access for non-admin roles in v1).
  - Keep the data source as the append-only `audit_events` table; do not introduce a new reporting/aggregation table in this slice.
  - Keep query contract deterministic:
    - exact filters (`action`, `result`, `source`, `resource_type`, `correlation_id`);
    - optional time window (`occurred_from`, `occurred_to`) with `422 detail=invalid_time_range` when `occurred_from > occurred_to`;
    - fixed ordering (`occurred_at DESC`, `event_id DESC`) and pagination (`limit`, `offset`).
  - Record audit events for the read path:
    - RBAC decision audit event for `audit:read` (existing centralized enforcement behavior);
    - business audit event `audit.event:list` with `resource_type=audit_event`, written after response assembly to avoid self-inclusion in returned rows.
  - Solo-maintainer architectural self-review:
    this ADR records that the slice stays additive (no schema changes), keeps audit evidence storage append-only, and preserves least-privilege by keeping raw audit reads admin-only.
- Consequences:
  - Audit evidence becomes queryable via HTTP for operator diagnostics and future admin UI slices without direct DB access.
  - Performance characteristics depend on existing `audit_events` indices; further indexing or retention automation can be addressed in later slices if needed.
  - Expanding audit-read access beyond admin becomes an explicit policy decision and should be tracked by a separate ADR.

## ADR-0047
- Context: `TASK-10-04` requires an export package for audits and management reporting that is safe to run synchronously in the current modular-monolith runtime and remains within a minimal, reversible scope (no new tables/jobs).
- Decision:
  - Add admin-only audit export endpoint:
    - `GET /api/v1/audit/events/export`
    - formats: `csv`, `jsonl`, `xlsx`
    - reuse the existing audit query filter contract (`action`, `result`, `source`, `resource_type`, `correlation_id`, `occurred_from`, `occurred_to`) and deterministic ordering (`occurred_at DESC`, `event_id DESC`)
    - require bounded exports (`limit` + `offset`), avoiding unbounded “export all” in one request thread
    - record business audit event `audit.event:export` after export content assembly so the export does not include its own business audit row
  - Add leader/admin KPI snapshot export endpoint:
    - `GET /api/v1/reporting/kpi-snapshots/export`
    - formats: `csv`, `xlsx`
    - reuse the stored snapshot read semantics (no live aggregation fallback)
    - record business audit event `kpi_snapshot:export` after export content assembly
  - Reuse existing read permissions (`audit:read`, `kpi_snapshot:read`) for export access in this slice; do not introduce new `*:export` permissions before an explicit policy ADR requires them.
- Consequences:
  - Operators/leaders can download evidence and reporting artifacts without direct DB access.
  - Export work stays synchronous and must remain bounded; async exports/ZIP bundling remain a follow-up slice with explicit operational review.
  - Audit export parity now includes native spreadsheet downloads without introducing a separate reporting job or table.

## ADR-0048
- Context: `TASK-08-01` requires a minimal, safe automation foundation that can evaluate trigger events into planned actions without mutating core domain state, while keeping recipients and PII handling fail-closed.
- Decision:
  - Introduce a dedicated backend package: `apps/backend/src/hrm_backend/automation`.
  - Persist automation rules in a minimal table `automation_rules` with:
    - `conditions_json` (JSON condition tree),
    - `actions_json` (JSON list of actions),
    - `priority`, `is_active`,
    - audit fields (`created_by_staff_id`, `updated_by_staff_id`, `created_at`, `updated_at`).
  - Define canonical trigger event contracts (envelope + payloads):
    - `pipeline.transition_appended`
    - `offer.status_changed`
    - `onboarding.task_assigned`
    Source of truth: `docs/architecture/automation-events.md`.
  - Add a deterministic evaluator interface:
    `evaluate(event) -> planned_actions[]`
    - deterministic ordering (rule priority + stable tie-breakers),
    - no side effects (planning only in `TASK-08-01`),
    - fail-closed recipient resolution limited to the current notification slice roles:
      `manager`, `accountant`.
  - Integrate evaluator calls from domain seams (best-effort, fail-closed):
    - pipeline transition append (including public apply),
    - offer status transitions,
    - onboarding task assignment changes.
  - Limit supported actions in this slice to `notification.emit` (in-app), with an idempotency hook:
    `dedupe_key = rule_id + trigger_event_id + event_time` (executor in `TASK-08-02`).
  - Enforce recruitment-trigger PII minimization for notification text/payload:
    only `vacancy_title`, `stage`/`offer_status`, `candidate_id_short`.
  - Expose minimal admin/hr CRUD APIs for rules under `/api/v1/automation/rules` guarded by new RBAC permissions:
    `automation_rule:create`, `automation_rule:list`, `automation_rule:update`, `automation_rule:activate`.
- Consequences:
  - Automation rules can be defined and validated early without introducing domain mutations.
  - Core domain flows remain reliable; automation evaluation failures do not block writes.
  - Durable execution logs and retries are deferred to `TASK-08-03+`.

## ADR-0049
- Context: `TASK-08-02` requires executing planned `notification.emit` actions in a retry-safe way
  without impacting core domain writes, while keeping evaluator behavior deterministic and fail-closed.
- Decision:
  - Introduce `AutomationActionExecutor` to execute evaluator plans by persisting in-app notifications
    via the existing `notifications` storage contract.
  - Keep the evaluator interface unchanged (`event -> planned_actions[]`), and move all side effects
    into the executor.
  - Execute synchronously from existing domain seams (after the domain write is committed) with
    fail-closed behavior (swallow exceptions and rollback the session on failure).
  - Use planned `dedupe_key` and `ux_notifications_recipient_dedupe` uniqueness to make execution
    idempotent for at-least-once semantics and future retries.
- Consequences:
  - Automation rules can now produce user-visible in-app notifications in v1.
  - Execution adds additional DB work on the request path; async/outbox execution can be introduced
    later if latency becomes a concern.

## ADR-0050
- Context: `TASK-08-03` requires durable automation execution logs and error traceability for the
  `TASK-08-02` executor while keeping core domain flows unaffected (fail-closed) and avoiding
  additional PII exposure in logs.
- Decision:
  - Introduce durable execution log tables:
    - `automation_execution_runs` (one run per handled trigger event),
    - `automation_action_executions` (one row per planned action attempt).
  - Store only a strict non-PII allowlist in execution logs:
    - technical identifiers and snapshots (`event_type`, `trigger_event_id`, `rule_id`,
      `recipient_staff_id`, `recipient_role`, `source_type`, `source_id`, `dedupe_key`);
    - execution state (`status`, `attempt_count`) and timestamps;
    - traceability fields (`correlation_id` from `X-Request-ID` when available, plus generated
      `trace_id`);
    - sanitized + truncated error metadata (`error_kind`, `error_text`).
  - Explicitly do **not** persist in execution logs:
    notification title/body, notification payload JSON, template context, trigger payloads, or
    any human-readable identity fields (names/emails/phones).
  - Keep executor semantics fail-closed:
    - automation planning/execution failures never block domain writes,
    - execution log failures never crash the request path (best-effort logging).
  - Expose minimal operator read APIs for execution logs under `/api/v1/automation/executions*`
    guarded by new RBAC permissions:
    `automation_execution:list`, `automation_execution:read` (admin/hr).
  - Retention policy baseline:
    execution logs are retained for **30 days** by default; automated purge is deferred to a
    follow-up slice once ops scheduling/worker ownership is finalized.
- Consequences:
  - Automation failures and dedupe behavior become observable and queryable without DB access.
  - Operators can correlate execution issues with request traces using `correlation_id`/`trace_id`.
  - Storage growth requires a retention/purge mechanism; list/read APIs must remain bounded and
    indexed to avoid operational degradation.

## ADR-0051
- Context: `TASK-08-04` requires a durable, idempotent KPI event stream so monthly automation share
  metrics can be rebuilt from an append-only source without reusing execution-log tables or adding
  new HTTP routes.
- Decision:
  - Introduce `automation_metric_events` as the durable KPI source of truth, keyed by
    `event_type + trigger_event_id`.
  - Persist one metric row per handled automation trigger event from `AutomationActionExecutor`
    after execution outcome is known, using a best-effort writer isolated from the main request
    transaction.
  - Store only aggregate, non-PII counts and outcome labels needed for reporting:
    `event_time`, `outcome`, `total_hr_operations_count`, `automated_hr_operations_count`,
    `planned_action_count`, `succeeded_action_count`, `deduped_action_count`, and
    `failed_action_count`.
  - Keep reporting on the existing KPI snapshot read/rebuild/export routes and aggregate the new
    automation metric stream inside the monthly rebuild path.
  - Derive `automated_hr_operations_share_percent` as floor division of the automated count by the
    total count, returning `0` when the denominator is `0`.
- Consequences:
  - Leaders get automation KPI visibility through the existing snapshot API and `/leader` UI
    without new route topology.
  - The metric stream stays additive and idempotent, even when execution logs or notification
    writes are retried.
  - Historical backfill remains a separate follow-up because the stream only covers handled events
    after this slice is deployed.
  - Architecture review: self-review completed on 2026-03-19; the change is additive, preserves
    existing RBAC and route boundaries, and keeps execution logs separate from KPI metrics.

## ADR-0052
- Context: ADMIN-04 needs to close the admin control-plane gap quickly without introducing a new
  backend namespace, destructive data operations, or route churn beyond the existing `/admin/*`
  shell.
- Decision:
  - Deliver the slice as a frontend-first control plane over existing backend contracts:
    candidate profile list/get/create/update, vacancy list/get/create/update, pipeline transition
    list/create, and audit list/export.
  - Add dedicated admin routes:
    - `/admin/candidates`
    - `/admin/vacancies`
    - `/admin/pipeline`
    - `/admin/audit`
  - Keep the slice non-destructive:
    - no hard delete flows;
    - archive/destructive policy remains a separate follow-up unless explicitly approved.
  - Extend admin route tagging so each new route emits a canonical `route=/admin/*` value.
  - Include XLSX alongside CSV/JSONL for admin audit exports because the backend already supports
    the bounded evidence export contract.
- Consequences:
  - Admin operators get a usable control plane without changing the backend route topology.
  - Compliance posture stays aligned with append-only audit and non-destructive management flows.
  - Future delete/archive or admin-support dashboards can be split into separate ADRs if they need
    independent policy or retention review.
  - Architecture review: self-review completed on 2026-03-19; the change is additive, reuses
    existing backend contracts, and does not introduce a new admin namespace.

## ADR-0053
- Context: ADMIN-05 should give support staff a small observability entrypoint without opening a
  new backend namespace, adding destructive behavior, or duplicating worker-health APIs when the
  existing read surfaces already cover the needed diagnostics.
- Decision:
  - Deliver the slice as a frontend-first dashboard at `/admin/observability` under the existing
    admin guard and shell.
  - Reuse existing backend contracts only:
    - shared `GET /health` backend health probe;
    - admin audit preview via `GET /api/v1/audit/events`;
    - candidate CV parsing status via
      `GET /api/v1/candidates/{candidate_id}/cv/parsing-status`;
    - match score status via
      `GET /api/v1/vacancies/{vacancy_id}/match-scores/{candidate_id}`.
  - Keep the slice read-only and non-destructive:
    - no create/update/delete actions;
    - no new backend namespace for worker health or observability.
  - Extend frontend route tagging so the new route emits canonical `route=/admin/observability`.
- Consequences:
  - Support staff get an operational dashboard without changing backend package boundaries or the
    admin route shell.
  - Existing health, audit, and job-status contracts remain the source of truth for observability
    data.
  - If a dedicated worker-health endpoint is later justified, it should be introduced as a separate
    ADR rather than folded into this slice.
  - Architecture review: self-review completed on 2026-03-19; the change is additive, reuses
    existing read-only contracts, and does not introduce destructive behavior or a new backend
    namespace.

## ADR-0054
- Context: the previous frontend route model overloaded `/` with multiple staff experiences and had
  no public company entrypoint, which made the UI harder to understand and blocked a branded
  careers surface with checked-in visual assets.
- Decision:
  - Reopen the frontend route topology for the public and staff UX layer.
  - Introduce a public company landing page on `/`.
  - Introduce a public careers page on `/careers` that reuses the existing public candidate apply
    API contract and, at the time of this decision, kept `/candidate?interviewToken=...` for
    interview-registration links before the later candidate-route split in ADR-0058.
  - Split staff workspaces onto dedicated role routes:
    - `/hr`
    - `/manager`
    - `/accountant`
    - `/leader`
    - `/employee`
    - `/admin`
  - Change post-login redirects so staff land directly on their role page instead of the old
    overloaded `/` split.
  - Refresh the shared visual system with a new theme, public-facing hero sections, and checked-in
    image assets under the frontend project.
  - Extend canonical Sentry route tagging to include:
    - `workspace=company` on `/`
    - `workspace=careers` on `/careers`
    - `workspace=hr` on `/hr`
    - `workspace=manager` on `/manager`
    - `workspace=accountant` on `/accountant`
- Consequences:
  - Public visitors now have a clear company-first entrypoint before entering careers and CV upload.
  - Staff users now land in clearer role-specific pages after login, reducing ambiguity around the
    previous shared `/` route.
  - Existing public candidate apply and interview-registration backend contracts remain reusable, so
    the change stays frontend-first and does not require new backend namespaces.
  - Browser smoke, observability docs, and route-based test expectations must stay synchronized with
    the reopened route model.
  - Architecture review: self-review completed on 2026-03-19; the change intentionally reopens the
    previously frozen frontend route topology, but it remains additive at the backend/API boundary
    and preserves the public candidate transport model.

## ADR-0055
- Context: the HR workspace has grown into several distinct staff tasks, and keeping them all inside
  one large `/hr` page makes navigation harder to understand while still needing a compatibility
  path for the existing consolidated workbench.
- Decision:
  - Split the HR entrypoint into a small overview page on `/hr` plus focused nested routes:
    - `/hr/vacancies`
    - `/hr/pipeline`
    - `/hr/interviews`
    - `/hr/offers`
    - `/hr/workbench`
  - Keep `/hr/workbench` as the legacy consolidated route so existing deep links and direct tests
    remain viable during the transition.
  - Reuse the canonical HR workspace Sentry tag and docs references so the split remains grouped
    as one workspace in telemetry and support workflows.
- Consequences:
  - HR users get a clearer entrypoint and faster access to the specific task they need.
  - Existing workbench behavior stays available without forcing an abrupt route migration.
  - Route-based smoke tests and documentation must describe both the overview page and the retained
    workbench path.
  - Architecture review: self-review completed on 2026-03-20; the change is frontend-route-only,
    additive, and intentionally preserves the consolidated workbench for compatibility.

## ADR-0056
- Context: the public careers page already supported guided CV submission, but candidates still
  needed a browseable open-role surface that did not expose staff-only vacancy data or force a
  separate public CMS.
- Decision:
  - Add a read-only public vacancy board endpoint at `GET /api/v1/public/vacancies`.
  - Return only open vacancies in the public schema:
    - `vacancy_id`
    - `title`
    - `description`
    - `department`
    - `created_at`
    - `updated_at`
  - Load the public board on `/careers` and let candidates open the shareable vacancy
    detail/apply page on `/careers/:vacancyId`.
  - Keep the board query redirect and legacy recruiter deep links available for manual vacancy ID
    fallback.
  - Keep staff-only vacancy fields and mutation contracts out of the public API surface.
- Consequences:
  - `/careers` becomes a real public job board without widening the anonymous write surface.
  - The backend exposes one new read-only public endpoint, and the frontend must keep its typed
    client and frozen OpenAPI artifacts synchronized.
  - Recruiter deep links still work, the application workspace now lives on the shareable vacancy
    page, and public browsing is the primary entrypoint on the careers board.
  - Architecture review: self-review completed on 2026-03-20; the change is additive, read-only,
    and intentionally avoids exposing staff-only vacancy fields.

## ADR-0057
- Context: the public careers board now has enough structure to separate browsing from applying,
  and the combined board-plus-apply layout makes the public surface harder to scan and share.
- Decision:
  - Keep `/careers` as the public board that loads `GET /api/v1/public/vacancies`.
  - Add `/careers/:vacancyId` as the canonical shareable vacancy detail and application page.
  - Redirect legacy `/careers?vacancyId=...&vacancyTitle=...` links to the detail route while
    keeping `/candidate?...` legacy interview-registration links unchanged until the later
    candidate-route split in ADR-0058.
  - Keep canonical Sentry route grouping on `route=/careers` for both board and detail pages.
- Consequences:
  - Public browsing and application are now split into smaller pages without a new backend vacancy
    detail endpoint.
  - Smoke/browser verification and docs now reference the shareable vacancy route as the canonical
    careers path.
  - Legacy board query links still work via redirect, preserving recruiter-issued links and older
    local smoke fixtures.
  - Architecture review: self-review completed on 2026-03-20; the route change is additive and
    keeps backend contracts stable.

## ADR-0058
- Context: the public candidate journey had grown into a single overloaded `/candidate` surface
  that mixed apply/tracking and interview registration, while browser smoke and Sentry route tags
  needed stable canonical paths for each public flow.
- Decision:
  - Keep `/candidate` as a compatibility redirect shell only.
  - Move public apply/tracking to `/candidate/apply`.
  - Move public interview registration to `/candidate/interview/:interviewToken`.
  - Generate HR invite URLs in the canonical `/candidate/interview/:interviewToken` form while
    keeping `/candidate` as the compatibility redirect shell for legacy links.
  - Preserve legacy query links by redirecting:
    - `/candidate?vacancyId=...` -> `/candidate/apply?vacancyId=...`
    - `/candidate?interviewToken=...` -> `/candidate/interview/:interviewToken`
  - Keep canonical Sentry route tags on:
    - `route=/candidate/apply`
    - `route=/candidate/interview`
- Consequences:
  - Candidate apply and interview registration now have distinct route surfaces, which makes the
    public UX easier to understand and test.
  - Legacy links continue to work through the redirect shell, so recruiter-issued URLs do not
    break during the route transition.
  - Browser smoke can target the apply shell directly, while interview route tests can assert the
    public token flow separately.
  - Architecture review: self-review completed on 2026-03-20; the change is additive, frontend
    route-only, and preserves the existing public vacancy application and interview API contracts.
