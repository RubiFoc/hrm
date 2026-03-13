"""Dependency providers for KPI snapshot reporting services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.core.db.session import get_db_session
from hrm_backend.reporting.dao.kpi_aggregation_dao import KpiAggregationDAO
from hrm_backend.reporting.dao.kpi_snapshot_dao import KpiSnapshotDAO
from hrm_backend.reporting.services.kpi_snapshot_service import KpiSnapshotService

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]


def get_kpi_snapshot_service(
    session: SessionDependency,
    audit_service: AuditServiceDependency,
) -> KpiSnapshotService:
    """Build KPI snapshot service dependency.

    Args:
        session: Active SQLAlchemy session.
        audit_service: Audit service for KPI access events.

    Returns:
        KpiSnapshotService: Ready KPI snapshot service.
    """
    return KpiSnapshotService(
        snapshot_dao=KpiSnapshotDAO(session=session),
        aggregation_dao=KpiAggregationDAO(session=session),
        audit_service=audit_service,
    )
