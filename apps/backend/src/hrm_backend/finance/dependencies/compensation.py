"""Dependency providers for compensation services."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.core.db.session import get_db_session
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.finance.dao.bonus_entry_dao import BonusEntryDAO
from hrm_backend.finance.dao.compensation_raise_confirmation_dao import (
    CompensationRaiseConfirmationDAO,
)
from hrm_backend.finance.dao.compensation_raise_request_dao import CompensationRaiseRequestDAO
from hrm_backend.finance.dao.salary_band_dao import SalaryBandDAO
from hrm_backend.finance.services.compensation_service import CompensationService
from hrm_backend.settings import AppSettings, get_settings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

SessionDependency = Annotated[Session, Depends(get_db_session)]
SettingsDependency = Annotated[AppSettings, Depends(get_settings)]
AuditDependency = Annotated[AuditService, Depends(get_audit_service)]


def get_compensation_service(
    settings: SettingsDependency,
    session: SessionDependency,
    audit_service: AuditDependency,
) -> CompensationService:
    """Build compensation service dependency."""
    return CompensationService(
        settings=settings,
        session=session,
        raise_request_dao=CompensationRaiseRequestDAO(session=session),
        confirmation_dao=CompensationRaiseConfirmationDAO(session=session),
        salary_band_dao=SalaryBandDAO(session=session),
        bonus_entry_dao=BonusEntryDAO(session=session),
        employee_profile_dao=EmployeeProfileDAO(session=session),
        vacancy_dao=VacancyDAO(session=session),
        audit_service=audit_service,
    )
