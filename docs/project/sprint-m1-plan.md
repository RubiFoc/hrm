# Sprint M1 Plan and Task Ownership

## Last Updated
- Date: 2026-03-04
- Updated by: coordinator

## Sprint Goal
Deliver Phase 1 MVP baseline (global queue items 0-24 + FE-1..FE-9) with working technical foundations, containerized platform bootstrap, core HR + candidate flows, and compliance baseline.
Current sprint acceptance target is stable local end-to-end operation on the current device (production rollout is out of scope for this stage).

## Team Roles
- architect
- business-analyst
- backend-engineer
- frontend-engineer
- data-ml-engineer
- qa-engineer
- devops-engineer

## Assignment by Workstream

| Workstream | Owner | TASK-* |
| --- | --- | --- |
| Platform containerization baseline | devops-engineer + backend-engineer + frontend-engineer | TASK-12-01 |
| Security and access baseline | architect + backend-engineer | TASK-01-01, TASK-01-02, TASK-01-03, TASK-01-04 |
| Compliance baseline | business-analyst + architect | TASK-01-05 |
| Compliance article-level mapping and evidence model | business-analyst + legal + architect | TASK-13-01, TASK-13-02 |
| Candidate and vacancy core domain | backend-engineer | TASK-03-01, TASK-02-01, TASK-02-02, TASK-02-03 |
| CV ingestion and parsing | backend-engineer + data-ml-engineer | TASK-03-02, TASK-03-03 |
| Ollama scoring pipeline | data-ml-engineer + backend-engineer | TASK-04-01, TASK-04-02, TASK-04-03 |
| Interview orchestration | backend-engineer | TASK-05-01, TASK-05-02, TASK-05-03, TASK-05-04 |
| Automation and KPI events | backend-engineer | TASK-08-01, TASK-08-02, TASK-08-03, TASK-08-04 |
| KPI data layer and snapshots | backend-engineer + data-ml-engineer | TASK-10-01, TASK-10-02 |
| Frontend platform and v1 flows | frontend-engineer | TASK-11-01, TASK-11-02, TASK-11-03, TASK-11-04, TASK-11-05, TASK-11-06, TASK-11-07, TASK-11-08, TASK-11-09 |
| Quality gates | qa-engineer | test strategy for all M1 tasks + release gate checks |
| CI/CD and environments | devops-engineer | CI baseline, environment configs, release pipeline |

## Sprint Approval
- Approved baseline: `M1` from `docs/project/tasks.md`.
- Start date: 2026-03-04.
- End date: rolling, as fast as possible with quality gates.

## Risks and Dependencies
- Docker image and compose baseline must be stable before multi-role feature streams scale.
- Legal controls matrix must progress in parallel for production readiness.
- External integrations (Ollama, Google Calendar) require stable staging credentials.
- Frontend localization (RU/EN) must be built into base routing and content model from first iteration.
- Production legal sign-off (`TASK-13-04`) is not a blocker for current local-stage acceptance, but remains mandatory before first production release.
