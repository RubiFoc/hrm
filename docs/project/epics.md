# Product Epics

## Last Updated
- Date: 2026-03-03
- Updated by: architect

## Planning Baseline
- Jurisdictions: Belarus and Russia.
- Legal baseline: `docs/project/legal-framework.md`.
- Mandatory integrations: Ollama, Google Calendar.
- Mandatory frontend stack: React.js + TypeScript.
- Frontend localization for v1: ru + en.
- Frontend browser target for v1: Google Chrome.
- Frontend monitoring: Sentry.
- Mobile application is out of scope.
- Delivery order: Phase 1 (HR + Candidates), then Phase 2 (Managers + Employees + Accountants + Leaders).
- KPI target for v1: share of automated HR operations = 70%.

## Epic Portfolio

| Epic ID | Epic | Business Value | Primary Users | Phase | Priority |
| --- | --- | --- | --- | --- | --- |
| EPIC-01 | Identity, Roles, and Data Compliance Foundation | Protect sensitive data and enable controlled access | All roles | Phase 1 | P0 |
| EPIC-11 | React.js Frontend Foundation and Role UX | Deliver consistent and secure role-based user experience | All roles | Phase 1-2 | P0 |
| EPIC-02 | Vacancy and Recruitment Pipeline Management | Standardize and accelerate candidate flow | HR, Managers | Phase 1 | P0 |
| EPIC-03 | Candidate Profile and CV Intake | Centralize candidate data and documents | HR, Candidates | Phase 1 | P0 |
| EPIC-04 | AI CV Analysis and Match Scoring (Ollama) | Improve shortlist quality and speed | HR, Managers | Phase 1 | P0 |
| EPIC-05 | Interview Scheduling and Fairness Controls | Reduce scheduling friction and interview bias | HR, Candidates, Managers | Phase 1 | P0 |
| EPIC-06 | Offer-to-Hire and Employee Profile Creation | Convert accepted candidates into employees cleanly | HR, Employees | Phase 2 | P1 |
| EPIC-07 | Onboarding Workflows and Progress Tracking | Simplify onboarding and reduce manual follow-up | HR, Employees, Managers | Phase 2 | P1 |
| EPIC-08 | HR Workflow Automation Engine | Increase percentage of automated HR operations | HR, Leaders | Phase 1-2 | P0 |
| EPIC-09 | Manager, Leader, and Accountant Workspaces | Reduce operational load outside HR team | Managers, Leaders, Accountants | Phase 2 | P1 |
| EPIC-10 | KPI Reporting and Audit Evidence | Measure outcomes and support compliance | HR, Leaders, Auditors | Phase 1-2 | P0 |

## Epic Dependencies

| Epic | Depends On |
| --- | --- |
| EPIC-11 | EPIC-01 |
| EPIC-02 | EPIC-01, EPIC-11 |
| EPIC-03 | EPIC-01, EPIC-11 |
| EPIC-04 | EPIC-03 |
| EPIC-05 | EPIC-02, EPIC-03, EPIC-11 |
| EPIC-06 | EPIC-02, EPIC-03, EPIC-05 |
| EPIC-07 | EPIC-06 |
| EPIC-08 | EPIC-01, EPIC-02, EPIC-06 |
| EPIC-09 | EPIC-01, EPIC-06, EPIC-07, EPIC-11 |
| EPIC-10 | EPIC-01, EPIC-02, EPIC-08 |

## Definition of Done by Epic

### EPIC-01: Identity, Roles, and Data Compliance Foundation
- Role-based access is enforced for all user groups.
- Access to sensitive personal data is audited.
- Data retention and storage policies are defined for Belarus/Russia scope.

### EPIC-11: React.js Frontend Foundation and Role UX
- Frontend is implemented with React.js + TypeScript and shared architecture conventions.
- Role-based navigation and protected routes are implemented.
- Candidate self-service v1 flows are implemented (CV upload, profile confirmation, interview registration).
- Core phase workspaces are delivered with consistent form/error behavior.
- Frontend observability through Sentry and accessibility baseline are in place.
- RU/EN localization and Chrome support are verified for critical v1 journeys.

### EPIC-02: Vacancy and Recruitment Pipeline Management
- HR can create/manage vacancies and pipeline stages.
- Candidate transitions are tracked with timestamps and status history.
- Managers can review assigned vacancies and candidate pools.

### EPIC-03: Candidate Profile and CV Intake
- Candidate profile schema is stable and validated.
- CV files are stored securely with metadata and parsing status.
- HR can search/filter candidates by vacancy-relevant criteria.

### EPIC-04: AI CV Analysis and Match Scoring (Ollama)
- CV-to-vacancy scoring runs asynchronously through Ollama.
- Score output includes confidence and explainable fields.
- Low-confidence cases are routed to manual HR review.

### EPIC-05: Interview Scheduling and Fairness Controls
- Interview slots sync with Google Calendar.
- Structured feedback form is mandatory before decision stage.
- Interview rubric enforces consistent evaluation criteria.

### EPIC-06: Offer-to-Hire and Employee Profile Creation
- Accepted candidate can be converted to employee profile.
- Offer and acceptance states are recorded and traceable.
- Employee profile creation triggers onboarding workflow.

### EPIC-07: Onboarding Workflows and Progress Tracking
- Onboarding checklist templates are configurable.
- Task assignment and completion status are visible to HR/manager.
- New employee receives required onboarding information.

### EPIC-08: HR Workflow Automation Engine
- Rule-based automation executes key HR operations.
- Execution logs capture trigger, action, result, and failures.
- Automation KPI pipeline supports measurement toward 70% target.

### EPIC-09: Manager, Leader, and Accountant Workspaces
- Managers get team-level hiring and onboarding visibility.
- Leaders get operational and KPI summary dashboards.
- Accountants get controlled exports for finance operations.

### EPIC-10: KPI Reporting and Audit Evidence
- KPI dashboards include automation share metric.
- Audit trail supports role actions and critical lifecycle events.
- Monthly KPI snapshot is reproducible and reviewable.

## Recommended Build Order
1. EPIC-01
2. EPIC-11
3. EPIC-02
4. EPIC-03
5. EPIC-04
6. EPIC-05
7. EPIC-08 (core set)
8. EPIC-06
9. EPIC-07
10. EPIC-09
11. EPIC-10 (full scope)

## Execution Mapping
- Task-level decomposition, dependencies, and global priority queue are documented in `docs/project/tasks.md`.
