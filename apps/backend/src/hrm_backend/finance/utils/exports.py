"""Binary export helpers for accountant workspace attachments."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from hrm_backend.finance.schemas.workspace import AccountingWorkspaceRowResponse

ACCOUNTING_WORKSPACE_EXPORT_COLUMNS: tuple[str, ...] = (
    "onboarding_id",
    "employee_id",
    "first_name",
    "last_name",
    "email",
    "location",
    "current_title",
    "start_date",
    "offer_terms_summary",
    "onboarding_status",
    "accountant_task_total",
    "accountant_task_pending",
    "accountant_task_in_progress",
    "accountant_task_completed",
    "accountant_task_overdue",
    "latest_accountant_due_at",
)


def render_accounting_workspace_csv(rows: list[AccountingWorkspaceRowResponse]) -> bytes:
    """Render accountant workspace rows into CSV attachment bytes."""
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(ACCOUNTING_WORKSPACE_EXPORT_COLUMNS)
    for row in rows:
        writer.writerow(_row_values(row))
    return buffer.getvalue().encode("utf-8")


def render_accounting_workspace_xlsx(rows: list[AccountingWorkspaceRowResponse]) -> bytes:
    """Render accountant workspace rows into one XLSX workbook."""
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "accounting_workspace"
    worksheet.append(list(ACCOUNTING_WORKSPACE_EXPORT_COLUMNS))
    for row in rows:
        worksheet.append(_row_values(row))

    payload = BytesIO()
    workbook.save(payload)
    workbook.close()
    return payload.getvalue()


def _row_values(row: AccountingWorkspaceRowResponse) -> list[Any]:
    """Extract ordered export cell values from one accountant workspace row."""
    serialized = row.model_dump(mode="json")
    return [serialized[column] for column in ACCOUNTING_WORKSPACE_EXPORT_COLUMNS]
