# Employee Profile, Referral, and Compensation Discovery Pass (`TASK-06-05`, `TASK-06-07`, `TASK-09-05`)

## Last Updated
- Date: 2026-03-27
- Updated by: business-analyst + architect + coordinator

## Purpose
- This document is a planning-only BA discovery baseline for three high-priority requests:
  1. employee profiles with avatars stored in MinIO and cross-employee profile visibility;
  2. employee referral recommendations for vacancies;
  3. manager/HR compensation controls (salary raises, payroll/bonus table, salary bands).
- It does not introduce runtime/API/schema changes by itself.
- `TASK-06-05` is finalized in this revision as implementation-ready `clarified/frozen`.
- Implementation tasks (`TASK-06-06`, `TASK-06-08`, `TASK-09-06`) start only after the open BA
  questions in this file are resolved.

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

### `TASK-06-05` Clarification Status
- Status: `clarified/frozen` (2026-03-27).
- Tracking: GitHub issue `#173` (clarification pass).
- Implementation dependency released: `TASK-06-06` (GitHub issue `#174`) is ready for execution
  with the frozen rules below.

### Decision Table (Implementation-Ready, Frozen)

| Decision Area | Frozen Rule for `TASK-06-06` | Fail-Closed / Compliance Note |
| --- | --- | --- |
| Profile visibility model | Employee directory and profile read are internal-only and available to authenticated active staff roles (`admin`, `hr`, `manager`, `employee`, `leader`, `accountant`) through explicit employee-directory permissions. Public/candidate access is forbidden. | Missing token, inactive account, unknown role, or missing permission returns deny (`401/403`); do not fallback to permissive read. |
| Subject scope | Directory includes only active employees by default. Dismissed employees are excluded from default directory cards. | Historical dismissed profiles remain retained in storage for audit/legal needs; visibility to dismissed records stays staff-admin/HR only on dedicated staff routes. |
| Baseline profile fields | Canonical field set for profile payload: `full_name`, `employee_id`, `department`, `position_title`, `manager`, `location`, `tenure_in_company`, `subordinates`, `phone`, `email`, `birthday_day_month` (without year), `avatar`. | Do not expose birth year or additional personal identifiers in employee directory/profile APIs for this slice. |
| Privacy controls | Employee can set per-field visibility only for optional fields: `phone`, `email`, `birthday_day_month`. Mandatory visible fields cannot be hidden: `full_name`, `employee_id`, `department`, `position_title`, `manager`, `location`, `tenure_in_company`, `subordinates`, `avatar`. | Privacy flags are enforced server-side on every read response. Unauthorized role or out-of-scope target never receives hidden values. |
| Avatar upload formats | Allowed avatar MIME types: `image/jpeg`, `image/png`, `image/webp`. | Unsupported MIME type is rejected (`415/422`) and audited as failure. |
| Avatar limits | Technical reliability limit is fixed: max upload size `10 MiB` per avatar object; one active avatar per employee profile. | Oversize upload is rejected fail-closed (`413`); no implicit resizing on backend required for acceptance. |
| Avatar processing and rendering | Business keeps original image upload semantics (no fixed business crop requirement); frontend normalizes display size in UI cards/pages. | Backend stores metadata and immutable object key reference; UI-only resizing must not alter stored original binary. |
| Avatar storage/read policy | Avatar binaries are stored in MinIO; relational row stores object key + metadata. Avatar read returns controlled backend response (download stream or short-lived signed URL), never raw bucket listing. | Direct anonymous object-store reads are forbidden. Expired/invalid read tokens must fail closed. |
| Avatar ownership and write scope | Avatar create/update/delete is self-service for the profile owner only; admin/HR override is allowed only through privileged staff route for legal/support operations. | Cross-user avatar writes are forbidden by default and audited as denied. |
| Moderation policy | No pre-moderation queue is required for this slice. Reactive moderation is allowed: admin/HR can remove avatar and set default fallback on policy breach. | Keep moderation actions auditable with actor, target, and reason code. |
| Audit and legal boundaries | Audit events are mandatory for employee-directory list/read, profile read, profile privacy updates, avatar upload/update/delete/read-deny. | Audit payload must include actor id, target employee id, result (`allowed/denied` or `success/failure`), and reason code for denials/failures. |
| PII minimization boundary | Employee directory/profile exposure is limited to the frozen field set above and must not widen manager workspace candidate PII rules or public candidate endpoints. | Any contract widening beyond the frozen field set requires new BA clarification and ADR update before implementation. |

