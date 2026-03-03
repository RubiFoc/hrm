# Project Agent Instructions

## Mission
Implement and maintain the project with predictable quality and low knowledge loss.

## Mandatory Read Order
1. `README.md`
2. `docs/README.md`
3. `docs/project/brief.md`
4. `docs/project/frontend-requirements.md`
5. `docs/architecture/overview.md`
6. `docs/architecture/diagrams.md`
7. `docs/engineering/best-practices.md`
8. `.ai/team/workflow.md`

## Non-Negotiable Rules
- Keep changes minimal and reversible.
- Update impacted docs in the same task.
- Record architecture-impacting decisions in `docs/architecture/decisions.md`.
- Update `docs/architecture/diagrams.md` when architecture/data-flow/critical workflow changes.
- Architect review is mandatory for architecture-level changes.
- Add or update verification steps in `docs/testing/strategy.md` when behavior changes.
- Apply best practices from `docs/engineering/best-practices.md` in every task.
- Keep frontend implementation on React.js + TypeScript, with Sentry monitoring and RU/EN support; do not switch stack without ADR approval.
- Do not add AI-style comments to code; keep only essential comments required for understanding non-obvious logic.
- Write detailed docstrings for public modules, classes, and functions (purpose, inputs, outputs, side effects/exceptions).
- Use git + github workflow for development changes (branching, commits, PR review).

## Task Output Contract
Always provide:
- Scope completed
- Files changed
- Verification commands run
- Residual risks
- Docs updated
- Diagram updates status

## If Context Is Missing
- Add assumptions explicitly.
- Request missing business constraints.
- Add TODO markers only with owner and due trigger.
