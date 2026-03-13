"""Dependency providers for notification APIs and emitters."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_staff_account_dao
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.core.db.session import get_db_session
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.notifications.services.notification_service import NotificationService
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]
StaffAccountDAODependency = Annotated[StaffAccountDAO, Depends(get_staff_account_dao)]


def get_notification_service(
    session: SessionDependency,
    audit_service: AuditDependency,
    staff_account_dao: StaffAccountDAODependency,
) -> NotificationService:
    """Build notification service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.
        audit_service: Audit service dependency for protected notification API access traces.
        staff_account_dao: DAO for recipient role and subject resolution.

    Returns:
        NotificationService: In-app notification read/update/emission service.
    """
    return NotificationService(
        notification_dao=NotificationDAO(session=session),
        staff_account_dao=staff_account_dao,
        task_dao=OnboardingTaskDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        audit_service=audit_service,
    )
