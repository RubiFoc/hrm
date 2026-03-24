# Employee Profile, Referral, and Compensation Discovery Pass (`TASK-06-05`, `TASK-06-07`, `TASK-09-05`)

## Last Updated
- Date: 2026-03-23
- Updated by: business-analyst + coordinator

## Purpose
- This document is a planning-only BA discovery baseline for three high-priority requests:
  1. employee profiles with avatars stored in MinIO and cross-employee profile visibility;
  2. employee referral recommendations for vacancies;
  3. manager/HR compensation controls (salary raises, payroll/bonus table, salary bands).
- It does not introduce runtime/API/schema changes by itself.
- Implementation tasks (`TASK-06-06`, `TASK-06-08`, `TASK-09-06`) start only after the open BA questions in this file are resolved.

## Scope for Discovery
- Clarify business intent, actor boundaries, and acceptance criteria for all three requests.
- Freeze minimal product rules that unblock backend/frontend implementation and testing.
- Define legal/audit-sensitive constraints early to avoid rework in later slices.

## Out of Scope for This Pass
- Database migrations and API implementation.
- UI implementation details beyond baseline role and route expectations.
- External payroll system integrations not yet approved in backlog scope.

## Request 1: Employee Profiles with Avatars (MinIO)

### Business Goal
- Improve internal transparency and collaboration by allowing employees to view colleague profiles.
- Provide profile avatars as part of employee identity in role workspaces.

### Preliminary Scope Hypothesis (to confirm)
- Keep profile source of truth in employee domain.
- Store avatar binaries in MinIO; store metadata/reference in relational storage.
- Allow authenticated employees to view other employee profiles with fail-closed RBAC checks.

### BA Clarification Questions (Blocking)
| Topic | Question to Confirm | Why It Matters |
| --- | --- | --- |
| Visibility model | Are profiles visible to all active employees or restricted by department/legal entity? | Defines authorization and list/query filtering rules. |
| Profile fields | Which fields are mandatory/public/internal-only (phone, email, location, manager, bio)? | Defines schema and frontend redaction behavior. |
| Avatar policy | Max size, allowed formats, crop rules, and moderation requirements? | Defines upload validation and storage lifecycle. |
| Privacy controls | Is opt-out/field-level privacy required for employees? | Impacts UI controls and data model. |
| Lifecycle | What happens to profiles/avatars for dismissed employees? | Defines archival, retention, and visibility policy. |

### Decision Freeze (2026-03-23)
- Visibility model: profiles are visible to all active employees.
- Baseline profile fields:
  `phone`, `email`, `full_name`, `employee_id`, `location`, `manager`, `birthday_day_month`
  (without year), `avatar`, `department`, `position_title`, `subordinates`, `tenure_in_company`.
- Avatar policy: business-side upload accepts original avatar input without a fixed business size
  restriction; frontend normalizes presentation size.
- Moderation policy: no moderation gate is required; avatar updates are allowed.
- Privacy controls: employee can hide profile fields except mandatory visible fields:
  `phone`, `email`, `full_name`, `employee_id`, `location`, `manager`, `position_title`,
  `subordinates`, `tenure_in_company`, `department`.
- Dismissal lifecycle: employee profile is retained and marked as dismissed.

### Acceptance Baseline Candidate
- Employee can open a profile directory and view allowed profile cards.
- Employee can open another employee profile page with permitted fields only.
- Avatar upload/update is available under validated constraints and persists via MinIO.
- All read/write profile actions are audited with actor and target identifiers.

## Request 2: Referral Recommendations

### Business Goal
- Allow employees to recommend candidates (friends/contacts) to open vacancies.
- Improve hiring funnel quality and speed through trusted referrals.

### Preliminary Scope Hypothesis (to confirm)
- Employees create referral suggestions bound to an existing open vacancy.
- HR/manager users can review referral status and move referrals through a controlled lifecycle.
- Referral flow must be auditable and protected from duplicate/abuse patterns.

### BA Clarification Questions (Blocking)
| Topic | Question to Confirm | Why It Matters |
| --- | --- | --- |
| Eligibility | Which roles can submit referrals (`employee` only or also `manager`/`hr`)? | Defines RBAC matrix and UI availability. |
| Candidate identity | Do we require full contact data at submission or only minimal lead data? | Defines data model and validation rules. |
| Deduplication | How to handle repeats for same vacancy/person (block, merge, allow with warnings)? | Defines conflict responses and lifecycle consistency. |
| Referral lifecycle | Required statuses and transitions (`submitted`, `reviewed`, `accepted`, `rejected`, `hired`)? | Defines APIs, timeline, and reporting model. |
| Incentive policy | Do rewards exist and who tracks payout eligibility/state? | Determines coupling with compensation/accounting modules. |
| Candidate consent | Is explicit consent required before storing referral contact data? | Legal/compliance gate for personal data processing. |

