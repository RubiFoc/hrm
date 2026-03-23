# Legal Controls Matrix (Belarus)

## Last Updated
- Date: 2026-03-23
- Updated by: coordinator

## Status Legend
- `planned`: control not yet represented by a concrete product/process artifact in the repo.
- `in-progress`: some repo artifacts exist, but the control is not yet complete enough for release sign-off.
- `implemented`: control is represented by concrete code/process artifacts and repeatable verification.
- `verified`: evidence and legal/security review completed.
- Jurisdiction scope: Belarus only (ADR-0059).

## Matrix

| Jurisdiction | NPA / Article | Obligation (short) | Control ID | Product/Process Control | Owner | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Belarus | Law No. 99-З (2021), Art. 5 | Obtain informed consent and limit consent payload to declared purposes | CTRL-BY-01 | Candidate/staff data collection uses explicit field contracts and frozen API payloads; separate purpose registry still missing | business-analyst + frontend | in-progress | `EVID-002`, `EVID-003` |
| Belarus | Law No. 99-З (2021), Arts. 11, 13 | Support access, correction, and deletion/stop-processing requests | CTRL-BY-02 | Runbook workflow and owner model for subject requests | backend + hr-ops | implemented | `EVID-007` |
| Belarus | Law No. 99-З (2021), Art. 17; Law No. 455-З (2008), Art. 17 | Protect restricted/personal information with legal, organizational, and technical measures | CTRL-BY-03 | RBAC, immutable audit events, object-storage protection baseline, and reproducible smoke verification | architect + backend + devops | implemented | `EVID-001`, `EVID-004`, `EVID-006` |

## Control Detail (Obligation -> Control -> Evidence)

| Control ID | Obligation Detail | Technical/Process Control | Evidence Baseline | Verification Baseline |
| --- | --- | --- | --- | --- |
| CTRL-BY-01 | Consent must be informed and field scope limited to declared purposes | Candidate apply/login payloads stay frozen through OpenAPI and typed frontend forms | `EVID-002`, `EVID-003` | `./scripts/check-openapi-freeze.sh`, `npm --prefix apps/frontend run api:types:check`, frontend tests |
| CTRL-BY-02 | Subject must be able to request access/correction/deletion or stop-processing | Runbook procedure + owner/SLA workflow | `EVID-007` | Runbook review for owner/SLA and log template |
| CTRL-BY-03 | Personal/restricted information must be protected against unauthorized actions | RBAC enforcement, immutable audit events, storage/security baseline, smoke verification | `EVID-001`, `EVID-004`, `EVID-006` | backend security/auth tests, compose smoke, config review |

## Delivery Gate
- Current stage delivery target is local runtime on the current device; production launch is not in scope for this stage.
- `docs/operations/release-checklist.md` is the canonical EPIC-13 pre-prod/production gate.
- `docs/project/production-legal-evidence-package.md` is the canonical repo-backed production sign-off manifest for current evidence, external attachments, blockers, and `verified` exit criteria.
- Development environment is non-blocking for controls in `planned` or `in-progress` status, but those states remain release blockers for EPIC-13.
- Current repo-backed critical controls are:
  - `implemented`: `CTRL-BY-03`, `CTRL-BY-02`
  - `in-progress`: `CTRL-BY-01`
- Pre-prod promotion requires all critical controls to be at least `implemented`, with current evidence rows and verification commands recorded in `docs/project/evidence-registry.md`.
- Production release additionally requires legal/security sign-off and `verified` status for every critical control; `CTRL-BY-01` must reach `implemented` before it can be verified.
- `CTRL-BY-03` stays `implemented` until the package manifest shows fresh release-candidate evidence plus non-repo legal/security approvals for the same release candidate.
- Any critical control that remains `planned` or `in-progress` is a hard blocker for both pre-prod and production release.
- Execution tracking for this matrix is formalized under `EPIC-13` in:
  - `TASK-13-01` (article-level mapping),
  - `TASK-13-02` (evidence ownership model),
  - `TASK-13-03` (release-gate checklist),
  - `TASK-13-04` (production legal evidence package).
- TODO(owner: business-analyst + legal, due_trigger: before first production release): approve final status and evidence completeness for all critical controls.
