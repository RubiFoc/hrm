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
    - `/` -> `workspace=hr`
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
  - Freeze the planning baseline in `docs/project/interview-planning-pass.md` before any interview implementation work starts.
  - Keep one non-terminal interview per `vacancy_id + candidate_id`; use `schedule_version` on the same row for reschedules.
  - Keep candidate access anonymous through a public opaque invitation token stored hashed in the backend and bound to `interview_id + schedule_version`.
  - Keep the existing route topology:
    - HR interview controls extend `/`
    - candidate interview registration extends `/candidate` through `?interviewToken=<token>`
  - Do not introduce candidate auth, new CORS rules, or a new route tree in the interview slice.
  - Separate business interview state from calendar execution state:
    - interview `status`: `pending_sync`, `awaiting_candidate_confirmation`, `confirmed`, `reschedule_requested`, `cancelled`, `completed`
    - `calendar_sync_status`: `queued`, `running`, `synced`, `conflict`, `failed`
  - Treat Google Calendar sync as staff-calendar orchestration only for the next slice; candidate invitation delivery remains manual through `candidate_invite_url` until a notification service exists.
  - Freeze the minimal public/backend API set around:
    - HR create/list/get/reschedule/cancel/resend-invite endpoints
    - public token read/confirm/request-reschedule/cancel endpoints
  - Auto-append one `shortlist -> interview` pipeline transition on first successful interview sync when needed.
- Consequences:
  - Interview implementation can proceed without the implementer making hidden product decisions.
  - Existing anonymous candidate transport assumptions remain intact.
  - Notification delivery is intentionally deferred, so the next slice remains feasible in local-stage scope.
