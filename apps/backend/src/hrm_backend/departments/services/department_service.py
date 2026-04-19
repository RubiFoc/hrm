"""Business service for department reference data."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status

from hrm_backend.departments.dao.department_dao import DepartmentDAO
from hrm_backend.departments.schemas.department import (
    DepartmentCreateRequest,
    DepartmentListItemResponse,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdateRequest,
)


class DepartmentService:
    """Orchestrates department CRUD and list operations."""

    def __init__(self, *, department_dao: DepartmentDAO) -> None:
        """Initialize department service dependencies.

        Args:
            department_dao: DAO for department persistence.
        """
        self._department_dao = department_dao

    def list_departments(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
    ) -> DepartmentListResponse:
        """List departments with pagination and optional search.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result.
            search: Optional search term for name filtering.

        Returns:
            DepartmentListResponse: Paginated list payload.
        """
        items = self._department_dao.list_departments(limit=limit, offset=offset, search=search)
        total = self._department_dao.count_departments(search=search)
        payload_items = [
            DepartmentListItemResponse(
                department_id=UUID(entity.department_id),
                name=entity.name,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            for entity in items
        ]
        return DepartmentListResponse(items=payload_items, total=total, limit=limit, offset=offset)

    def get_department(self, *, department_id: UUID) -> DepartmentResponse:
        """Return one department by identifier.

        Args:
            department_id: Department identifier.

        Returns:
            DepartmentResponse: Department payload.

        Raises:
            HTTPException: When department is missing.
        """
        entity = self._department_dao.get_by_id(str(department_id))
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="department_not_found",
            )
        return DepartmentResponse(
            department_id=UUID(entity.department_id),
            name=entity.name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def create_department(self, *, payload: DepartmentCreateRequest) -> DepartmentResponse:
        """Create a new department.

        Args:
            payload: Department create request.

        Returns:
            DepartmentResponse: Created department payload.

        Raises:
            HTTPException: When department name already exists.
        """
        normalized_name = _normalize_department_name(payload.name)
        if self._department_dao.get_by_name(normalized_name) is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="department_name_exists",
            )
        entity = self._department_dao.create_department(name=normalized_name)
        return DepartmentResponse(
            department_id=UUID(entity.department_id),
            name=entity.name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def update_department(
        self,
        *,
        department_id: UUID,
        payload: DepartmentUpdateRequest,
    ) -> DepartmentResponse:
        """Update department name.

        Args:
            department_id: Department identifier.
            payload: Department update request.

        Returns:
            DepartmentResponse: Updated department payload.

        Raises:
            HTTPException: When department is missing, patch is empty, or name collides.
        """
        if payload.name is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="empty_patch",
            )
        normalized_name = _normalize_department_name(payload.name)
        entity = self._department_dao.get_by_id(str(department_id))
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="department_not_found",
            )
        existing = self._department_dao.get_by_name(normalized_name)
        if existing is not None and existing.department_id != entity.department_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="department_name_exists",
            )
        entity = self._department_dao.update_department(entity=entity, name=normalized_name)
        return DepartmentResponse(
            department_id=UUID(entity.department_id),
            name=entity.name,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )


def _normalize_department_name(value: str) -> str:
    """Normalize department name input.

    Args:
        value: Raw department name input.

    Returns:
        str: Trimmed department name.

    Raises:
        HTTPException: When the resulting name is empty.
    """
    normalized = value.strip()
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="invalid_department_name",
        )
    return normalized
