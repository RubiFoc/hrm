# ISPDn Class Checklist and Attestation (CTRL-RU-06)

## Last Updated
- Date: 2026-03-23
- Updated by: coordinator
- Approver: sole maintainer (self-approval)

## ISPDn Class
- Class: UZ-4 (minimal)

## Checklist (Baseline)
- Access control and RBAC are enforced for staff/admin workflows (see `docs/project/rbac-matrix.md`).
- Auth/session lifecycle is defined and enforced (see `docs/project/auth-session-lifecycle.md`).
- Audit logging is enabled for sensitive actions (see `docs/project/export-package-audit-kpi.md`).
- Local-only storage with no cloud providers in use (see `docs/project/evidence/ru-data-residency-pack.md`).
- Encryption policy baseline is documented in `docs/operations/runbook.md`.
- Daily local backups are required (see `docs/project/evidence/ru-data-residency-pack.md`).
- Incident escalation and response expectations are documented in `docs/operations/runbook.md`.

## Attestation
I confirm the checklist above reflects the current local-only environment as of 2026-03-23.

Signed: sole maintainer (self)
