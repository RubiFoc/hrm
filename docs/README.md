# Documentation Index

## Purpose
This folder is the single source of truth for project context required for delivery and support.

## Structure
- `project/brief.md`: Product and business context
- `project/glossary.md`: Shared terms and definitions
- `project/requirements-questionnaire.md`: Stakeholder interview template for requirement discovery
- `project/epics.md`: Product epics, dependencies, and delivery order
- `project/tasks.md`: Task-level backlog derived from epics with priorities
- `project/sprint-m1-plan.md`: Approved M1 sprint ownership by role
- `project/frontend-requirements.md`: React.js frontend requirements and confirmed decisions
- `project/migration-notes-auth-login.md`: Client migration note for auth login contract changes
- `project/legal-framework.md`: Priority NPAs for Belarus and Russia compliance baseline
- `project/legal-controls-matrix.md`: NPA-to-controls compliance tracking matrix
- `project/rbac-matrix.md`: Phase-1 role and permission matrix baseline
- `project/auth-session-lifecycle.md`: Authentication/session lifecycle baseline and API contract
- `architecture/overview.md`: System architecture and boundaries
- `architecture/diagrams.md`: Canonical architecture and flow diagrams
- `architecture/decomposition.md`: Architecture breakdown by domains, services, and modules
- `architecture/decisions.md`: Decision log (ADR-lite)
- `architecture/adr-template.md`: Template for major decisions
- `api/openapi.frozen.json`: Frozen OpenAPI contract used for CI drift checks and frontend type generation
- `engineering/best-practices.md`: Mandatory development best practices
- `operations/runbook.md`: Operational procedures and incident basics
- `operations/release-checklist.md`: Release readiness checks
- `operations/changelog.md`: Project release and breaking-change log
- `operations/github-workflow.md`: Branching, PR, and protected branch policy
- `testing/strategy.md`: Test strategy and verification matrix
- `llm/start-here.md`: How LLM should begin work
- `llm/context-map.md`: Which docs to load per task type
- `llm/task-template.md`: Prompt template for implementation tasks
- `llm/handoff-template.md`: Delivery handoff template
- `llm/docs-update-checklist.md`: Required documentation updates per change
- `ownership.md`: Document owners and review cadence

## Update Policy
- Update docs in the same PR/task as the change.
- Keep facts close to source; avoid duplicated text.
- Prefer short sections and explicit tables over long prose.
