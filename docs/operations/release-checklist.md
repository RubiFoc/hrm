# Release Checklist

## Purpose
- Canonical EPIC-13 pre-prod and production gate.
- Use this checklist before any first production release.
- Local development and test deployments may proceed, but they do not waive the gate below.
- `docs/project/production-legal-evidence-package.md` is the canonical manifest for package contents, required attachments, evidence freshness rules, and sign-off workflow.

## Gate Rules
- Pre-prod gate:
  - every critical control in `docs/project/legal-controls-matrix.md` must be at least `implemented`;
  - the matching evidence rows in `docs/project/evidence-registry.md` must exist and be current;
  - controls in `planned` or `in-progress` remain blockers, not waivers.
- Production gate:
  - every critical control must be `verified`;
  - legal and security sign-off must confirm attached evidence and acknowledge any remaining gaps;
  - a control that is still `planned` or `in-progress` blocks release outright.

## Known Blocking Controls
- `CTRL-RU-04` remains a blocker because locality is confirmed as Belarus (not RU-compliant).
- `CTRL-BY-03`, `CTRL-RU-02`, `CTRL-RU-05`, and `CTRL-RU-06` are implemented, but production release still requires `verified` status and refreshed evidence plus legal/security sign-off.

## Required Package Attachments
- Repo-backed inputs:
  - the current `docs/project/legal-controls-matrix.md`;
  - the current `docs/project/evidence-registry.md`;
  - the current `docs/project/production-legal-evidence-package.md`;
  - the release-candidate outputs for `EVID-001`, `EVID-004`, `EVID-005`, `EVID-006`, `EVID-007`, `EVID-009`, and `EVID-010` as applicable.
- External / non-repo inputs:
  - legal sign-off record;
  - security sign-off record.

## Evidence Freshness Rules
- Every attached output and approval must reference the exact production release candidate commit SHA or tag.
- Attached outputs for repo-backed evidence rows must be refreshed after any matching update trigger fires and no more than `7` calendar days before production approval.
- External legal/security approvals become stale immediately if the release candidate, referenced evidence IDs, or blocker state changes.
- `CTRL-RU-04` remains a blocker until RU locality is confirmed in `EVID-009`.
- `CTRL-RU-06` remains a production blocker until legal/security sign-off is attached and the control is marked `verified`.

## Blocking Control Table

| Control ID | Current status | Required threshold | Owner | Evidence IDs | Verification source/command | Sign-off prerequisite | Blocker if planned/in-progress |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL-BY-03 | implemented | Pre-prod: `implemented`; production: `verified` | architect + backend + devops | `EVID-001`, `EVID-004`, `EVID-006` | `EVID-001` backend security/auth tests, `EVID-004` compose smoke, `EVID-006` docs/config review | Legal/security sign-off must confirm RBAC, immutable audit events, storage baseline, and smoke evidence are current | Blocks both gates until the control is at least `implemented` with current evidence |
| CTRL-RU-02 | implemented | Pre-prod: `implemented`; production: `verified` | architect + backend + frontend | `EVID-001`, `EVID-005`, `EVID-007` | `EVID-001` backend security/auth tests, `EVID-005` frontend observability tests, `EVID-007` shortlist/scoring integration checks | Legal/security sign-off must confirm operator measures, observability, and auditability are current | Blocks both gates until the control is at least `implemented` with current evidence |
| CTRL-RU-04 | in-progress | Pre-prod: `implemented`; production: `verified` | architect + devops | `EVID-009` | Manual review of `docs/project/evidence/ru-data-residency-pack.md` | Legal sign-off requires RU locality confirmation in the evidence pack (current locality: Belarus) | Blocks both gates while the control remains `planned` or `in-progress` |
| CTRL-RU-05 | implemented | Pre-prod: `implemented`; production: `verified` | backend + devops | `EVID-001`, `EVID-004` | `EVID-001` access-policy/audit tests, `EVID-004` compose/browser smoke | Legal/security sign-off must confirm access control and smoke verification are current | Blocks both gates until the control is at least `implemented` with current evidence |
| CTRL-RU-06 | implemented | Pre-prod: `implemented`; production: `verified` | security + business-analyst | `EVID-010` | Manual review of `docs/project/evidence/ru-ispdn-class-checklist.md` | Legal/security sign-off must confirm the checklist and attestation are current | Blocks both gates until the control is at least `implemented` with current evidence |

## Release Preconditions
- Do not promote to pre-prod if any critical control is `planned` or `in-progress`.
- Do not promote to production if any critical control is not `verified`.
- Do not claim legal/security sign-off unless the evidence IDs above are current and RU locality is confirmed in `EVID-009`.
- Keep this document aligned with `docs/project/legal-controls-matrix.md`, `docs/project/evidence-registry.md`, `docs/operations/runbook.md`, and `docs/testing/strategy.md` in the same change set.

## Sign-Off Workflow
1. Freeze the production release candidate commit/tag.
2. Refresh and attach the repo-backed evidence outputs required by the critical controls in scope.
3. Attach the non-repo approvals and gap-closure artifacts named in `docs/project/production-legal-evidence-package.md`.
4. Re-check blocker state before approval; missing or stale attachments keep production blocked.
5. Update control status to `verified` only after the same release candidate has fresh evidence and the required legal/security attachments.
