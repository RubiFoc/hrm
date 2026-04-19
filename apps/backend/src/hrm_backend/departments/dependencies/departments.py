"""Dependency providers for the departments domain."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from hrm_backend.core.db.session import get_db_session
from hrm_backend.departments.dao.department_dao import DepartmentDAO
from hrm_backend.departments.services.department_service import DepartmentService

SessionDependency = Annotated[Session, Depends(get_db_session)]


def get_department_dao(session: SessionDependency) -> DepartmentDAO:
    """Build department DAO.

    Args:
        session: Active SQLAlchemy session.

    Returns:
        DepartmentDAO: DAO for department persistence.
    """
    return DepartmentDAO(session=session)


def get_department_service(
    dao: Annotated[DepartmentDAO, Depends(get_department_dao)],
) -> DepartmentService:
    """Build department service.

    Args:
        dao: Department DAO dependency.

    Returns:
        DepartmentService: Department business service.
    """
    return DepartmentService(department_dao=dao)
