# RU Data-Residency Evidence Pack (CTRL-RU-04)

## Last Updated
- Date: 2026-03-23
- Updated by: coordinator
- Approver: sole maintainer (self-approval)

## Scope
- Applies to the current local-only environment for this repository.
- No cloud providers or external hosting platforms are in use.

## Storage Locality
- Primary storage: local workstation filesystem on the maintainer's machine.
- Datastores: local Docker volumes for Postgres/Redis/MinIO and local repo files.
- External storage: none.

## Backup Policy
- Frequency: daily.
- Location: local-only on the same machine (no offsite or cloud replication).
- Owner: sole maintainer.

## Residency Confirmation Status
- Physical location of the workstation is not documented in this pack.
- Production compliance for RU residency requires explicit confirmation that the host location is in RU
  or a migration to RU-local infrastructure.

## Evidence Statement
I confirm the statements above reflect the current storage and backup setup as of 2026-03-23.

Signed: sole maintainer (self)