### Implementation-Ready Acceptance Criteria for `TASK-06-06`
1. Authenticated internal user with allowed role can open employee directory and read only active
   employee cards with the frozen mandatory fields.
2. Attempt to read directory/profile without token, with unsupported role, or without permission is
   denied (`401/403`) and audited.
3. Profile page enforces privacy flags:
   `phone`, `email`, and `birthday_day_month` are hidden when owner disabled visibility; mandatory
   fields stay visible.
4. Avatar upload accepts only `jpeg/png/webp` and file size up to `10 MiB`; invalid uploads fail
   with stable error codes and audit records.
5. Successful avatar upload persists MinIO object + relational metadata link and updates the
   profile’s active avatar reference.
6. Avatar read path is protected (no anonymous bucket/object read), supports only authorized access,
   and fails closed on expired/invalid read token.
7. Employee can update/delete only own avatar and own privacy flags; cross-user write attempts are
   denied and audited.
8. Dismissed employees are excluded from default directory visibility while retained for
   audit/legal history through privileged staff operations.
9. All profile/avatar actions produce immutable audit events with actor/target/result/reason.

### Explicit Non-Goals for `TASK-06-06`
- No social graph, follows, likes, comments, or messaging in employee profiles.
- No AI image moderation/classification pipeline.
- No public internet exposure of employee directory/profile pages.
- No compensation/payroll fields inside employee public profile payload.
- No change to existing candidate/public-apply transport, manager candidate snapshot policy, or
  auth/session model.

### Risks and Follow-Ups
- Upload limits and signed-read TTL values are fixed for this slice but may require tuning after
  operational telemetry review.
- Reactive moderation without pre-screening reduces implementation cost but can increase moderation
  response pressure on HR/admin; monitor incident frequency post-release.
- If stakeholder policy later requires department/legal-entity segmentation, this will require a
  new BA clarification and follow-up ADR before widening read filters.

## Request 2: Referral Recommendations

### Business Goal
- Allow employees to recommend candidates (friends/contacts) to open vacancies.
- Improve hiring funnel quality and speed through trusted referrals.

### Preliminary Scope Hypothesis (to confirm)
- Employees create referral suggestions bound to an existing open vacancy.
- HR/manager users can review referral status and move referrals through a controlled lifecycle.
- Referral flow must be auditable and protected from duplicate/abuse patterns.

### `TASK-06-07` Clarification Status
- Status: `clarified/frozen` (2026-03-27).
- Tracking: backlog queue in `docs/project/tasks.md` (`TASK-06-07` -> `TASK-06-08`).
- Runtime alignment note: repo-backed `TASK-06-08` implementation already exists locally and must
  remain aligned with the frozen rules below.

### Decision Table (Implementation-Ready, Frozen)

| Decision Area | Frozen Rule for `TASK-06-08` | Fail-Closed / Compliance Note |
| --- | --- | --- |
| Submission eligibility | Referral submission is available to the authenticated `employee` role through dedicated employee self-service flow. `hr` and `manager` roles are reviewers, not referral submitters, in this baseline. | Out-of-scope role attempts to submit are denied and audited. |
| Vacancy scope | Referral must be bound to an existing open vacancy. Vacancy-less or closed-vacancy submissions are rejected. | Do not persist referral contact data when vacancy validation fails. |
| Required referral payload | Required fields: `full_name`, `phone`, `email`, `cv`. | Missing required identity/contact/CV fields return stable validation error and create no partial referral row. |
| Candidate consent | Referrer must confirm candidate consent before storing contact data and CV. | Submission without consent confirmation is blocked fail-closed and audited as failure/validation deny. |
| Deduplication policy | Dedupe key is `(vacancy_id, email)`. Duplicate referrals merge into the same candidate/referral linkage. | Duplicate merge must preserve one consistent record and must not create parallel candidate/referral identities. |
| Bonus ownership policy | Referral bonus ownership is preserved for the first referrer on the deduped vacancy+candidate pair. Later duplicate referrals do not overwrite ownership. | Bonus-owner overwrite is forbidden by default and audited when rejected/merged. |
| Review and lifecycle model | Do not introduce a separate referral status machine. Referral review maps to the existing recruitment pipeline lifecycle; review outcomes move candidate through canonical pipeline stages. | Keep state model single-source-of-truth in existing pipeline transitions; no parallel custom referral statuses. |
| Reviewer scope | `hr` and `manager` can read/review referrals only in their scoped workspaces and according to existing role visibility. | Unauthorized read/review attempts are denied and audited. |
| Incentive policy boundary | Each vacancy defines referral bonus amount in vacancy data; payout/accounting execution remains outside this slice. | Do not add bonus-payment engine or payroll side effects in referral slice. |
| Audit and legal boundaries | Audit events are mandatory for submit, read, review, dedupe merge, and denied referral operations. | Audit payload includes actor, target vacancy/candidate/referral identifiers, result, and reason code on denied/failure paths. |
| Anti-abuse baseline | Duplicate-safe merge, mandatory consent flag, vacancy binding, and staff review scopes are the minimum anti-abuse controls for this slice. | No anonymous public referral endpoint and no permissive duplicate creation fallback. |

