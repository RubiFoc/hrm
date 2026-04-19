# Architecture Decomposition

## Last Updated
- Date: 2026-04-06
- Updated by: backend-engineer + frontend-engineer

This document breaks the system architecture from high-level domains into smaller technical units.
The recruitment and CV-analysis scope is profession-agnostic and must support workers across
industries rather than only IT roles.

## Level 1: Domain Decomposition

| Domain | Business Purpose | Main Users | Phase |
| --- | --- | --- | --- |
| Frontend Experience | Role-based web interfaces and UX orchestration on React.js + TypeScript | All roles | Phase 1-2 |
| Recruitment | Candidate-to-vacancy lifecycle, interviews, hiring decisions | HR, candidates, managers | Phase 1 |
| Employee | Employee profile and onboarding lifecycle | HR, employees, managers | Phase 2 |
| HR Operations | Process automation and operational workflows | HR, leaders | Phase 1-2 |
| Finance Adapter | Compensation controls, payroll/bonus visibility, and accounting-aligned exports | Accountants, HR, managers, leaders | Phase 2 |
| Platform | Identity, access, audit, notifications, integrations | All roles | Phase 1 |
| Reference Data | Shared company directories (departments, catalogs) | All staff roles | Phase 1 |
| Core Foundation | Shared technical primitives reused by all backend domains | Backend teams | Phase 1-2 |
| Intelligence | CV analysis and recommendation support | HR, managers | Phase 1 |
| Analytics | KPI and operational reporting (monthly snapshots in v1) | Admin, leaders | Phase 1-2 |

## Level 2: Service Decomposition

| Service | Domain | Responsibilities | Public Interface |
| --- | --- | --- | --- |
| Frontend App (React.js + TypeScript) | Frontend Experience | Role workspaces, routing, forms, i18n (ru/en), client-side state, API integration | Browser UI |
| Frontend Telemetry Service | Frontend Experience | Sentry SDK integration and client monitoring | Sentry |
| Core Shared Package | Core Foundation | Reusable ORM base, env parsers, shared errors, common utils | Python imports |
| Auth and Access Service | Platform | Authentication, role policies, session validation | REST/Token |
| Department Directory Service | Reference Data | Department reference CRUD and shared list/read access | REST |
| Vacancy Service | Recruitment | Vacancy CRUD, requirements and stages | REST |
| Candidate Service | Recruitment | Candidate profiles, attachments, status transitions | REST |
| CV Processing Service | Intelligence | Document extraction and profession-agnostic normalized CV structure (workplaces, held positions, education, titles, dates, generic skills) | Async jobs + REST status |
| Match Scoring Service | Intelligence | Candidate-vacancy scoring via Ollama adapter | Async jobs |
| Interview Service | Recruitment | Interview planning, feedback capture, fairness guardrails | REST |
| Calendar Sync Service | Platform | Google Calendar synchronization and retries | Async jobs + webhooks |
| Hiring Decision Service | Recruitment | Offer/reject decisions and transition to onboarding | REST |
| Employee Profile Service | Employee | Employee identity and profile lifecycle | REST |
| Onboarding Service | Employee | Onboarding templates, tasks and status tracking | REST + async |
| Workflow Automation Service | HR Operations | Rule engine and triggered HR tasks | Event-driven |
| Notification Service | Platform | Recipient-scoped in-app notifications and on-demand digests in v1; outbound templates/channels later | REST |
| Audit Service | Platform | Immutable security and business audit logs + admin-only evidence query API | Event ingestion + admin read APIs |
| Reporting Service | Analytics | Monthly KPI snapshots (admin rebuild, leader/admin read) and dashboards | Read/maintenance APIs |
| Compensation Controls Service | Finance Adapter | Raise approvals, salary-band governance, manual bonuses, unified compensation table read model | REST |
| Accounting Export Service | Finance Adapter | Controlled export for accounting workflows | File/API adapter |

## Level 3: Internal Module Decomposition (Priority Services)

### 1. Candidate Service
- API Module:
  handle candidate CRUD, status transitions, and validation.
- Document Module:
  store document references and metadata.
- Compliance Module:
  enforce retention and access constraints.
- Event Module:
  publish lifecycle events for scoring, interviews, and reporting.

### 2. Match Scoring Service
- Request Builder Module:
  build normalized prompt payload from CV and vacancy profile.
- Ollama Adapter Module:
  execute model calls and manage model/version routing.
- Post-Processing Module:
  normalize model output to stable score schema.
- Quality Guard Module:
  detect low-confidence responses and trigger manual review.

### 3. Interview Service
- Scheduling Module:
  create interview slots and participant assignments.
- Calendar Orchestration Module:
  integrate with Calendar Sync service and track reconciliation state.
- Feedback Module:
  collect structured interviewer feedback and decision signals.
- Fairness Control Module:
  enforce standardized interview rubric and missing-feedback checks.

