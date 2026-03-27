"""Dependency providers for referral APIs."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_staff_account_dao
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.services.evaluator import AutomationEvaluator
from hrm_backend.automation.services.executor import AutomationActionExecutor
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.dependencies.candidates import get_candidate_storage
from hrm_backend.candidates.infra.minio.storage import CandidateStorage
from hrm_backend.core.db.session import get_db_session
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.referrals.dao.referral_dao import EmployeeReferralDAO
from hrm_backend.referrals.services.referral_service import ReferralService
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

SessionDependency = Annotated[Session, Depends(get_db_session)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]
CandidateStorageDependency = Annotated[CandidateStorage, Depends(get_candidate_storage)]
StaffAccountDependency = Annotated[StaffAccountDAO, Depends(get_staff_account_dao)]


def get_referral_service(
    settings: SettingsDependency,
    session: SessionDependency,
    audit_service: AuditDependency,
    storage: CandidateStorageDependency,
    staff_account_dao: StaffAccountDependency,
) -> ReferralService:
    """Build referral service dependency."""
    automation_evaluator = AutomationEvaluator(
        rule_dao=AutomationRuleDAO(session=session),
        staff_account_dao=staff_account_dao,
    )
    automation_executor = AutomationActionExecutor(
        evaluator=automation_evaluator,
        notification_dao=NotificationDAO(session=session),
    )
    return ReferralService(
        settings=settings,
        session=session,
        referral_dao=EmployeeReferralDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        candidate_profile_dao=CandidateProfileDAO(session=session),
        candidate_document_dao=CandidateDocumentDAO(session=session),
        cv_parsing_job_dao=CVParsingJobDAO(session=session),
        transition_dao=PipelineTransitionDAO(session=session),
        employee_profile_dao=EmployeeProfileDAO(session=session),
        storage=storage,
        automation_executor=automation_executor,
        audit_service=audit_service,
    )
