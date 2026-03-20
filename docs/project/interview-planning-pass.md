# Interview Planning Pass (`TASK-11-08`, `TASK-05-01`, `TASK-05-02`)

## Last Updated
- Date: 2026-03-20
- Updated by: architect + frontend-engineer

## Purpose
- This document is a planning-only deliverable. It freezes the product and interface decisions required before interview scheduling implementation starts.
- It does not introduce runtime, API, routing, auth, or infrastructure changes by itself.
- Route names in the implemented frontend are now aligned with ADR-0054 and the candidate route split:
  HR controls live on `/hr`, the public company landing is `/`, public application entry is `/careers`, the canonical public apply shell is `/candidate/apply`, and `/candidate` remains compatibility-only.

## Scope of the Next Implementation Slice
- HR scheduling and rescheduling of one active interview per `vacancy_id + candidate_id`.
- Candidate self-service confirmation, reschedule request, and cancellation through a public invitation token.
- Google Calendar synchronization for staff/interviewer calendars with explicit sync states and conflict handling.
- HR review and control inside the dedicated `/hr` workspace.
- Candidate interview registration on `/candidate/interview/:interviewToken` with `/candidate` compatibility redirects.

## Out of Scope for the Next Slice
- Candidate authentication or any return to a candidate session model.
- New CORS or transport rewrites.
- Email/SMS notification service rollout.
- Multi-slot availability collection from candidates.
- Structured interviewer feedback and fairness rubric enforcement (`TASK-05-03`, `TASK-05-04`), now frozen separately in `docs/project/interview-feedback-fairness-pass.md`.
- Manager-specific frontend workspace changes.

## Assumptions
- Current delivery target remains stable local operation on the current device.
- Notification service is not implemented yet, so invitation delivery stays manual in the next slice.
- Candidate identity source of truth remains the profile created by the public apply flow.
- Google Calendar is required, but only staff/interviewer availability is synchronized in the next slice. Candidate attendance is managed through the public invitation token, not calendar account federation.

## Actor Boundaries

| Actor | Allowed Actions | Explicitly Not Allowed |
| --- | --- | --- |
| `admin`, `hr`, `manager` via `interview:manage` | Create interview, reschedule, cancel, resend invite, inspect sync state | Use candidate public token endpoints |
| Candidate via public token | Read current interview invitation, confirm, request reschedule, cancel/decline | Edit vacancy data, choose interviewers, change slot directly, read internal HR notes |
| Background calendar sync worker | Create/update calendar event, persist sync status, persist conflict/failure reason | Decide candidate-facing product behavior beyond persisted status rules |

The implemented frontend keeps the HR interview controls on `/hr`. Manager role keeps backend permission compatibility but does not get a dedicated UI in this slice.

## Canonical Entity Model

One interview row represents one active interview process for a single `vacancy_id + candidate_id` pair.

### Constraints
- At most one non-terminal interview may exist per `vacancy_id + candidate_id`.
- Rescheduling updates the same interview row and increments `schedule_version`.
- Cancelled interviews are terminal. A new interview requires a new row.
- Historical rows remain queryable for audit and future reporting.

### Minimal Interview Fields

| Field | Purpose |
| --- | --- |
| `id` | Interview identifier |
| `vacancy_id`, `candidate_id` | Recruitment linkage |
| `status` | Business lifecycle state |
| `calendar_sync_status` | Calendar execution state |
| `schedule_version` | Invalidates old candidate tokens on reschedule |
| `scheduled_start_at`, `scheduled_end_at`, `timezone` | Canonical schedule window |
| `location_kind` | `google_meet`, `onsite`, or `phone` |
| `location_details` | Meet link, office address, or dial-in details |
| `interviewer_staff_ids[]` | Staff participants whose calendars are synchronized |
| `calendar_event_id` | External Google Calendar event reference |
| `candidate_token_hash`, `candidate_token_expires_at` | Public invitation token state |
| `candidate_response_status` | `pending`, `confirmed`, `reschedule_requested`, `declined` |
| `candidate_response_note` | Optional free-text note from candidate |
| `cancelled_by`, `cancel_reason_code` | Terminal cancellation metadata |
| `created_by_staff_id`, `updated_by_staff_id` | Ownership and audit linkage |
| `created_at`, `updated_at`, `last_synced_at` | Operational traceability |

