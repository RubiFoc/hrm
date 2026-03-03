# Legal Controls Matrix (Belarus + Russia)

## Last Updated
- Date: 2026-03-04
- Updated by: business-analyst

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
| Belarus | Law No. 455-З (2008) | Information protection measures | CTRL-BY-03 | Encryption at rest/in transit + RBAC + audit logs | architect + backend | in-progress | `docs/architecture/overview.md`, TASK-01-04 |
| Russia | Federal Law 152-ФЗ | Personal data processing lawfulness and minimization | CTRL-RU-01 | Personal data classification and minimization policy | business-analyst | planned | Policy doc (to create) |
| Russia | Federal Law 152-ФЗ | Security of PD information systems | CTRL-RU-02 | Threat model + protection controls baseline | architect + security | planned | `docs/architecture/decisions.md` entry |
| Russia | Federal Law 242-ФЗ | Localization of Russian citizens' data | CTRL-RU-03 | Data residency control for RU citizen records | architect + devops | planned | Infrastructure ADR (to create) |
| Russia | Federal Law 149-ФЗ | Information security and access protection | CTRL-RU-04 | Access control enforcement and immutable audit trail | backend | in-progress | TASK-01-03, TASK-01-04 |
| Russia | Decree No. 1119 (2012) | Organizational and technical PD protection requirements | CTRL-RU-05 | Security control checklist per ISPDn class | security + business-analyst | planned | Security checklist (to create) |

## Delivery Gate
- V1 development can start with `planned`/`in-progress` controls.
- Production readiness is blocked until all critical controls (`CTRL-BY-03`, `CTRL-RU-02`, `CTRL-RU-03`, `CTRL-RU-04`, `CTRL-RU-05`) are at least `implemented`.
- Legal sign-off requires `verified` status with evidence links.
