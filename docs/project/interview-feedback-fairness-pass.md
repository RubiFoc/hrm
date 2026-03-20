# Interview Feedback and Fairness Pass (`TASK-05-03`, `TASK-05-04`)

## Last Updated
- Date: 2026-03-20
- Updated by: architect + frontend-engineer

## Purpose
- This document is a planning-only deliverable.
- It freezes the product and interface decisions required before implementation of structured interview feedback and fairness gating starts.
- It does not introduce runtime, API, routing, auth, or infrastructure changes by itself.
- Route names in the implemented frontend are now aligned with ADR-0054 and the candidate route split:
  HR controls live on `/hr`, the public company landing is `/`, public application entry is `/careers`, the canonical public apply shell is `/candidate/apply`, and `/candidate` remains compatibility-only.

## Scope of the Next Implementation Slice
- Structured interviewer feedback capture for the current interview panel.
- Readable HR summary of submitted and missing interviewer feedback.
- Fairness gate before the existing pipeline transition from `interview` to `offer`.
- Feedback UX inside the dedicated HR workspace on `/hr`.
- Backend validation and audit behavior for feedback submission and decision gating.

## Out of Scope for the Next Slice
- Candidate authentication or any change to public token-based candidate transport.
- New route tree, new candidate route mode, or new CORS behavior.
- Notification-service rollout for interviewer reminders or feedback chasers.
- Manager-specific frontend workspace outside the dedicated `/manager` screen.
- Automatic hire/reject decisions based on feedback sentiment.
- New recruitment pipeline stages or route topology changes.
- Google Calendar browser automation inside compose smoke.

## Preserved Constraints
- Keep HR controls on `/hr`.
- Keep candidate interview registration on `/candidate/interview/:interviewToken`.
- Do not reopen auth model, CORS model, route topology, or public candidate transport model.
- Keep changes minimal and reversible when implementation starts.
- Freeze OpenAPI and generated frontend types in the same implementation change.

## Assumptions
- Interview scheduling and candidate registration are already implemented from `docs/project/interview-planning-pass.md`.
- The canonical recruitment pipeline stays unchanged:
  `shortlist -> interview -> offer -> hired/rejected`.
- The fairness gate is applied only to the transition `interview -> offer`.
- Feedback completeness is the minimum fairness control for this slice; recommendation disagreement is surfaced to HR but does not auto-block `offer`.
- One current schedule version is the source of truth for required interviewer feedback.

## Actor Boundaries

| Actor | Allowed Actions | Explicitly Not Allowed |
| --- | --- | --- |
| Assigned interviewer (authenticated staff whose subject id is present in `interviewer_staff_ids`) | Create or update only their own feedback for the current `schedule_version`; read the current interview feedback summary in HR workspace | Submit feedback for another interviewer; bypass required rubric fields; submit stale feedback for an older schedule version |
| `admin`, `hr`, `manager` via existing `interview:manage` permission | Read panel summary, inspect missing interviewers, and attempt pipeline transition to `offer` subject to fairness gate | Override or edit another interviewer's submitted feedback in this slice |
| Candidate via public token | Continue using existing interview registration endpoints | Read or mutate interviewer feedback |
| Background workers | None for this slice | Auto-generate interviewer feedback or auto-resolve hiring outcome |

## Canonical Feedback Model

One feedback row represents one interviewer's latest submission for one interview and one `schedule_version`.

### Constraints
- At most one active feedback row exists per `interview_id + schedule_version + interviewer_staff_id`.
- Rescheduling an interview increments `schedule_version`; previous-version feedback remains audit history but no longer satisfies the fairness gate.
- Feedback is interviewer-scoped and cannot be shared across different interview rows or schedule versions.

### Minimal Feedback Fields

