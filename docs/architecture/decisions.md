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
