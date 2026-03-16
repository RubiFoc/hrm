"""Dependency providers for automation rule services and evaluators."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_staff_account_dao
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.dao.execution_log_dao import AutomationExecutionLogDAO
from hrm_backend.automation.services.automation_rule_service import AutomationRuleService
from hrm_backend.automation.services.evaluator import AutomationEvaluator
from hrm_backend.automation.services.execution_log_service import AutomationExecutionLogService
from hrm_backend.automation.services.executor import AutomationActionExecutor
from hrm_backend.core.db.session import get_db_session
from hrm_backend.notifications.dao.notification_dao import NotificationDAO

SessionDependency = Annotated[Session, Depends(get_db_session)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]
StaffAccountDAODependency = Annotated[StaffAccountDAO, Depends(get_staff_account_dao)]


def get_automation_rule_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> AutomationRuleService:
    """Build automation rule CRUD service for current request."""
    return AutomationRuleService(
        rule_dao=AutomationRuleDAO(session=session),
        audit_service=audit_service,
    )


def get_automation_evaluator(
    session: SessionDependency,
    staff_account_dao: StaffAccountDAODependency,
) -> AutomationEvaluator:
    """Build automation evaluator for the current request session."""
    return AutomationEvaluator(
        rule_dao=AutomationRuleDAO(session=session),
        staff_account_dao=staff_account_dao,
    )


def get_automation_executor(
    session: SessionDependency,
    staff_account_dao: StaffAccountDAODependency,
) -> AutomationActionExecutor:
    """Build automation executor for the current request session."""
    evaluator = AutomationEvaluator(
        rule_dao=AutomationRuleDAO(session=session),
        staff_account_dao=staff_account_dao,
    )
    return AutomationActionExecutor(
        evaluator=evaluator,
        notification_dao=NotificationDAO(session=session),
    )


def get_automation_execution_log_service(
    session: SessionDependency,
    audit_service: AuditDependency,
) -> AutomationExecutionLogService:
    """Build automation execution log read service for the current request session."""
    return AutomationExecutionLogService(
        dao=AutomationExecutionLogDAO(session=session),
        audit_service=audit_service,
    )
