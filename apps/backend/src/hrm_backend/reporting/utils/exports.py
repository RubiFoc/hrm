"""Binary export helpers for KPI snapshot attachments."""

from __future__ import annotations

import csv
from io import BytesIO, StringIO
from typing import Any

from hrm_backend.reporting.schemas.kpi_snapshot import KpiSnapshotReadResponse

KPI_SNAPSHOT_EXPORT_COLUMNS: tuple[str, ...] = (
    "period_month",
    "metric_key",
    "metric_value",
    "generated_at",
)


def render_kpi_snapshot_csv(snapshot: KpiSnapshotReadResponse) -> bytes:
    """Render one KPI snapshot response into UTF-8 CSV attachment bytes."""
    buffer = StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(KPI_SNAPSHOT_EXPORT_COLUMNS)
    period_month = snapshot.period_month.isoformat()
    for metric in snapshot.metrics:
        serialized = metric.model_dump(mode="json")
        writer.writerow(
            [
                period_month,
                serialized["metric_key"],
                serialized["metric_value"],
                serialized["generated_at"],
            ]
        )
    return buffer.getvalue().encode("utf-8")


def render_kpi_snapshot_xlsx(snapshot: KpiSnapshotReadResponse) -> bytes:
    """Render one KPI snapshot response into one XLSX workbook."""
    from openpyxl import Workbook

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "kpi_snapshot"
    worksheet.append(list(KPI_SNAPSHOT_EXPORT_COLUMNS))
    period_month = snapshot.period_month.isoformat()
    for metric in snapshot.metrics:
        worksheet.append(
            _row_values(
                period_month=period_month,
                metric=metric.model_dump(mode="json"),
            )
        )

    payload = BytesIO()
    workbook.save(payload)
    workbook.close()
    return payload.getvalue()


def _row_values(*, period_month: str, metric: dict[str, Any]) -> list[Any]:
    """Build ordered worksheet row values for one KPI metric entry."""
    return [period_month, metric["metric_key"], metric["metric_value"], metric["generated_at"]]