## Lifecycle Rules

### Business Status
- `pending_sync`: HR created or rescheduled the interview and calendar sync has not succeeded yet.
- `awaiting_candidate_confirmation`: calendar sync succeeded and a current candidate token is active.
- `confirmed`: candidate accepted the current schedule version.
- `reschedule_requested`: candidate requested a new slot or calendar sync returned a hard conflict.
- `cancelled`: HR or candidate cancelled the interview.
- `completed`: reserved for a later slice when interview completion and feedback are implemented.

### Calendar Sync Status
- `queued`
- `running`
- `synced`
- `conflict`
- `failed`

### Transition Rules
- `create interview`:
  - precondition: candidate pipeline stage is `shortlist` or `interview`;
  - result: `status=pending_sync`, `calendar_sync_status=queued`, `schedule_version=1`.
- `calendar sync success`:
  - set `calendar_sync_status=synced`;
  - set `status=awaiting_candidate_confirmation`;
  - mint candidate invitation token;
  - if current pipeline stage is `shortlist`, append one transition to `interview`.
- `calendar sync conflict`:
  - set `calendar_sync_status=conflict`;
  - set `status=reschedule_requested`;
  - do not keep an active candidate token for the conflicting schedule.
- `calendar sync failure`:
  - set `calendar_sync_status=failed`;
  - keep `status=pending_sync`;
  - HR must retry, reschedule, or cancel explicitly.
- `candidate confirm`:
  - allowed only from `awaiting_candidate_confirmation`;
  - result: `status=confirmed`, `candidate_response_status=confirmed`.
- `candidate request reschedule`:
  - allowed from `awaiting_candidate_confirmation` or `confirmed`;
  - result: `status=reschedule_requested`, `candidate_response_status=reschedule_requested`.
- `candidate cancel/decline`:
  - allowed from `awaiting_candidate_confirmation` or `confirmed`;
  - result: `status=cancelled`, `candidate_response_status=declined`, `cancelled_by=candidate`.
- `HR reschedule`:
  - allowed from any non-terminal status except `completed`;
  - increments `schedule_version`;
  - invalidates the previous token immediately;
  - returns the interview to `pending_sync`.
- `HR cancel`:
  - allowed from any non-terminal status;
  - invalidates the current token immediately;
  - result: `status=cancelled`, `cancelled_by=staff`.

## Candidate Registration Token Model
- Keep candidate access anonymous and token-based. Do not add candidate login, refresh tokens, or candidate sessions.
- Generate one opaque random token per successful schedule version.
- Persist only the token hash plus metadata in the database.
- Bind the token to:
  - `interview_id`
  - `schedule_version`
  - candidate identity already linked to the application record
- Expire the token at `min(scheduled_end_at + 12h, issued_at + 30d)`.
- Revoke the token immediately when:
  - the interview is rescheduled;
  - the interview is cancelled;
  - HR explicitly resends the invite;
  - a newer schedule version is created.
- HR-facing responses may expose `candidate_invite_url` and `candidate_token_expires_at`.
- Public token responses must never expose internal staff notes or interviewer private metadata.

## Invitation Delivery Rule
- The next implementation slice will not introduce email/SMS transport.
- After calendar sync succeeds, the backend returns `candidate_invite_url` to authorized staff users.
- HR shares that link with the candidate manually out of band during the current local-stage baseline.
- A future notification service may automate delivery without changing the public token contract.

## Minimal Backend API Set

### HR APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/vacancies/{vacancy_id}/interviews` | Create the active interview for one candidate and enqueue calendar sync |
| `GET` | `/api/v1/vacancies/{vacancy_id}/interviews` | List interviews for the vacancy, optionally filtered by `candidate_id` or `status` |
| `GET` | `/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}` | Read one interview with calendar state and current invite metadata |
| `POST` | `/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/reschedule` | Replace the schedule window, bump `schedule_version`, and enqueue sync again |
| `POST` | `/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/cancel` | Cancel the interview with a reason code |
| `POST` | `/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/resend-invite` | Reissue a fresh token for the current schedule version after successful sync |

