"""Dependency providers for accountant workspace services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.core.db.session import get_db_session
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.finance.dao import AccountingWorkspaceDAO
from hrm_backend.finance.services.accounting_workspace_service import AccountingWorkspaceService

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]


def get_accounting_workspace_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> AccountingWorkspaceService:
    """Build accountant workspace service dependency."""
    return AccountingWorkspaceService(
        workspace_dao=AccountingWorkspaceDAO(session=session),
        task_dao=OnboardingTaskDAO(session=session),
        audit_service=audit_service,
    )
