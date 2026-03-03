# Agent Team Workflow

## 1. Intake
- Coordinator reads the task and fills `task-input.yaml`.
- Business analyst clarifies business goals, scope boundaries, and success metrics.
- Coordinator consolidates scope, risks, and acceptance criteria.

## 2. Analysis & Architecture
- Architect defines solution boundaries, key technical decisions, and constraints.
- Architect records non-functional concerns (reliability, security, performance).
- Architect creates or updates architecture diagrams in `docs/architecture/diagrams.md`.

## 3. Planning
- Coordinator splits work into parallelizable subtasks.
- Coordinator assigns subtasks to `architect`, `implementer`, `reviewer`, and `tester`.

## 4. Execution
- Implementer produces code and notes design decisions.
- Business analyst validates requirement coverage against business goals.
- Reviewer checks correctness, regressions, and maintainability.
- Tester validates behavior with automated/manual checks.

## 5. Handoff
- Each role returns `handoff-output.yaml`.
- Documentation updates are prepared using `docs/llm/docs-update-checklist.md`.
- Architect confirms diagram consistency and best-practice alignment.
- Coordinator merges outputs into one final delivery.

## 6. Done Criteria
- Acceptance criteria are explicitly satisfied.
- Business goals and user impact are explicitly addressed.
- Architecture decisions and tradeoffs are documented.
- Risks and follow-ups are documented.
- Test evidence is attached.
- Impacted documentation is updated in the same task.
- Architecture diagrams are updated for relevant changes.
- Best practices from `docs/engineering/best-practices.md` are explicitly followed.
