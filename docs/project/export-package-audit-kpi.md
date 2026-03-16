# Export Package: Audit + KPI Attachments (TASK-10-04)

## Last Updated
- Date: 2026-03-16
- Updated by: backend-engineer

## Goal
Provide a deterministic, RBAC-protected export surface for:
- compliance/audit evidence review (raw audit events);
- management reporting (stored monthly KPI snapshots).

Non-goals (out of scope for this slice):
- background export jobs, new export tables, or object-storage export artifacts;
- ZIP “export packages” bundling multiple exports;
- unbounded exports (the API must stay safe for synchronous request execution).

## Export Surfaces

### 1) Audit Events Export
- Endpoint: `GET /api/v1/audit/events/export`
- RBAC: `audit:read` (admin-only in Phase 1 matrix)
- Formats:
  - `format=csv` (`text/csv`)
  - `format=jsonl` (`application/x-ndjson`)
- Filters + ordering:
  - Same filters as `GET /api/v1/audit/events`: `action`, `result`, `source`, `resource_type`, `correlation_id`, `occurred_from`, `occurred_to`
  - Same ordering as the list API: `occurred_at DESC`, `event_id DESC`
- Volume constraints:
  - `limit` is required to be bounded (no “export all” in one request thread):
    default `5000`, max `10000`.
  - `offset` is supported for deterministic page-like exports.
- Filename (attachment): `audit-events-<UTC timestamp>.<csv|jsonl>`
- Audit logging:
  - RBAC decision `audit:read` is always audited by the centralized policy evaluator.
  - Business audit event `audit.event:export` is written only after export content assembly so the export does not include its own business audit row.

### 2) KPI Snapshot Export
- Endpoint: `GET /api/v1/reporting/kpi-snapshots/export`
- RBAC: `kpi_snapshot:read` (leader/admin)
- Formats:
  - `format=csv` (`text/csv`)
  - `format=xlsx` (`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`)
- Input scope:
  - `period_month` query param (first day of the calendar month, same validation as the read API).
  - Data source is the stored `kpi_snapshots` month read path (no live aggregation fallback).
- Volume constraints:
  - Snapshot scope is fixed to the known KPI metric key set (small, bounded output).
- Filename (attachment): `kpi-snapshot-<period_month>-<UTC timestamp>.<csv|xlsx>`
- Audit logging:
  - RBAC decision `kpi_snapshot:read` is audited by the centralized policy evaluator.
  - Business audit event `kpi_snapshot:export` is written after export content assembly.
