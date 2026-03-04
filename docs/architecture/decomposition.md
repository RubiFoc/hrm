# Architecture Decomposition

## Last Updated
- Date: 2026-03-04
- Updated by: architect + backend-engineer

This document breaks the system architecture from high-level domains into smaller technical units.

## Level 1: Domain Decomposition

| Domain | Business Purpose | Main Users | Phase |
| --- | --- | --- | --- |
| Frontend Experience | Role-based web interfaces and UX orchestration on React.js + TypeScript | All roles | Phase 1-2 |
| Recruitment | Candidate-to-vacancy lifecycle, interviews, hiring decisions | HR, candidates, managers | Phase 1 |
| Employee | Employee profile and onboarding lifecycle | HR, employees, managers | Phase 2 |
| HR Operations | Process automation and operational workflows | HR, leaders | Phase 1-2 |
| Finance Adapter | Accounting-aligned exports and statuses | Accountants, leaders | Phase 2 |
| Platform | Identity, access, audit, notifications, integrations | All roles | Phase 1 |
| Core Foundation | Shared technical primitives reused by all backend domains | Backend teams | Phase 1-2 |
| Intelligence | CV analysis and recommendation support | HR, managers | Phase 1 |
| Analytics | KPI and operational reporting | HR, leaders, managers | Phase 2 |

## Level 2: Service Decomposition

| Service | Domain | Responsibilities | Public Interface |
| --- | --- | --- | --- |
| Frontend App (React.js + TypeScript) | Frontend Experience | Role workspaces, routing, forms, i18n (ru/en), client-side state, API integration | Browser UI |
| Frontend Telemetry Service | Frontend Experience | Sentry SDK integration and client monitoring | Sentry |
| Core Shared Package | Core Foundation | Reusable ORM base, env parsers, shared errors, common utils | Python imports |
| Auth and Access Service | Platform | Authentication, role policies, session validation | REST/Token |
| Vacancy Service | Recruitment | Vacancy CRUD, requirements and stages | REST |
| Candidate Service | Recruitment | Candidate profiles, attachments, status transitions | REST |
| CV Processing Service | Intelligence | Document extraction, normalized CV structure | Async jobs + REST status |
| Match Scoring Service | Intelligence | Candidate-vacancy scoring via Ollama adapter | Async jobs |
| Interview Service | Recruitment | Interview planning, feedback capture, fairness guardrails | REST |
| Calendar Sync Service | Platform | Google Calendar synchronization and retries | Async jobs + webhooks |
| Hiring Decision Service | Recruitment | Offer/reject decisions and transition to onboarding | REST |
| Employee Profile Service | Employee | Employee identity and profile lifecycle | REST |
| Onboarding Service | Employee | Onboarding templates, tasks and status tracking | REST + async |
| Workflow Automation Service | HR Operations | Rule engine and triggered HR tasks | Event-driven |
| Notification Service | Platform | Email/in-app notifications and templates | Async jobs |
| Audit Service | Platform | Immutable security and business audit logs | Event ingestion |
| Reporting Service | Analytics | KPI aggregation and dashboards | Read APIs |
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
| Automation executions | Workflow Automation Service | PostgreSQL | Used for KPI and incident analysis |
| Audit events | Audit Service | Append-only storage | Compliance evidence |
| Auth denylist markers (`jti`/`sid`) | Auth and Access Service | Redis | Valid tokens are not persisted server-side |

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

### Phase 2: Manager/Employee/Accountant/Leader Expansion
- Frontend App (React.js + TypeScript) expansion: manager/employee/accountant/leader workspaces
- Employee Profile Service
- Onboarding Service
- Workflow Automation Service (expanded rules)
- Reporting Service
- Accounting Export Service
- Notification Service (full template coverage)

## Ownership Decomposition (Suggested)

| Team Slice | Services |
| --- | --- |
| Recruitment Slice | Vacancy, Candidate, Interview, Hiring Decision |
| Intelligence Slice | CV Processing, Match Scoring |
| Platform Slice | Auth and Access, Calendar Sync, Notification, Audit |
| People Ops Slice | Employee Profile, Onboarding, Workflow Automation |
| Data Slice | Reporting, KPI datasets |
