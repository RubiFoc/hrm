"""Dependency providers for admin API service wiring."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.admin.dao.employee_registration_key_dao import AdminEmployeeRegistrationKeyDAO
from hrm_backend.admin.dao.staff_account_dao import AdminStaffAccountDAO
from hrm_backend.admin.services.admin_service import AdminService
from hrm_backend.auth.dependencies.auth import get_password_service
from hrm_backend.auth.infra.security.password_service import PasswordService
from hrm_backend.core.db.session import get_db_session

SessionDependency = Annotated[Session, Depends(get_db_session)]
PasswordServiceDependency = Annotated[PasswordService, Depends(get_password_service)]


def get_admin_service(
    session: SessionDependency,
    password_service: PasswordServiceDependency,
) -> AdminService:
    """Build admin service dependency.

    Args:
        session: Active SQLAlchemy session.
        password_service: Password hashing adapter.

    Returns:
        AdminService: Fully wired admin domain service.
    """
    return AdminService(
        staff_account_dao=AdminStaffAccountDAO(session=session),
        employee_registration_key_dao=AdminEmployeeRegistrationKeyDAO(session=session),
        password_service=password_service,
    )
