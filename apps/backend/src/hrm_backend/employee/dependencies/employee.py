"""Dependency providers for employee-domain services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_staff_account_dao
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.core.db.session import get_db_session
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.hire_conversion_dao import HireConversionDAO
from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.dao.onboarding_task_dao import OnboardingTaskDAO
from hrm_backend.employee.dao.onboarding_template_dao import OnboardingTemplateDAO
from hrm_backend.employee.services.employee_onboarding_portal_service import (
    EmployeeOnboardingPortalService,
)
from hrm_backend.employee.services.employee_profile_service import EmployeeProfileService
from hrm_backend.employee.services.hire_conversion_service import HireConversionService
from hrm_backend.employee.services.onboarding_dashboard_service import (
    OnboardingDashboardService,
)
from hrm_backend.employee.services.onboarding_service import OnboardingRunService
from hrm_backend.employee.services.onboarding_task_service import OnboardingTaskService
from hrm_backend.employee.services.onboarding_template_service import (
    OnboardingTemplateService,
)

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]
StaffAccountDAODependency = Annotated[StaffAccountDAO, Depends(get_staff_account_dao)]


def get_hire_conversion_service(session: SessionDependency) -> HireConversionService:
    """Build hire-conversion service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.

    Returns:
        HireConversionService: Employee-domain handoff service.
    """
    return HireConversionService(dao=HireConversionDAO(session=session))


def get_employee_profile_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> EmployeeProfileService:
    """Build employee profile service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.
        audit_service: Audit service dependency for success/failure traces.

    Returns:
        EmployeeProfileService: Employee profile bootstrap service.
    """
    return EmployeeProfileService(
        session=session,
        hire_conversion_dao=HireConversionDAO(session=session),
        profile_dao=EmployeeProfileDAO(session=session),
        onboarding_service=OnboardingRunService(dao=OnboardingRunDAO(session=session)),
        onboarding_task_service=OnboardingTaskService(
            session=session,
            run_dao=OnboardingRunDAO(session=session),
            task_dao=OnboardingTaskDAO(session=session),
            template_dao=OnboardingTemplateDAO(session=session),
            audit_service=audit_service,
        ),
        audit_service=audit_service,
    )


def get_onboarding_template_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> OnboardingTemplateService:
    """Build onboarding checklist template service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.
        audit_service: Audit service dependency for success/failure traces.

    Returns:
        OnboardingTemplateService: Staff-facing onboarding template management service.
    """
    return OnboardingTemplateService(
        session=session,
        dao=OnboardingTemplateDAO(session=session),
        audit_service=audit_service,
    )


def get_onboarding_task_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> OnboardingTaskService:
    """Build onboarding task service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.
        audit_service: Audit service dependency for success/failure traces.

    Returns:
        OnboardingTaskService: Staff-facing onboarding task generation and update service.
    """
    return OnboardingTaskService(
        session=session,
        run_dao=OnboardingRunDAO(session=session),
        task_dao=OnboardingTaskDAO(session=session),
        template_dao=OnboardingTemplateDAO(session=session),
        audit_service=audit_service,
    )


def get_employee_onboarding_portal_service(
    session: SessionDependency,
    audit_service: AuditDependency,
    staff_account_dao: StaffAccountDAODependency,
) -> EmployeeOnboardingPortalService:
    """Build employee self-service onboarding portal service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.
        audit_service: Audit service dependency for success/failure traces.
        staff_account_dao: DAO for authenticated staff-account lookups.

    Returns:
        EmployeeOnboardingPortalService: Employee-facing onboarding portal service.
    """
    return EmployeeOnboardingPortalService(
        profile_dao=EmployeeProfileDAO(session=session),
        run_dao=OnboardingRunDAO(session=session),
        task_dao=OnboardingTaskDAO(session=session),
        staff_account_dao=staff_account_dao,
        audit_service=audit_service,
    )


def get_onboarding_dashboard_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> OnboardingDashboardService:
    """Build onboarding progress dashboard service for the current request session.

    Args:
        session: SQLAlchemy session bound to the current request scope.
        audit_service: Audit service dependency for success/failure traces.

    Returns:
        OnboardingDashboardService: Staff-facing onboarding progress dashboard service.
    """
    return OnboardingDashboardService(
        profile_dao=EmployeeProfileDAO(session=session),
        run_dao=OnboardingRunDAO(session=session),
        task_dao=OnboardingTaskDAO(session=session),
        audit_service=audit_service,
    )
