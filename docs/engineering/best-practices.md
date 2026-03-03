# Engineering Best Practices

## Last Updated
- Date: 2026-03-03
- Updated by: architect

These practices are mandatory for development and documentation.

## 1. Architecture and Design
- Keep bounded contexts explicit; avoid hidden cross-domain coupling.
- Define stable interfaces before implementation.
- Prefer modular monolith boundaries and asynchronous processing for heavy jobs.
- Make idempotency explicit for retried commands and background jobs.

## 2. Code Quality
- Keep changes small, reversible, and focused on one concern.
- Use clear naming and deterministic behavior for core business logic.
- Add tests for changed behavior: happy path + failure path.
- Enforce lint/format and avoid dead code.
- Write detailed docstrings for public modules, classes, and functions (purpose, parameters, returns, errors, side effects).
- Do not add AI-style comments; keep only comments that explain non-obvious intent or constraints.

## 3. Security and Compliance
- Apply least-privilege access by default.
- Encrypt sensitive data in transit and at rest.
- Record access to sensitive data in immutable audit logs.
- Follow Belarus/Russia data storage standards and retention policy.

## 4. Data and Reliability
- Keep one source of truth per entity.
- Use explicit schema migrations with rollback strategy.
- Add retries with backoff only for safe idempotent operations.
- Add circuit-breaker/fallback behavior for external integrations.

## 5. Observability and Operations
- Emit structured logs with correlation id.
- Track service metrics and error budgets for critical flows.
- Document runbooks for incidents and recoveries.
- Verify release with smoke checks and rollback readiness.

## 6. Documentation and Diagrams
- Update docs in the same task as implementation.
- Update `docs/architecture/diagrams.md` for every architecture or data flow change.
- Keep Mermaid diagrams readable and aligned with current code boundaries.
- Record architecture-impacting decisions in `docs/architecture/decisions.md`.

## 7. Definition of Done Gate
- Requirements satisfied.
- Tests and verification commands executed.
- Best-practice checks passed.
- Diagrams and architecture docs updated.
- Risks and follow-ups documented.

## 8. Version Control Workflow
- Use git for all development changes.
- Use GitHub pull requests for review and merge.
- Keep commit messages meaningful and scoped to a single change intent.
