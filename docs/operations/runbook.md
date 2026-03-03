# Operations Runbook

## Last Updated
- Date: 2026-03-03
- Updated by: bootstrap

## Incident Triage
1. Confirm impact and affected user segment.
2. Capture failing signal (logs/metrics/error id).
3. Apply mitigations with lowest blast radius first.
4. Record timeline and root cause candidate.

## Escalation Matrix
| Severity | Condition | Notify | Target Response |
| --- | --- | --- | --- |
| Sev-1 | Full outage or data corruption risk | coordinator + architect | 15 min |
| Sev-2 | Major degradation | coordinator | 30 min |
| Sev-3 | Minor issue | owner role | 1 business day |

## Postmortem Minimum
- Impact summary
- Root cause
- Corrective actions
- Preventive actions
