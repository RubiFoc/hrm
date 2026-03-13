"""Versioned HTTP routes for KPI snapshot reporting."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.rbac import Role, require_permission
from hrm_backend.reporting.dependencies.reporting import get_kpi_snapshot_service
from hrm_backend.reporting.schemas.kpi_snapshot import (
    KpiSnapshotReadResponse,
    KpiSnapshotRebuildRequest,
)
from hrm_backend.reporting.services.kpi_snapshot_service import KpiSnapshotService
from hrm_backend.reporting.utils.dates import ensure_month_start

router = APIRouter(prefix="/api/v1/reporting/kpi-snapshots", tags=["reporting"])
KpiSnapshotServiceDependency = Annotated[
    KpiSnapshotService,
    Depends(get_kpi_snapshot_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
KpiSnapshotReadRole = Annotated[Role, Depends(require_permission("kpi_snapshot:read"))]
KpiSnapshotRebuildRole = Annotated[Role, Depends(require_permission("kpi_snapshot:rebuild"))]
PeriodMonthQuery = Annotated[date, Query()]


def _resolve_period_month(period_month: PeriodMonthQuery) -> date:
    """Validate and normalize the period month query parameter."""
    try:
        return ensure_month_start(period_month)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        ) from exc


@router.post("/rebuild", response_model=KpiSnapshotReadResponse)
def rebuild_kpi_snapshot(
    payload: KpiSnapshotRebuildRequest,
    request: Request,
    _: KpiSnapshotRebuildRole,
    auth_context: CurrentAuthContext,
    service: KpiSnapshotServiceDependency,
) -> KpiSnapshotReadResponse:
    """Rebuild KPI snapshot rows for a single month."""
    return service.rebuild_monthly_snapshot(
        period_month=payload.period_month,
        auth_context=auth_context,
        request=request,
    )


@router.get("", response_model=KpiSnapshotReadResponse)
def read_kpi_snapshot(
    request: Request,
    _: KpiSnapshotReadRole,
    auth_context: CurrentAuthContext,
    service: KpiSnapshotServiceDependency,
    period_month: Annotated[date, Depends(_resolve_period_month)],
) -> KpiSnapshotReadResponse:
    """Read KPI snapshot rows for a single month."""
    return service.get_monthly_snapshot(
        period_month=period_month,
        auth_context=auth_context,
        request=request,
    )
