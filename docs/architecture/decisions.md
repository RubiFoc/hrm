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