### Public Candidate APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/public/interview-registrations/{token}` | Read the current invitation payload for the token |
| `POST` | `/api/v1/public/interview-registrations/{token}/confirm` | Confirm attendance for the current schedule version |
| `POST` | `/api/v1/public/interview-registrations/{token}/request-reschedule` | Request a new slot and optionally send a note |
| `POST` | `/api/v1/public/interview-registrations/{token}/cancel` | Cancel/decline the interview |

### Canonical Interview Response Shape
- `interview_id`
- `vacancy_id`
- `candidate_id`
- `status`
- `calendar_sync_status`
- `schedule_version`
- `scheduled_start_at`
- `scheduled_end_at`
- `timezone`
- `location_kind`
- `location_details`
- `interviewer_staff_ids`
- `candidate_response_status`
- `candidate_response_note`
- `candidate_token_expires_at`
- `candidate_invite_url` (`HR` responses only)
- `calendar_event_id`
- `last_synced_at`
- `cancelled_by`
- `cancel_reason_code`
- `created_at`
- `updated_at`

## Error Contract Rules

### HR APIs
- `403`: caller lacks `interview:manage`.
- `404`: vacancy, candidate, or interview not found in the allowed scope.
- `409`: active interview already exists, interview is terminal, or calendar conflict blocks the requested action.
- `422`: invalid schedule window, invalid stage, duplicate interviewer list, or unsupported location mode.

### Public Token APIs
- `404`: token not found or already revoked.
- `409`: current interview state does not allow the requested action.
- `410`: token expired.
- `422`: malformed note payload or invalid public action body.

## Frontend Route and UX Model

### HR Route
- Keep the current HR workspace on `/hr`.
- Add an interview scheduling block beside the existing shortlist review area when a vacancy and candidate are selected.
- Required HR UI elements:
  - create interview form;
  - current `status` and `calendar_sync_status`;
  - copyable `candidate_invite_url` when available;
  - actions for `reschedule`, `cancel`, and `resend invite`;
  - localized errors for `403`, `404`, `409`, `422`, and generic HTTP failures.

### Candidate Route
- Keep `/candidate` as the compatibility redirect shell.
- Use `/candidate/apply` for the public apply/tracking flow.
- Use `/candidate/interview/:interviewToken` for interview registration.
- Route mode rules:
  - `vacancyId` mode: public apply/tracking flow on `/candidate/apply`;
  - `interviewToken` mode: interview registration flow on `/candidate/interview/:interviewToken`;
  - mixed parameters are invalid and must render a localized error state.
- Candidate interview mode must show:
  - vacancy title and interview schedule;
  - timezone and location details;
  - calendar sync-derived meeting link/details when available;
  - actions `Confirm`, `Request reschedule`, and `Decline`.

## Pipeline and Audit Boundaries
- Interview creation is allowed only from candidate pipeline stages `shortlist` or `interview`.
- First successful interview sync appends `shortlist -> interview` if the candidate has not yet entered the `interview` stage.
- Candidate public actions do not modify vacancy data or pipeline stages directly beyond interview state.
- All HR interview actions and public token actions must emit audit events with reason codes and correlation identifiers.

## Future Implementation Acceptance Baseline
- Freeze OpenAPI and generate frontend types in the same change.
- Do not change auth, CORS, or the anonymous candidate transport model.
- Keep compose smoke green without adding Google Calendar nondeterministic browser steps.
- Cover at minimum:
  - HR create/reschedule/cancel happy and negative paths;
  - calendar `queued/running/synced/conflict/failed` transitions;
  - candidate token `confirm/reschedule/cancel` paths;
  - expired/revoked token handling;
  - `/candidate/interview/:interviewToken` route-mode rendering and localized failures.

## Explicit Deferrals
- `TASK-05-03` keeps structured feedback out of the scheduling slice and is planned separately in `docs/project/interview-feedback-fairness-pass.md`.
- `TASK-05-04` keeps fairness rubric enforcement out of the scheduling slice and is planned separately in `docs/project/interview-feedback-fairness-pass.md`.
- Candidate notification automation remains a later platform slice.
