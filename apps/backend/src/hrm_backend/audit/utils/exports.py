"""Binary export helpers for audit event attachments."""

from __future__ import annotations

import csv
import json
from io import BytesIO, StringIO

from hrm_backend.audit.schemas.read import AuditEventListItem

AUDIT_EVENT_EXPORT_COLUMNS: tuple[str, ...] = (
    "event_id",
    "occurred_at",
    "source",
    "actor_sub",
    "actor_role",
    "action",
    "resource_type",
    "resource_id",
    "result",
    "reason",
    "correlation_id",
    "ip",
    "user_agent",
)


def render_audit_events_csv(items: list[AuditEventListItem]) -> bytes:
    """Render audit event items into UTF-8 CSV attachment bytes."""
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(AUDIT_EVENT_EXPORT_COLUMNS)
    for item in items:
        serialized = item.model_dump(mode="json")
        writer.writerow([serialized[column] for column in AUDIT_EVENT_EXPORT_COLUMNS])
    return buffer.getvalue().encode("utf-8")


def render_audit_events_jsonl(items: list[AuditEventListItem]) -> bytes:
    """Render audit event items into UTF-8 JSONL attachment bytes."""
    lines = [
        json.dumps(
            item.model_dump(mode="json"),
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for item in items
    ]
    return ("\n".join(lines) + ("\n" if lines else "")).encode("utf-8")


def render_audit_events_xlsx(items: list[AuditEventListItem]) -> bytes:
    """Render audit event items into one XLSX workbook attachment."""
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "audit_events"
    worksheet.freeze_panes = "A2"
    worksheet.append(list(AUDIT_EVENT_EXPORT_COLUMNS))
    for item in items:
        worksheet.append(_row_values(item))

    payload = BytesIO()
    workbook.save(payload)
    workbook.close()
    return payload.getvalue()


def _row_values(item: AuditEventListItem) -> list[object]:
    """Extract ordered export cell values from one audit event row."""
    serialized = item.model_dump(mode="json")
    return [serialized[column] for column in AUDIT_EVENT_EXPORT_COLUMNS]
