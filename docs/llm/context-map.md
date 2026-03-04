# LLM Context Map

Load the smallest set of documents required for the task.

## Task Type -> Required Context
| Task Type | Required Docs |
| --- | --- |
| Bug fix | `project/brief.md`, `testing/strategy.md`, `operations/runbook.md`, `engineering/best-practices.md` |
| New feature | `project/brief.md`, `architecture/overview.md`, `architecture/diagrams.md`, `testing/strategy.md`, `engineering/best-practices.md` |
| Security/Auth feature | `project/brief.md`, `project/rbac-matrix.md`, `project/auth-session-lifecycle.md`, `architecture/overview.md`, `architecture/decisions.md`, `testing/strategy.md` |
| Backend domain refactor | `architecture/decomposition.md`, `engineering/best-practices.md`, `architecture/decisions.md`, `testing/strategy.md` |
| Frontend feature | `project/brief.md`, `project/frontend-requirements.md`, `architecture/overview.md`, `architecture/diagrams.md`, `testing/strategy.md`, `engineering/best-practices.md` |
| Refactor | `architecture/overview.md`, `architecture/diagrams.md`, `architecture/decisions.md`, `testing/strategy.md`, `engineering/best-practices.md` |
| Incident response | `operations/runbook.md`, `operations/release-checklist.md` |
| Documentation update | `docs/README.md`, `ownership.md`, `llm/docs-update-checklist.md`, `engineering/best-practices.md` |

## Optional Context
- `project/glossary.md` for domain-heavy tasks.
- `project/legal-framework.md` for compliance and personal-data tasks.
- `architecture/adr-template.md` when creating a new decision.
