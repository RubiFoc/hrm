# Legal Controls Matrix (Belarus + Russia)

## Last Updated
- Date: 2026-03-04
- Updated by: business-analyst + backend-engineer

## Status Legend
- `planned`: control designed, not implemented.
- `in-progress`: implementation started.
- `implemented`: implemented in code/process.
- `verified`: evidence and legal/security review completed.

## Matrix

| Jurisdiction | NPA | Obligation (short) | Control ID | Product/Process Control | Owner | Status | Evidence |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Belarus | Law No. 99-З (2021) | Lawful and secure personal data processing | CTRL-BY-01 | Data inventory and processing purpose registry | business-analyst | planned | `docs/project/data-inventory.md` (to create) |
| Belarus | Law No. 99-З (2021) | Data subject rights handling | CTRL-BY-02 | Request workflow: access/correction/deletion SLA | backend + hr-ops | planned | `docs/operations/runbook.md` update |
| Belarus | Law No. 455-З (2008) | Information protection measures | CTRL-BY-03 | Encryption at rest/in transit + RBAC + audit logs | architect + backend | implemented | `docs/project/rbac-matrix.md`, `docs/project/auth-session-lifecycle.md`, `apps/backend/src/hrm_backend/audit/`, `apps/backend/src/hrm_backend/rbac.py` |
| Russia | Federal Law 152-ФЗ | Personal data processing lawfulness and minimization | CTRL-RU-01 | Personal data classification and minimization policy | business-analyst | planned | Policy doc (to create) |
| Russia | Federal Law 152-ФЗ | Security of PD information systems | CTRL-RU-02 | Threat model + protection controls baseline | architect + security | planned | `docs/architecture/decisions.md` entry |
| Russia | Federal Law 242-ФЗ | Localization of Russian citizens' data | CTRL-RU-03 | Data residency control for RU citizen records | architect + devops | planned | Infrastructure ADR (to create) |
| Russia | Federal Law 149-ФЗ | Information security and access protection | CTRL-RU-04 | Access control enforcement and immutable audit trail | backend | implemented | `docs/project/rbac-matrix.md`, `docs/project/auth-session-lifecycle.md`, `apps/backend/alembic/versions/20260304_000002_audit_events.py`, `apps/backend/src/hrm_backend/audit/`, PR #37 |
| Russia | Decree No. 1119 (2012) | Organizational and technical PD protection requirements | CTRL-RU-05 | Security control checklist per ISPDn class | security + business-analyst | planned | Security checklist (to create) |

## Control Detail (Obligation -> Control -> Evidence)

| Control ID | Obligation Detail | Technical/Process Control | Evidence Baseline | Verification Baseline |
| --- | --- | --- | --- | --- |
| CTRL-BY-01 | Keep lawful basis and processing purpose for each PD category | Data inventory registry + purpose mapping document | `docs/project/data-inventory.md` (planned) | Legal review checklist before prod |
| CTRL-BY-02 | Handle subject access/correction/deletion requests within SLA | Runbook procedure + ticket workflow + actor responsibility | `docs/operations/runbook.md` request handling section (planned) | Quarterly SLA evidence audit |
| CTRL-BY-03 | Ensure confidentiality and integrity of PD systems | Encryption in transit, encryption at rest, RBAC, immutable audit events | `docs/operations/runbook.md`, `docs/project/rbac-matrix.md`, PR #37 | Security review + penetration test report |
| CTRL-RU-01 | Minimize collected PD and justify processing | Data minimization policy per domain object and API payload | Policy doc (planned) | Product/legal sign-off before prod |
| CTRL-RU-02 | Define protection baseline by threat model | Threat model + compensating controls registry | `docs/architecture/decisions.md` entry (planned) | Security architecture review |
| CTRL-RU-03 | Localize RU citizens data in approved jurisdiction | Infrastructure placement controls + backup residency checks | Infra ADR (planned) | DevOps/legal go-live checklist |
| CTRL-RU-04 | Enforce access controls and immutable logging | Unified policy evaluator for API/jobs + append-only audit events | PR #37 + `docs/project/auth-session-lifecycle.md` | Integration tests + DB audit trail sampling |
| CTRL-RU-05 | Apply organizational/technical ISPDn safeguards | Control checklist by class + periodic control attestations | Security checklist (planned) | External/internal security audit |

## Delivery Gate
- Development environment is non-blocking for controls in `planned` or `in-progress` status.
- Production release is blocked until all critical controls (`CTRL-BY-03`, `CTRL-RU-02`, `CTRL-RU-03`, `CTRL-RU-04`, `CTRL-RU-05`) reach at least `implemented`.
- Production release is additionally blocked until legal sign-off confirms `verified` status and attached evidence for critical controls.
- TODO(owner: business-analyst + legal, due_trigger: before first production release): approve final status and evidence completeness for all critical controls.
