"""Dependency providers for audit services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.core.db.session import get_db_session
from hrm_backend.settings import AppSettings, get_settings

SettingsDependency = Annotated[AppSettings, Depends(get_settings)]


def get_audit_service(
    settings: SettingsDependency,
    session: Annotated[Session, Depends(get_db_session)],
) -> AuditService:
    """Build audit service dependency for API and background calls.

    Args:
        settings: Application runtime settings.
        session: SQLAlchemy session.

    Returns:
        AuditService: Ready-to-use audit service.
    """
    del settings
    return AuditService(dao=AuditEventDAO(session=session))
