# Automation Event Contracts (v1)

## Purpose
Define the canonical trigger event payloads consumed by the automation evaluator and the field set
available for rule conditions and notification templates.

The evaluator introduced in `TASK-08-01` remains **planning only**:
`evaluate(event) -> planned_actions[]` is deterministic and has no side effects.

`TASK-08-02` adds an executor that turns planned `notification.emit` actions into persisted
in-app notifications (best-effort, fail-closed).

## Common Envelope
All automation events share the following envelope:
- `event_type`: trigger key (string).
- `event_time`: timezone-aware UTC timestamp of the domain change.
- `trigger_event_id`: stable domain identifier used for idempotency (transition/offer/task id).
- `payload`: trigger-specific payload.

Idempotency hook (used by the `TASK-08-02` executor): `dedupe_key` is built from:
`rule_id + trigger_event_id + event_time`.

## Trigger: `pipeline.transition_appended`
Emitted after a pipeline transition is persisted.

### Payload
| Field | Type | Notes |
| --- | --- | --- |
| `transition_id` | UUID | Equals `trigger_event_id`. |
| `vacancy_id` | UUID | |
| `vacancy_title` | string | Allowed in notification text/payload. |
| `candidate_id` | UUID | For conditions only (do not interpolate into notifications). |
| `candidate_id_short` | string | Allowed in notification text/payload. |
| `from_stage` | string\|null | |
| `to_stage` | string | |
| `stage` | string | Alias of `to_stage` (allowed in notification text/payload). |
| `hiring_manager_staff_id` | UUID\|null | Recipient source (fail-closed when null). |
| `changed_by_staff_id` | string | Staff subject id (conditions only). |
| `changed_by_role` | string | Staff role snapshot (conditions only). |

## Trigger: `offer.status_changed`
Emitted after offer status is persisted (`draft -> sent`, `sent -> accepted/declined`).

### Payload
| Field | Type | Notes |
| --- | --- | --- |
| `offer_id` | UUID | Equals `trigger_event_id`. |
| `vacancy_id` | UUID | |
| `vacancy_title` | string | Allowed in notification text/payload. |
| `candidate_id` | UUID | For conditions only (do not interpolate into notifications). |
| `candidate_id_short` | string | Allowed in notification text/payload. |
| `previous_status` | string\|null | |
| `status` | string | |
| `offer_status` | string | Alias of `status` (allowed in notification text/payload). |
| `hiring_manager_staff_id` | UUID\|null | Recipient source (fail-closed when null). |
| `changed_by_staff_id` | string | Staff subject id (conditions only). |
| `changed_by_role` | string | Staff role snapshot (conditions only). |

## Trigger: `onboarding.task_assigned`
Emitted after onboarding task assignment visibility changes (assigned role and/or staff changes).

### Payload
| Field | Type | Notes |
| --- | --- | --- |
| `task_id` | UUID | Equals `trigger_event_id`. |
| `onboarding_id` | UUID | |
| `employee_id` | UUID | |
| `task_title` | string | |
| `assigned_role` | string\|null | Recipient source (role-based). |
| `assigned_staff_id` | UUID\|null | Recipient source (direct staff). |
| `previous_assigned_role` | string\|null | |
| `previous_assigned_staff_id` | UUID\|null | |
| `due_at` | datetime\|null | |
| `employee_full_name` | string | Used by existing notification slice templates. |

## Notification PII Rules (v1)
For **recruitment** triggers (`pipeline.transition_appended`, `offer.status_changed`) automation
notifications must not include candidate names or contacts. Only these fields are allowed in the
notification **text and payload**:
- `vacancy_title`
- `stage` (pipeline) and/or `offer_status` (offer)
- `candidate_id_short`

Recipient resolution is fail-closed and limited to the current notification slice roles:
`manager`, `accountant`.
