"""Exports for department schemas."""

from hrm_backend.departments.schemas.department import (
    DepartmentCreateRequest,
    DepartmentListItemResponse,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdateRequest,
)

__all__ = [
    "DepartmentCreateRequest",
    "DepartmentUpdateRequest",
    "DepartmentResponse",
    "DepartmentListItemResponse",
    "DepartmentListResponse",
]