### Decision Freeze (2026-03-23)
- Eligibility: all employees can submit referrals.
- Required referral payload fields: `full_name`, `phone`, `email`, `cv`.
- Deduplication policy: merge duplicates; referral bonus ownership is preserved for the first
  referrer.
- Referral lifecycle baseline: align with regular candidate lifecycle progression in the existing
  recruitment flow (no separate custom lifecycle introduced in this pass).
- Incentive policy: each vacancy defines a referral bonus amount in vacancy data.
- Consent policy: candidate consent is mandatory in the careers flow; without consent confirmation
  CV submission is blocked.

### Acceptance Baseline Candidate
- Employee can submit a referral for an open vacancy.
- HR/manager can view referrals in scoped queues and update status with reason codes.
- Duplicate-safe rules prevent inconsistent referral states.
- Referral events are available for audit and operational reporting.

## Request 3: Compensation Controls, Salary Bands, Payroll/Bonus Visibility

### Business Goal
- Give managers controlled tooling to propose or apply salary raises.
- Give managers/HR structured visibility into salary and bonus accrual tables.
- Introduce salary bands per vacancy and show employee-to-band alignment to manager/HR users.

### Preliminary Scope Hypothesis (to confirm)
- Compensation actions are role-restricted and fully audited.
- Vacancy salary bands become explicit structured fields.
- Manager/HR workspace includes read models for payroll/bonus status and salary-band alignment.

### BA Clarification Questions (Blocking)
| Topic | Question to Confirm | Why It Matters |
| --- | --- | --- |
| Authority model | Can managers apply raises directly or only submit approval requests? | Defines workflow complexity and permission model. |
| Approval chain | Which roles approve raises (HR, leader, accountant) and in what order? | Defines state machine and accountability. |
| Effective dates | Are raises immediate or date-scheduled with backdating restrictions? | Defines calculation and audit semantics. |
| Payroll table scope | Which exact columns are required for managers vs HR vs accountants? | Defines redaction and read model boundaries. |
| Bonus rules | Are bonus values manual, formula-based, or imported from other systems? | Defines data ownership and calculation logic. |
| Salary bands | Who can set/update vacancy bands and are historical versions required? | Defines schema/history requirements. |
| Currency/legal | Currency set, rounding rules, and legal constraints for salary storage? | Prevents financial inconsistencies and legal risk. |

### Decision Freeze (2026-03-23)
- Authority model: manager creates raise request only (no direct final apply).
- Approval model: final approval role is `leader`; raise request requires multiple manager
  confirmations before leader approval.
- Effective date policy: raises apply from configured effective date only; backdating is forbidden.
- Payroll/bonus table scope: same column set for manager, HR, and accountant workspaces.
- Bonus calculation policy: manual input/management.
- Salary bands: managed by HR with historical versioning enabled.
- Currency and precision: `BYN`, rounding precision to `0.01`.

### Acceptance Baseline Candidate
- Authorized manager/HR users can view salary and bonus tables in scoped workspaces.
- Raise action path enforces role permissions and approval chain defined by BA outcomes.
- Vacancy salary bands are visible and editable by authorized roles only.
- Manager/HR views show employee salary relative to current vacancy band.
- Compensation decisions and changes are auditable with reason metadata.

## Cross-Cutting Constraints to Preserve
- Keep frontend stack on React.js + TypeScript with RU/EN localization and Sentry tags.
- Keep least-privilege RBAC and immutable audit trails for sensitive operations.
- Keep documentation updates coupled with implementation tasks.
- Keep architecture changes additive; record architecture-impacting decisions in ADR/decision log.

## Discovery Deliverables (Required Before Implementation)
| Task | Deliverable | Owner |
| --- | --- | --- |
| `TASK-06-05` | Decision-complete profile/avatar requirement set and acceptance criteria | business-analyst |
| `TASK-06-07` | Decision-complete referral requirement set and lifecycle rules | business-analyst |
| `TASK-09-05` | Decision-complete compensation requirement set and approval model | business-analyst |

## Blocking Status
- BA decisions were captured with stakeholder confirmation on 2026-03-23.
- `TASK-06-05`, `TASK-06-07`, and `TASK-09-05` are decision-complete from a BA perspective.
- `TASK-06-06`, `TASK-06-08`, and `TASK-09-06` are unblocked for implementation planning.

## BA Assumptions Logged for Implementation
- "Multiple manager confirmations" is implemented as a configurable rule in application settings
  (exact minimum value to be fixed in implementation design).
- "Referral lifecycle equals regular candidate lifecycle" means referral status transitions map to
  the existing recruitment/pipeline states instead of introducing a parallel status model.
- "Any avatar size" is treated as no business cap; technical upload constraints for reliability and
  security may still be enforced during implementation.
