# Legal Controls Matrix (Belarus + Russia)

## Last Updated
- Date: 2026-03-23
- Updated by: coordinator

## Status Legend
- `planned`: control not yet represented by a concrete product/process artifact in the repo.
- `in-progress`: some repo artifacts exist, but the control is not yet complete enough for release sign-off.
- `implemented`: control is represented by concrete code/process artifacts and repeatable verification.
- `verified`: evidence and legal/security review completed.

## Matrix

| Jurisdiction | NPA / Article | Obligation (short) | Control ID | Product/Process Control | Owner | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Belarus | Law No. 99-З (2021), Art. 5 | Obtain informed consent and limit consent payload to declared purposes | CTRL-BY-01 | Candidate/staff data collection uses explicit field contracts and frozen API payloads; separate purpose registry still missing | business-analyst + frontend | in-progress | `EVID-002`, `EVID-003` |
| Belarus | Law No. 99-З (2021), Arts. 11, 13 | Support access, correction, and deletion/stop-processing requests | CTRL-BY-02 | Runbook workflow and owner model for subject requests | backend + hr-ops | planned | Coverage gap (see `docs/project/evidence-registry.md`) |
| Belarus | Law No. 99-З (2021), Art. 17; Law No. 455-З (2008), Art. 17 | Protect restricted/personal information with legal, organizational, and technical measures | CTRL-BY-03 | RBAC, immutable audit events, object-storage protection baseline, and reproducible smoke verification | architect + backend + devops | implemented | `EVID-001`, `EVID-004`, `EVID-006` |
| Russia | Federal Law 152-ФЗ, Art. 5 | Minimize collected PD and keep purpose-bound data contracts | CTRL-RU-01 | Frozen OpenAPI contract plus frontend/backend forms limited to the current Phase 1 fields | business-analyst + frontend + backend | in-progress | `EVID-002`, `EVID-003`, `EVID-007` |
| Russia | Federal Law 152-ФЗ, Arts. 18.1, 19 | Implement operator measures and security baseline for PD processing | CTRL-RU-02 | RBAC/audit controls, scoring/candidate evidence traceability, and Sentry observability baseline | architect + backend + frontend | implemented | `EVID-001`, `EVID-005`, `EVID-007` |
| Russia | Federal Law 152-ФЗ, Arts. 14, 20 | Provide data-subject access/correction/deletion workflow within statutory response path | CTRL-RU-03 | Request handling workflow and response SLA process | backend + hr-ops | planned | Coverage gap (see `docs/project/evidence-registry.md`) |
| Russia | Federal Law 242-ФЗ; Federal Law 152-ФЗ, Art. 18(5) | Localize Russian citizens' data in the required jurisdiction | CTRL-RU-04 | Infrastructure/data-residency control for RU citizen records and backups | architect + devops | in-progress | `EVID-009` |
| Russia | Federal Law 149-ФЗ, Art. 16 | Apply organizational/technical measures to protect restricted information and access | CTRL-RU-05 | Unified access control enforcement, audit trail, compose smoke, and browser auth/public-flow verification | backend + devops | implemented | `EVID-001`, `EVID-004` |
| Russia | Decree No. 1119 (2012) | Maintain class-based PD protection checklist and attestations | CTRL-RU-06 | Security control checklist by ISPDn class and release-time attestations | security + business-analyst | implemented | `EVID-010` |

## Control Detail (Obligation -> Control -> Evidence)

| Control ID | Obligation Detail | Technical/Process Control | Evidence Baseline | Verification Baseline |
| --- | --- | --- | --- | --- |
| CTRL-BY-01 | Consent must be informed and field scope limited to declared purposes | Candidate apply/login payloads stay frozen through OpenAPI and typed frontend forms | `EVID-002`, `EVID-003` | `./scripts/check-openapi-freeze.sh`, `npm --prefix apps/frontend run api:types:check`, frontend tests |
| CTRL-BY-02 | Subject must be able to request access/correction/deletion or stop-processing | Runbook procedure + owner/SLA workflow | No current evidence artifact | To implement under future request-handling slice |
| CTRL-BY-03 | Personal/restricted information must be protected against unauthorized actions | RBAC enforcement, immutable audit events, storage/security baseline, smoke verification | `EVID-001`, `EVID-004`, `EVID-006` | backend security/auth tests, compose smoke, config review |
| CTRL-RU-01 | Processing must stay purpose-bound and data-minimized | Frozen contracts and UI/API payload boundaries define the current Phase 1 data set | `EVID-002`, `EVID-003`, `EVID-007` | OpenAPI drift check, frontend tests, targeted backend/frontend scoring tests |
| CTRL-RU-02 | Operator must implement and confirm adequate security measures | Access control, auditability, explainable AI artifacts, and critical-route observability | `EVID-001`, `EVID-005`, `EVID-007` | backend security tests, frontend observability tests, scoring/candidate test suites |
| CTRL-RU-03 | Subject rights requests need a repeatable response workflow | Request intake/runbook + actor ownership | No current evidence artifact | To implement under future request-handling slice |
| CTRL-RU-04 | RU citizens' PD must be stored/localized in the required jurisdiction | Infra placement and backup residency controls | `EVID-009` | Manual review of the RU data-residency pack; confirm locality is RU (current evidence: Belarus), backup cadence, and approver |
| CTRL-RU-05 | Restricted information requires legal/organizational/technical protection measures | Access control, audit trail, and repeatable smoke verification of critical routes | `EVID-001`, `EVID-004` | backend security tests + compose/browser smoke |
| CTRL-RU-06 | ISPDn safeguards must be documented and attested by class | Security checklist and attestation workflow | `EVID-010` | Manual review of the ISPDn class checklist and attestation |

## Delivery Gate
- Current stage delivery target is local runtime on the current device; production launch is not in scope for this stage.
- `docs/operations/release-checklist.md` is the canonical EPIC-13 pre-prod/production gate.
- `docs/project/production-legal-evidence-package.md` is the canonical repo-backed production sign-off manifest for current evidence, external attachments, blockers, and `verified` exit criteria.
- Development environment is non-blocking for controls in `planned` or `in-progress` status, but those states remain release blockers for EPIC-13.
- Current repo-backed critical controls are:
  - `implemented`: `CTRL-BY-03`, `CTRL-RU-02`, `CTRL-RU-05`, `CTRL-RU-06`
  - `in-progress`: `CTRL-RU-04` (residency location confirmed as Belarus; not RU-compliant)
- Pre-prod promotion requires all critical controls to be at least `implemented`, with current evidence rows and verification commands recorded in `docs/project/evidence-registry.md`.
- Production release additionally requires legal/security sign-off, `verified` status for the implemented critical controls, and explicit closure of the remaining `CTRL-RU-04` residency-location gap.
- `CTRL-BY-03`, `CTRL-RU-02`, and `CTRL-RU-05` stay `implemented` until the package manifest shows fresh release-candidate evidence plus non-repo legal/security approvals for the same release candidate.
- Any critical control that remains `planned` or `in-progress` is a hard blocker for both pre-prod and production release.
- Execution tracking for this matrix is formalized under `EPIC-13` in:
  - `TASK-13-01` (article-level mapping),
  - `TASK-13-02` (evidence ownership model),
  - `TASK-13-03` (release-gate checklist),
  - `TASK-13-04` (production legal evidence package).
- TODO(owner: business-analyst + legal, due_trigger: before first production release): approve final status and evidence completeness for all critical controls.
