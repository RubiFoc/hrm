"""Dependency providers for the audit read/query service."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dao.audit_event_read_dao import AuditEventReadDAO
from hrm_backend.audit.services.audit_read_service import AuditReadService
from hrm_backend.core.db.session import get_db_session

SessionDependency = Annotated[Session, Depends(get_db_session)]


def get_audit_read_service(
    session: SessionDependency,
) -> AuditReadService:
    """Build audit read service dependency.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        AuditReadService: Read-only audit service.
    """
    return AuditReadService(dao=AuditEventReadDAO(session=session))