### Implementation-Ready Acceptance Criteria for `TASK-06-08`
1. Authenticated employee can submit referral only for an existing open vacancy with required
   fields `full_name`, `phone`, `email`, and `cv`.
2. Submission without confirmed candidate consent is rejected and audited.
3. Duplicate referral on the same `(vacancy_id, email)` merges safely instead of creating
   inconsistent parallel records.
4. First referrer bonus ownership is preserved across later duplicates and is never silently
   overwritten.
5. HR and manager can review referrals in scoped queues without a separate referral state machine;
   review actions stay aligned with canonical recruitment pipeline transitions.
6. Unauthorized roles cannot submit or review referrals outside the frozen scope.
7. Referral events are auditable for submit, read, review, merge, and deny paths.
8. Bonus payout/accounting processing is not performed inside referral workflow.

### Explicit Non-Goals for `TASK-06-08`
- No public anonymous referral submission endpoint.
- No separate referral lifecycle/status model outside the recruitment pipeline.
- No automatic bonus payout, accounting export, or payroll side effects.
- No support for referral submission without vacancy binding.
- No candidate-auth requirement or change to existing public apply transport.

### Risks and Follow-Ups
- Email-based dedupe is simple and deterministic but can miss duplicates when the same person uses
  multiple e-mail addresses.
- Consent is captured as flow confirmation in this slice; stronger documentary consent evidence may
  require a follow-up compliance decision.
- Bonus ownership is frozen, but payout processing remains outside the slice and needs later
  finance-policy synchronization if automated compensation workflows are introduced.

## Request 3: Compensation Controls, Salary Bands, Payroll/Bonus Visibility

### Business Goal
- Give managers controlled tooling to propose or apply salary raises.
- Give managers/HR structured visibility into salary and bonus accrual tables.
- Introduce salary bands per vacancy and show employee-to-band alignment to manager/HR users.

### Preliminary Scope Hypothesis (to confirm)
- Compensation actions are role-restricted and fully audited.
- Vacancy salary bands become explicit structured fields.
- Manager/HR workspace includes read models for payroll/bonus status and salary-band alignment.

### `TASK-09-05` Clarification Status
- Status: `clarified/frozen` (2026-03-27).
- Tracking: backlog queue in `docs/project/tasks.md` (`TASK-09-05` -> `TASK-09-06`).
- Implementation dependency released: `TASK-09-06` is ready for execution with the frozen rules
  below.

### Decision Table (Implementation-Ready, Frozen)