### 4. Workflow Automation Service
- Rules Module:
  evaluate trigger conditions.
- Executor Module:
  dispatch automated tasks and retries.
- Policy Module:
  restrict automation based on role and data sensitivity.
- Monitoring Module:
  emit execution metrics and failure events.

### 5. Auth and Access Service
- Token Issuance Module:
  issue signed short-lived access tokens and rotating refresh tokens.
- Denylist Module:
  store only revoked token/session markers in Redis (`jti` + `sid`).
- Token Validation Module:
  validate bearer signature/claims and enforce denylist checks.
- Access Policy Module:
  map validated role claims to RBAC permission checks.

### 6. Notification Service
- Recipient Resolver Module:
  map vacancy ownership and onboarding assignment changes to manager/accountant staff recipients.
- In-App Store Module:
  persist deduped recipient-scoped notification rows.
- Digest Read Model Module:
  compute unread counts plus manager/accountant task or vacancy summary counters on demand.
- Delivery Policy Module:
  keep v1 fail-closed and in-app only; defer outbound channels/templates.

## Data Decomposition

| Data Group | Primary Owner Service | Storage Type | Notes |
| --- | --- | --- | --- |
| Vacancies and pipeline stages | Vacancy Service | PostgreSQL | Source of truth for recruitment flow |
| Candidate profiles and statuses | Candidate Service | PostgreSQL | Personal data controls required |
| CV files and attachments | Candidate Service | Object storage | Encrypted and versioned |
| Match scores and explanations | Match Scoring Service | PostgreSQL | Store model version and confidence |
| Interview events and feedback | Interview Service | PostgreSQL | Audit-linked |
| Employee profiles | Employee Profile Service | PostgreSQL | Created post-hire |
| Onboarding tasks | Onboarding Service | PostgreSQL | Linked to employee profile |
| In-app notifications | Notification Service | PostgreSQL | Recipient-scoped, deduped, and read-tracked |
| Departments directory | Department Directory Service | PostgreSQL | Canonical reference data for department names |
| KPI snapshots | Reporting Service | PostgreSQL | Monthly snapshots keyed by `period_month + metric_key`, rebuilt on demand |
| Automation executions | Workflow Automation Service | PostgreSQL | Used for KPI and incident analysis |
| Audit events | Audit Service | Append-only storage | Compliance evidence |
| Auth denylist markers (`jti`/`sid`) | Auth and Access Service | Redis | Valid tokens are not persisted server-side |
| Compensation raises/confirmations | Compensation Controls Service | PostgreSQL | Manager quorum + leader decision trail |
| Salary band history | Compensation Controls Service | PostgreSQL | Append-only, HR-only governance |
| Manual bonus entries | Compensation Controls Service | PostgreSQL | Manual updates with audit evidence |

## Integration Decomposition

| Integration | Adapter Service | Direction | Failure Strategy |
| --- | --- | --- | --- |
| Ollama | Match Scoring Service | Outbound | retries + fallback to manual review |
| Google Calendar | Calendar Sync Service | Bi-directional | idempotent sync + conflict reconciliation |

## Phase Decomposition

### Phase 1: HR + Candidate (MVP Core)
- Core Shared Package baseline (`core/models`, `core/config`, `core/errors`, `core/utils`)
- Frontend App (React.js + TypeScript) foundation: app shell, auth-aware routing, HR/Candidate workspaces
- Frontend baseline: shared UI library, i18n (ru/en), candidate self-service (CV upload, profile confirmation, interview registration), Chrome target support
- Auth and Access Service
- Vacancy Service
- Candidate Service
- CV Processing Service
- Match Scoring Service (Ollama)
- Interview Service
- Calendar Sync Service (Google Calendar)
- Audit Service
- Reporting Service (monthly KPI snapshot foundation, admin rebuild + leader/admin read API)

### Phase 2: Manager/Employee/Accountant/Leader Expansion
- Frontend App (React.js + TypeScript) expansion: manager/employee/accountant/leader workspaces
- Employee Profile Service
- Onboarding Service
- Workflow Automation Service (expanded rules)
- Reporting Service (leader/manager dashboards and expanded KPI scope)
- Compensation Controls Service (raises, salary bands, bonuses, unified compensation table)
- Accounting Export Service
- Notification Service (in-app + digest baseline, outbound/template coverage later)

## Ownership Decomposition (Suggested)

| Team Slice | Services |
| --- | --- |
| Recruitment Slice | Vacancy, Candidate, Interview, Hiring Decision |
| Intelligence Slice | CV Processing, Match Scoring |
| Platform Slice | Auth and Access, Calendar Sync, Notification, Audit |
| People Ops Slice | Employee Profile, Onboarding, Workflow Automation |
| Finance Slice | Compensation Controls, Accounting Export |
| Data Slice | Reporting, KPI datasets |
