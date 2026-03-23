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
- `CTRL-BY-01` is `in-progress`, so it blocks pre-prod until it reaches `implemented`, and it blocks production until it is `verified`.
- `CTRL-BY-02` and `CTRL-BY-03` are `implemented`, so they do not block pre-prod, but production release remains blocked until each is `verified` with current evidence and required sign-off.

## Required Package Attachments
- Repo-backed inputs:
  - the current `docs/project/legal-controls-matrix.md`;
  - the current `docs/project/evidence-registry.md`;
  - the current `docs/project/production-legal-evidence-package.md`;
  - the release-candidate outputs for `EVID-001`, `EVID-002`, `EVID-003`, `EVID-004`, `EVID-006`, and `EVID-007` as applicable.
- External / non-repo inputs:
  - legal sign-off record;
  - security sign-off record.

## Evidence Freshness Rules
- Every attached output and approval must reference the exact production release candidate commit SHA or tag.
- Attached outputs for repo-backed evidence rows must be refreshed after any matching update trigger fires and no more than `7` calendar days before production approval.
- External legal/security approvals become stale immediately if the release candidate, referenced evidence IDs, or blocker state changes.
- For production release, any critical control that is not `verified` remains a blocker (currently `CTRL-BY-01`, `CTRL-BY-02`, `CTRL-BY-03`).

## Blocking Control Table

| Control ID | Current status | Required threshold | Owner | Evidence IDs | Verification source/command | Sign-off prerequisite | Blocker if planned/in-progress |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL-BY-01 | in-progress | Pre-prod: `implemented`; production: `verified` | business-analyst + frontend | `EVID-002`, `EVID-003` | `./scripts/check-openapi-freeze.sh`, `npm --prefix apps/frontend run api:types:check`, frontend tests | Legal sign-off must confirm consent and purpose-bound contracts | Blocks both gates while the control remains `planned` or `in-progress` |
| CTRL-BY-02 | implemented | Pre-prod: `implemented`; production: `verified` | backend + hr-ops | `EVID-007` | Runbook review for owner/SLA and log template | Legal sign-off must confirm the subject-rights runbook and SLA | Blocks production until the control is `verified` |
| CTRL-BY-03 | implemented | Pre-prod: `implemented`; production: `verified` | architect + backend + devops | `EVID-001`, `EVID-004`, `EVID-006` | `EVID-001` backend security/auth tests, `EVID-004` compose smoke, `EVID-006` docs/config review | Legal/security sign-off must confirm RBAC, immutable audit events, storage baseline, and smoke evidence are current | Blocks both gates until the control is at least `implemented` with current evidence |

## Release Preconditions
- Do not promote to pre-prod if any critical control is `planned` or `in-progress`.
- Do not promote to production if any critical control is not `verified`.
- Do not claim legal/security sign-off unless the evidence IDs above are current and the Belarus controls are verified.
- Keep this document aligned with `docs/project/legal-controls-matrix.md`, `docs/project/evidence-registry.md`, `docs/operations/runbook.md`, and `docs/testing/strategy.md` in the same change set.
- Data Retention Policy is approved and current; see `docs/operations/runbook.md` (Data Retention Policy).

## Sign-Off Workflow
1. Freeze the production release candidate commit/tag.
2. Refresh and attach the repo-backed evidence outputs required by the critical controls in scope.
3. Attach the non-repo approvals and gap-closure artifacts named in `docs/project/production-legal-evidence-package.md`.
4. Re-check blocker state before approval; missing or stale attachments keep production blocked.
5. Update control status to `verified` only after the same release candidate has fresh evidence and the required legal/security attachments.
