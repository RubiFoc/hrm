"""Versioned HTTP routes for department reference data."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from hrm_backend.departments.dependencies.departments import get_department_service
from hrm_backend.departments.schemas.department import (
    DepartmentCreateRequest,
    DepartmentListResponse,
    DepartmentResponse,
    DepartmentUpdateRequest,
)
from hrm_backend.departments.services.department_service import DepartmentService
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/departments", tags=["departments"])
DepartmentServiceDependency = Annotated[DepartmentService, Depends(get_department_service)]
DepartmentListRole = Annotated[Role, Depends(require_permission("department:list"))]
DepartmentReadRole = Annotated[Role, Depends(require_permission("department:read"))]
DepartmentCreateRole = Annotated[Role, Depends(require_permission("department:create"))]
DepartmentUpdateRole = Annotated[Role, Depends(require_permission("department:update"))]
DepartmentSearchQuery = Annotated[str | None, Query(min_length=1, max_length=128)]


@router.get("", response_model=DepartmentListResponse)
def list_departments(
    request: Request,
    _: DepartmentListRole,
    service: DepartmentServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: DepartmentSearchQuery = None,
) -> DepartmentListResponse:
    """List department reference entries."""
    _ = request
    return service.list_departments(limit=limit, offset=offset, search=search)


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: UUID,
    request: Request,
    _: DepartmentReadRole,
    service: DepartmentServiceDependency,
) -> DepartmentResponse:
    """Fetch one department reference entry."""
    _ = request
    return service.get_department(department_id=department_id)


@router.post("", response_model=DepartmentResponse)
def create_department(
    request: Request,
    payload: DepartmentCreateRequest,
    _: DepartmentCreateRole,
    service: DepartmentServiceDependency,
) -> DepartmentResponse:
    """Create a department reference entry."""
    _ = request
    return service.create_department(payload=payload)


@router.patch("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: UUID,
    request: Request,
    payload: DepartmentUpdateRequest,
    _: DepartmentUpdateRole,
    service: DepartmentServiceDependency,
) -> DepartmentResponse:
    """Patch a department reference entry."""
    _ = request
    return service.update_department(department_id=department_id, payload=payload)
