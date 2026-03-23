# Production Legal Evidence Package

## Last Updated
- Date: 2026-03-23
- Updated by: coordinator

## Purpose
- Canonical repo-backed manifest for the first production legal evidence package under `TASK-13-04`.
- Defines:
  - which critical-control evidence already exists in repo;
  - which attachments still must come from legal, security, or infrastructure outside the repo;
  - what still blocks production release;
  - what is required before a control can move to `verified`.
- This document does not, by itself, move any control to `implemented` or `verified`.

## Explicit Assumptions
- Release-specific command outputs, screenshots, and approval records are attached to the release ticket or PR rather than committed into the repo.
- The repo remains the source of truth for the package manifest, evidence sources, verification commands, blockers, and exit criteria.
- If the release candidate commit/tag changes, any previously attached evidence or approvals must be refreshed before sign-off.

## Current Critical-Control Snapshot

| Control ID | Current Status | Already Evidenced in Repo | Still Needs External / Non-Repo Attachment | Blocking Production Now | Required to Move to `verified` |
| --- | --- | --- | --- | --- | --- |
| CTRL-BY-01 | `in-progress` | `EVID-002`, `EVID-003` | Legal sign-off record referencing the current release candidate | Yes. The control is not yet `verified`. | Attach legal sign-off for the same release candidate, then update the control status to `verified`. |
| CTRL-BY-02 | `planned` | No current evidence artifact in repo | Runbook procedure for subject requests plus legal sign-off record | Yes. The control remains a blocker while no real artifact exists. | Create the runbook procedure, register it in the repo, attach legal sign-off, then update the control status. |
| CTRL-BY-03 | `implemented` | `EVID-001`, `EVID-004`, `EVID-006` | Security sign-off record referencing the current release candidate and refreshed evidence outputs; legal release acknowledgment referencing the same package | Yes. The control is not yet `verified`. | Re-run the listed evidence on the exact production candidate, attach results, record legal/security sign-off, then update the matrix/registry status in repo. |

## Repo-Backed Package Inputs Available Today

| Package Input | Control IDs | Source of Truth | Package Use Today | Freshness Action Before Production Sign-Off |
| --- | --- | --- | --- | --- |
| `EVID-001` | `CTRL-BY-03` | `docs/project/evidence-registry.md` | RBAC, audit, and auth control evidence already defined in repo | Re-run the listed backend verification commands on the exact release candidate and attach the output bundle |
| `EVID-002` | `CTRL-BY-01` | `docs/project/evidence-registry.md` | Frozen OpenAPI contract evidence already defined in repo | Re-run the listed OpenAPI verification on the exact release candidate and attach the output |
| `EVID-003` | `CTRL-BY-01` | `docs/project/evidence-registry.md` | Frontend consent/contract UI evidence already defined in repo | Re-run the listed frontend tests on the exact release candidate and attach the output |
| `EVID-004` | `CTRL-BY-03` | `docs/project/evidence-registry.md` | Compose/browser smoke baseline already defined in repo | Re-run compose/browser smoke on the exact release candidate and attach the results |
| `EVID-006` | `CTRL-BY-03` | `docs/project/evidence-registry.md` | Config/runbook/object-storage baseline already defined in repo | Refresh the config review against the exact release candidate docs/config set and attach the review note |
| Control/status manifest | All critical controls | `docs/project/legal-controls-matrix.md` | Shows current control status and prevents silent status upgrades | Refresh in repo if any evidence row or control status changes |
| Package manifest | All critical controls | `docs/project/production-legal-evidence-package.md` | Keeps repo-backed evidence, external attachments, blockers, and verified-exit criteria aligned | Refresh in repo whenever package composition, blocker state, or sign-off rules change |

## Required External / Non-Repo Attachments

| Attachment | Control IDs | Owner | Required Contents | Current State |
| --- | --- | --- | --- | --- |
| Legal sign-off record | `CTRL-BY-01`, `CTRL-BY-02`, `CTRL-BY-03` | legal + business-analyst | Release candidate identifier, reviewed control IDs, reviewed evidence IDs/attachments, approval date, explicit blocker acknowledgement | Missing until first production sign-off |
| Security sign-off record | `CTRL-BY-03` | security + architect | Release candidate identifier, reviewed evidence IDs/attachments, approval date, security decision, residual-risk note if any | Missing until first production sign-off |

## Production Blockers Right Now
- `CTRL-BY-01` is `in-progress`; production release remains blocked until it is `verified`.
- `CTRL-BY-02` is `planned` with no evidence artifact; production release remains blocked until a runbook procedure exists and is verified.
- `CTRL-BY-03` is `implemented`; it still needs fresh release-candidate evidence attachments plus legal/security sign-off before it can move to `verified`.
- No blocker may be converted into a waiver by adding a placeholder row or a synthetic attachment reference.

## Evidence Freshness Rules
- Every attached output or approval must name the exact release candidate commit SHA or tag proposed for production.
- Evidence outputs for `EVID-001`, `EVID-002`, `EVID-003`, `EVID-004`, and `EVID-006` must be refreshed after any matching `Update Trigger` in `docs/project/evidence-registry.md` fires.
- For production sign-off, attached evidence outputs must be generated no more than `7` calendar days before the approval date and after the latest change to the release candidate.
- External legal/security approvals expire immediately if the release candidate, the referenced evidence ID set, or the blocking-gap state changes.
- `CTRL-BY-01` and `CTRL-BY-02` stay blocking until they are `verified`.

## Sign-Off Workflow
1. Freeze the production release candidate commit SHA or tag.
2. Refresh all repo-backed evidence rows required by the critical controls in scope and attach the outputs to the release ticket or PR.
3. Assemble the package manifest with links to:
   - `docs/project/legal-controls-matrix.md`
   - `docs/project/evidence-registry.md`
   - `docs/project/production-legal-evidence-package.md`
   - `docs/operations/release-checklist.md`
   - `docs/operations/runbook.md`
   - `docs/testing/strategy.md`
4. Attach the required non-repo approvals and gap-closure artifacts listed above.
5. Re-check blocker state:
   - if any critical control is still `planned` or `in-progress`, the release remains blocked;
   - if any required attachment is missing or stale, the release remains blocked.
6. Move a control to `verified` only after the same release candidate has:
   - fresh repo-backed evidence attached;
   - all required non-repo approvals attached;
   - no remaining blocking gap for that control.

## Package Closeout Rule
- After production sign-off, keep the attached package with the release record, and update the repo only when the control status, evidence rows, or blocker state materially changes.