| Field | Purpose |
| --- | --- |
| `feedback_id` | Unique feedback identifier |
| `interview_id` | Parent interview row |
| `schedule_version` | Binds feedback to the current interview schedule |
| `interviewer_staff_id` | Submitting interviewer identity |
| `requirements_match_score` | Standardized 1-5 rubric score |
| `communication_score` | Standardized 1-5 rubric score |
| `problem_solving_score` | Standardized 1-5 rubric score |
| `collaboration_score` | Standardized 1-5 rubric score |
| `recommendation` | `strong_yes`, `yes`, `mixed`, or `no` |
| `strengths_note` | Required qualitative evidence for positives |
| `concerns_note` | Required qualitative evidence for risks/concerns |
| `evidence_note` | Required free-text evidence that supports the ratings |
| `submitted_at`, `updated_at` | Traceability for fairness gate and audit |

## Rubric and Recommendation Rules

### Score Scale
- All rubric scores use integer values `1..5`.
- `1` means the interviewer observed a clear deficit for that criterion.
- `3` means borderline or mixed evidence.
- `5` means strong, explicit evidence for the criterion.

### Mandatory Rubric Criteria
- `requirements_match_score`
- `communication_score`
- `problem_solving_score`
- `collaboration_score`

### Recommendation Enum
- `strong_yes`
- `yes`
- `mixed`
- `no`

### Qualitative Field Rules
- `strengths_note` is required and must be non-empty.
- `concerns_note` is required and must be non-empty.
- `evidence_note` is required and must be non-empty.
- Free-text notes are capped at implementation-defined safe lengths, but the fields are mandatory for every submission.

## Feedback Lifecycle Rules
- Feedback submission is allowed only for the current interview `schedule_version`.
- Feedback submission is allowed only when:
  - the interview is not `cancelled`;
  - the interview has a real schedule window;
  - `scheduled_end_at <= now`.
- Feedback submission is rejected before the interview window ends with `409 interview_feedback_window_not_open`.
- Rescheduling invalidates the previous schedule version for fairness-gate purposes immediately.
- Assigned interviewers may update their own submission for the current version any number of times until HR moves the candidate past `interview`.
- Once the candidate leaves pipeline stage `interview`, feedback becomes read-only audit history in this slice.

## Fairness Gate Rules

The fairness gate is evaluated only when the existing pipeline transition request asks for `to_stage=offer`.

### Gate Preconditions
- Candidate is currently in pipeline stage `interview`.
- There is one active interview row for the same `vacancy_id + candidate_id`.
- The active interview is not `cancelled`.
- `scheduled_end_at <= now` for the active interview.
- Every interviewer listed in `interviewer_staff_ids` for the current `schedule_version` has exactly one current-version feedback submission.
- Every current-version feedback submission contains all mandatory rubric scores and all mandatory qualitative notes.

### Gate Outcomes
- `passed`:
  - all current-version interviewer feedback is present and complete.
- `blocked` with reason codes:
  - `interview_feedback_window_not_open`
  - `interview_feedback_missing`
  - `interview_feedback_incomplete`
  - `interview_feedback_stale`
  - `interview_feedback_not_required_for_terminal_interview`

### Recommendation Disagreement Policy
- Recommendation disagreement does not block `interview -> offer` by itself in this slice.
- HR remains the human decision owner.
- The system surfaces distribution of recommendations and average rubric scores, but does not auto-reject or auto-hire.

## Minimal Backend API Set

