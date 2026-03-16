"""Business service for KPI snapshot aggregation and reads."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from fastapi import Request

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.reporting.dao.kpi_aggregation_dao import KpiAggregationDAO
from hrm_backend.reporting.dao.kpi_snapshot_dao import KpiSnapshotDAO
from hrm_backend.reporting.models.kpi_snapshot import KpiSnapshot
from hrm_backend.reporting.schemas.export import KpiSnapshotExportFormat
from hrm_backend.reporting.schemas.kpi_snapshot import (
    KpiSnapshotMetric,
    KpiSnapshotReadResponse,
)
from hrm_backend.reporting.utils.dates import month_bounds
from hrm_backend.reporting.utils.exports import render_kpi_snapshot_csv, render_kpi_snapshot_xlsx
from hrm_backend.reporting.utils.metrics import KPI_METRIC_KEYS


@dataclass(frozen=True)
class KpiSnapshotExportPayload:
    """Binary export payload returned by KPI snapshot export method.

    Attributes:
        content: Attachment bytes.
        media_type: HTTP content type for the attachment.
        filename: Attachment filename returned in `Content-Disposition`.
    """

    content: bytes
    media_type: str
    filename: str


class KpiSnapshotService:
    """Aggregate and read monthly KPI snapshots."""

    def __init__(
        self,
        *,
        snapshot_dao: KpiSnapshotDAO,
        aggregation_dao: KpiAggregationDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize KPI snapshot service dependencies.

        Args:
            snapshot_dao: DAO for KPI snapshot persistence.
            aggregation_dao: DAO for aggregation reads across domain tables.
            audit_service: Audit service used to record KPI snapshot access.
        """
        self._snapshot_dao = snapshot_dao
        self._aggregation_dao = aggregation_dao
        self._audit_service = audit_service

    def rebuild_monthly_snapshot(
        self,
        *,
        period_month: date,
        auth_context: AuthContext,
        request: Request,
    ) -> KpiSnapshotReadResponse:
        """Rebuild and replace KPI snapshot rows for one calendar month.

        Args:
            period_month: First day of the month to rebuild.
            auth_context: Authenticated actor context for audit logging.
            request: Active FastAPI request.

        Returns:
            KpiSnapshotReadResponse: Rebuilt KPI snapshot payload.
        """
        start_at, end_at = month_bounds(period_month)
        generated_at = datetime.now(UTC)
        metrics_by_key = {
            "vacancies_created_count": self._aggregation_dao.count_vacancies_created(
                start_at=start_at,
                end_at=end_at,
            ),
            "candidates_applied_count": self._aggregation_dao.count_candidates_applied(
                start_at=start_at,
                end_at=end_at,
            ),
            "interviews_scheduled_count": self._aggregation_dao.count_interviews_scheduled(
                start_at=start_at,
                end_at=end_at,
            ),
            "offers_sent_count": self._aggregation_dao.count_offers_sent(
                start_at=start_at,
                end_at=end_at,
            ),
            "offers_accepted_count": self._aggregation_dao.count_offers_accepted(
                start_at=start_at,
                end_at=end_at,
            ),
            "hires_count": self._aggregation_dao.count_hires(
                start_at=start_at,
                end_at=end_at,
            ),
            "onboarding_started_count": self._aggregation_dao.count_onboarding_started(
                start_at=start_at,
                end_at=end_at,
            ),
            "onboarding_tasks_completed_count": (
                self._aggregation_dao.count_onboarding_tasks_completed(
                    start_at=start_at,
                    end_at=end_at,
                )
            ),
        }

        snapshots = [
            KpiSnapshot(
                period_month=period_month,
                metric_key=metric_key,
                metric_value=metrics_by_key[metric_key],
                generated_at=generated_at,
            )
            for metric_key in KPI_METRIC_KEYS
        ]
        self._snapshot_dao.replace_monthly_snapshots(
            period_month=period_month,
            snapshots=snapshots,
        )

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="kpi_snapshot:rebuild",
            resource_type="kpi_snapshot",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=period_month.isoformat(),
        )
        return KpiSnapshotReadResponse(
            period_month=period_month,
            metrics=[
                KpiSnapshotMetric(
                    metric_key=metric_key,
                    metric_value=metrics_by_key[metric_key],
                    generated_at=generated_at,
                )
                for metric_key in KPI_METRIC_KEYS
            ],
        )

    def get_monthly_snapshot(
        self,
        *,
        period_month: date,
        auth_context: AuthContext,
        request: Request,
    ) -> KpiSnapshotReadResponse:
        """Read KPI snapshot rows for a month without live aggregation.

        Args:
            period_month: First day of the month to read.
            auth_context: Authenticated actor context for audit logging.
            request: Active FastAPI request.

        Returns:
            KpiSnapshotReadResponse: Snapshot payload for the month or empty result when missing.
        """
        metrics = self._build_snapshot_metrics(period_month=period_month)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="kpi_snapshot:read",
            resource_type="kpi_snapshot",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=period_month.isoformat(),
        )
        return KpiSnapshotReadResponse(period_month=period_month, metrics=metrics)

    def export_monthly_snapshot(
        self,
        *,
        period_month: date,
        auth_context: AuthContext,
        request: Request,
        export_format: KpiSnapshotExportFormat,
    ) -> KpiSnapshotExportPayload:
        """Render the stored KPI snapshot for a month as a downloadable attachment.

        Args:
            period_month: First day of the month to export.
            auth_context: Authenticated actor context for audit logging.
            request: Active FastAPI request.
            export_format: Requested attachment format (`csv` or `xlsx`).

        Returns:
            KpiSnapshotExportPayload: Attachment bytes and metadata.

        Side effects:
            - records one `kpi_snapshot:export` audit event after content assembly.
        """
        response = KpiSnapshotReadResponse(
            period_month=period_month,
            metrics=self._build_snapshot_metrics(period_month=period_month),
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        if export_format == "csv":
            payload = KpiSnapshotExportPayload(
                content=render_kpi_snapshot_csv(response),
                media_type="text/csv",
                filename=f"kpi-snapshot-{period_month.isoformat()}-{timestamp}.csv",
            )
        else:
            payload = KpiSnapshotExportPayload(
                content=render_kpi_snapshot_xlsx(response),
                media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                filename=f"kpi-snapshot-{period_month.isoformat()}-{timestamp}.xlsx",
            )

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="kpi_snapshot:export",
            resource_type="kpi_snapshot_export",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=period_month.isoformat(),
            reason=export_format,
        )
        return payload

    def _build_snapshot_metrics(self, *, period_month: date) -> list[KpiSnapshotMetric]:
        """Build deterministic KPI snapshot metric list for a period month.

        This helper keeps metric ordering stable and applies the same missing/zero-fill
        semantics used by the read API.
        """
        rows = self._snapshot_dao.list_by_period_month(period_month=period_month)
        if not rows:
            return []

        rows_by_key = {row.metric_key: row for row in rows}
        metrics: list[KpiSnapshotMetric] = []
        for metric_key in KPI_METRIC_KEYS:
            row = rows_by_key.get(metric_key)
            metrics.append(
                KpiSnapshotMetric(
                    metric_key=metric_key,
                    metric_value=0 if row is None else row.metric_value,
                    generated_at=None if row is None else row.generated_at,
                )
            )
        return metrics
