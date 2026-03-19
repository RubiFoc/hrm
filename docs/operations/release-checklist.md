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
- `CTRL-RU-04` and `CTRL-RU-06` are current hard blockers because the evidence registry still lists them as gaps.
- `CTRL-BY-03`, `CTRL-RU-02`, and `CTRL-RU-05` are implemented, but production release still requires `verified` status and refreshed evidence before sign-off.

## Required Package Attachments
- Repo-backed inputs:
  - the current `docs/project/legal-controls-matrix.md`;
  - the current `docs/project/evidence-registry.md`;
  - the current `docs/project/production-legal-evidence-package.md`;
  - the release-candidate outputs for `EVID-001`, `EVID-004`, `EVID-005`, `EVID-006`, and `EVID-007` as applicable.
- External / non-repo inputs:
  - legal sign-off record;
  - security sign-off record;
  - RU data-residency attachment pack for `CTRL-RU-04`;
  - ISPDn class checklist and attestation pack for `CTRL-RU-06`.

## Evidence Freshness Rules
- Every attached output and approval must reference the exact production release candidate commit SHA or tag.
- Attached outputs for repo-backed evidence rows must be refreshed after any matching update trigger fires and no more than `7` calendar days before production approval.
- External legal/security approvals become stale immediately if the release candidate, referenced evidence IDs, or blocker state changes.
- `CTRL-RU-04` and `CTRL-RU-06` remain blockers until their gap rows are replaced by real artifacts in `docs/project/evidence-registry.md`.

## Blocking Control Table

| Control ID | Current status | Required threshold | Owner | Evidence IDs | Verification source/command | Sign-off prerequisite | Blocker if planned/in-progress |
| --- | --- | --- | --- | --- | --- | --- | --- |
| CTRL-BY-03 | implemented | Pre-prod: `implemented`; production: `verified` | architect + backend + devops | `EVID-001`, `EVID-004`, `EVID-006` | `EVID-001` backend security/auth tests, `EVID-004` compose smoke, `EVID-006` docs/config review | Legal/security sign-off must confirm RBAC, immutable audit events, storage baseline, and smoke evidence are current | Blocks both gates until the control is at least `implemented` with current evidence |
| CTRL-RU-02 | implemented | Pre-prod: `implemented`; production: `verified` | architect + backend + frontend | `EVID-001`, `EVID-005`, `EVID-007` | `EVID-001` backend security/auth tests, `EVID-005` frontend observability tests, `EVID-007` shortlist/scoring integration checks | Legal/security sign-off must confirm operator measures, observability, and auditability are current | Blocks both gates until the control is at least `implemented` with current evidence |
| CTRL-RU-04 | planned | Pre-prod: `implemented`; production: `verified` | architect + devops | none (gap) | No current in-repo command; release stays blocked until a real RU residency artifact is added to the registry | Legal sign-off cannot proceed until a real infrastructure/data-residency artifact exists | Blocks both gates while the control remains `planned` or `in-progress` |
| CTRL-RU-05 | implemented | Pre-prod: `implemented`; production: `verified` | backend + devops | `EVID-001`, `EVID-004` | `EVID-001` access-policy/audit tests, `EVID-004` compose/browser smoke | Legal/security sign-off must confirm access control and smoke verification are current | Blocks both gates until the control is at least `implemented` with current evidence |
| CTRL-RU-06 | planned | Pre-prod: `implemented`; production: `verified` | security + business-analyst | none (gap) | No current in-repo command; release stays blocked until the class checklist and attestation pack exist and are registered | Legal/security sign-off cannot proceed until the class checklist and attestation pack exist | Blocks both gates while the control remains `planned` or `in-progress` |

## Release Preconditions
- Do not promote to pre-prod if any critical control is `planned` or `in-progress`.
- Do not promote to production if any critical control is not `verified`.
- Do not claim legal/security sign-off unless the evidence IDs above are current and the gap rows for `CTRL-RU-04` and `CTRL-RU-06` are either closed with real artifacts or still blocking the release.
- Keep this document aligned with `docs/project/legal-controls-matrix.md`, `docs/project/evidence-registry.md`, `docs/operations/runbook.md`, and `docs/testing/strategy.md` in the same change set.

## Sign-Off Workflow
1. Freeze the production release candidate commit/tag.
2. Refresh and attach the repo-backed evidence outputs required by the critical controls in scope.
3. Attach the non-repo approvals and gap-closure artifacts named in `docs/project/production-legal-evidence-package.md`.
4. Re-check blocker state before approval; missing or stale attachments keep production blocked.
5. Update control status to `verified` only after the same release candidate has fresh evidence and the required legal/security attachments.