### HR Feedback APIs

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback` | Read current-version panel summary plus submitted feedback rows |
| `PUT` | `/api/v1/vacancies/{vacancy_id}/interviews/{interview_id}/feedback/me` | Create or replace the current interviewer's feedback for the current `schedule_version` |

### Existing Pipeline API Integration

| Method | Path | Purpose |
| --- | --- | --- |
| `POST` | `/api/v1/pipeline/transitions` | Keep the existing endpoint; when `to_stage=offer`, run fairness gate before creating the transition |

## Canonical Feedback Response Shape

### Feedback Item
- `feedback_id`
- `interview_id`
- `schedule_version`
- `interviewer_staff_id`
- `requirements_match_score`
- `communication_score`
- `problem_solving_score`
- `collaboration_score`
- `recommendation`
- `strengths_note`
- `concerns_note`
- `evidence_note`
- `submitted_at`
- `updated_at`

### Panel Summary
- `interview_id`
- `vacancy_id`
- `candidate_id`
- `schedule_version`
- `required_interviewer_ids`
- `submitted_interviewer_ids`
- `missing_interviewer_ids`
- `required_interviewer_count`
- `submitted_count`
- `gate_status`
- `gate_reason_codes`
- `recommendation_distribution`
- `average_scores`
- `items`

## Error Contract Rules

### Feedback APIs
- `403`:
  - caller lacks `interview:manage` for read;
  - caller is not an assigned interviewer for `feedback/me`.
- `404`:
  - vacancy, interview, or current-version interview context not found.
- `409`:
  - interview is cancelled;
  - interview window has not ended yet;
  - feedback belongs to an old schedule version.
- `422`:
  - invalid score range;
  - missing mandatory note field;
  - malformed payload.

### Pipeline Transition Gate
- Keep the existing transition endpoint and stage matrix.
- When `to_stage=offer`, return `409` with stable detail codes:
  - `interview_feedback_window_not_open`
  - `interview_feedback_missing`
  - `interview_feedback_incomplete`
  - `interview_feedback_stale`
- Do not add a separate offer-decision endpoint in this slice.

## Frontend Route and UX Model

### HR Route
- Keep the existing HR workspace on `/hr`.
- Add an interview-feedback block that becomes active when:
  - a vacancy is selected;
  - a candidate is selected;
  - the selected pair has an interview row.
- Required HR UI elements:
  - current fairness gate status;
  - missing interviewer list when feedback is incomplete;
  - recommendation distribution summary;
  - rubric averages summary;
  - current-user feedback form when the authenticated staff user is an assigned interviewer;
  - read-only list of submitted feedback rows for authorized staff users.

### Form Rules
- Use one form for create/update on `feedback/me`.
- Validate all rubric fields client-side before submit.
- Validate that required qualitative fields are non-empty before submit.
- Show localized `403`, `404`, `409`, `422`, and generic HTTP errors.

### Offer Transition UX
- Keep the current pipeline transition controls on `/hr`.
- When the selected target stage is `offer`, surface the current fairness summary before submit.
- If backend returns one of the fairness `409` codes, render a localized blocker message instead of a generic transition failure.

### Candidate Route
- Keep `/candidate` as the compatibility redirect shell for this slice.
- Do not expose interviewer feedback or fairness summary through public token endpoints or the dedicated apply/interview public routes.

## Pipeline and Audit Boundaries
- Feedback submission does not create a new pipeline stage.
- Feedback APIs and fairness-gated transition attempts must emit audit events with correlation id and stable reason codes.
- Feedback history is interview-domain data; pipeline transition history remains append-only in the vacancy domain.
- The fairness gate may read interview-domain feedback state, but must not duplicate feedback data inside vacancy/pipeline tables.

## Future Implementation Acceptance Baseline
- Freeze OpenAPI and generate frontend types in the same change.
- Do not change auth, CORS, route topology, or anonymous candidate transport.
- Keep compose smoke green without adding feedback-specific browser automation.
- Cover at minimum:
  - interviewer feedback create/update happy path;
  - non-interviewer submit deny path;
  - stale feedback after reschedule;
  - `interview -> offer` blocked when feedback is missing, incomplete, stale, or too early;
  - `interview -> offer` success after complete current-version panel feedback;
  - `/` route feedback form render, summary render, and localized fairness-gate blocker messages.

## Explicit Deferrals
- No automatic hiring recommendation engine beyond human-visible summary.
- No interviewer reminder notifications or escalation workflow.
- No dedicated manager workspace or mobile-specific feedback UX.
- No candidate-facing visibility into internal interviewer rubric data.
