---
name: backend-feature
description: Implement backend features with predictable delivery quality. Use when requests involve new API endpoints, business logic, schema changes, service integrations, or non-trivial backend refactoring.
---

# Backend Feature

1. Read acceptance criteria and constraints from the task contract.
2. Build the smallest end-to-end slice first (request -> logic -> persistence).
3. Add tests for critical path and one failure path.
4. Document migration or rollout risks.
5. Return a concise handoff with files changed and verification commands.

## References
- Load `references/stack.md` for project-specific conventions.

## Scripts
- Put deterministic helper automation into `scripts/`.