| Decision Area | Frozen Rule for `TASK-09-06` | Fail-Closed / Compliance Note |
| --- | --- | --- |
| Authority model | Manager can create raise request only; direct salary apply by manager is forbidden. | Any manager attempt to bypass request flow is denied and audited. |
| Approval chain | Raise request requires manager confirmation quorum and final `leader` approval. Quorum is configurable via settings, minimum `2` distinct manager confirmations (`>=2`, default `2`). | Request cannot transition to `approved` without quorum + leader action; any missing step returns `409`/domain error and leaves salary unchanged. |
| Approval separation | Request initiator cannot perform final leader approval and cannot self-confirm twice. | Distinct actor checks are mandatory and audited on every transition. |
| Effective date policy | Raise takes effect from explicit `effective_date`; backdating is forbidden. | `effective_date < today` is rejected fail-closed (`422`) with reason code; no retroactive recalculation in this slice. |
| Salary bands governance | Vacancy salary bands are created/updated by `hr` only and versioned historically (append-only history). | Manager/leader/accountant band-write attempts are denied and audited. |
| Payroll/bonus table read scope | Manager, HR, and accountant use the same read column set for compensation view. | Read access remains RBAC-gated; unauthorized role or out-of-scope employee returns `403/404` and audit deny record. |
| Payroll/bonus baseline columns | Frozen baseline columns: `employee_id`, `full_name`, `department`, `position_title`, `currency`, `base_salary`, `bonus_amount`, `bonus_period_month`, `salary_band_min`, `salary_band_max`, `band_alignment_status`, `last_raise_effective_date`, `last_raise_status`. | Do not expose bank account details, tax identifiers, passport data, or other extra PII in this slice. |
| Bonus policy | Bonus values are manual entries/updates in controlled staff workflows; no formula engine/import integration in this slice. | Missing required bonus inputs fails validation; no silent defaults for payout-critical fields. |
| Currency and precision | Currency is fixed to `BYN`; monetary precision fixed to `0.01`. | Mixed/missing currency values are rejected fail-closed; rounding must be deterministic server-side. |
| Audit and legal boundaries | Audit events are mandatory for compensation read, raise request create/confirm/approve/reject, salary-band update, and bonus update actions. | Audit record includes actor, target employee/vacancy, result, reason code, and before/after monetary snapshot for write operations. |
| PII minimization and non-leakage | Compensation data remains internal staff-only and must not leak to employee public profile pages or candidate/public routes. | Any contract widening outside compensation workspace requires new BA clarification + ADR update. |

### Implementation-Ready Acceptance Criteria for `TASK-09-06`
1. Manager can create raise request only within authorized employee scope; direct salary update path
   is unavailable.
2. Raise request lifecycle enforces configurable manager quorum (`>=2`, default `2`) and final
   leader approval before status `approved`.
3. Requests without quorum or without leader approval cannot change effective salary values.
4. Backdated raise requests are rejected with stable validation errors; future-dated requests are
   allowed.
5. HR can create/update salary bands per vacancy with historical versioning; previous versions stay
   queryable.
6. Manager/HR/accountant can read the same compensation table columns and see deterministic
   band-alignment status (`below_band`, `within_band`, `above_band`).
7. Bonus values are manually maintained via controlled staff actions and reflected in compensation
   table reads.
8. Currency is always `BYN` and monetary values are rounded to `0.01` deterministically.
9. Unauthorized roles and out-of-scope read/write attempts are denied fail-closed and audited.
10. Employee public profile and public candidate routes do not expose compensation fields.

### Explicit Non-Goals for `TASK-09-06`
- No external payroll or ERP integrations.
- No automatic bonus formulas, KPI-based bonus engine, or AI compensation recommendations.
- No retroactive payroll recalculation for past periods.
- No multi-currency compensation storage or FX conversion.
- No compensation data exposure in employee public directory/profile pages.

### Risks and Follow-Ups
- Quorum logic needs operational guidance for small org structures; default `2` may need policy
  override in constrained teams.
- Manual bonus entry improves control but increases operational workload and error risk without
  import automation.
- Historical salary-band version growth may require indexing/archival tuning after rollout.

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
- BA decisions were captured with stakeholder confirmation on 2026-03-23 and refined to
  implementation-ready frozen rules on 2026-03-27.
- `TASK-06-05` is `clarified/frozen` and issue `#173` is closed.
- `TASK-06-06` is unblocked and ready for implementation execution (issue `#174`).
- `TASK-06-07` is `clarified/frozen` and issue `#175` is closed; repo-backed `TASK-06-08`
  implementation is the local runtime source of truth and should remain aligned with the frozen rules.
- `TASK-09-05` is `clarified/frozen` and issue `#181` is closed; `TASK-09-06` is unblocked for implementation execution.
- `TASK-09-06` remains implementation-phase follow-up item per backlog plan.

## BA Assumptions Logged for Implementation
- Manager confirmation quorum for raise approval is implemented as configurable settings rule with
  hard lower bound `>=2` and default `2`.
- "Referral lifecycle equals regular candidate lifecycle" means referral status transitions map to
  the existing recruitment/pipeline states instead of introducing a parallel status model.
- Referral submit eligibility is frozen to the `employee` role in the dedicated employee self-service
  flow; HR/manager remain reviewers in this baseline.
- Avatar business semantics stay "original upload" (no mandatory crop), while implementation now has
  fixed technical guardrails (`jpeg/png/webp`, max `10 MiB`) to keep reliability and security
  fail-closed.
