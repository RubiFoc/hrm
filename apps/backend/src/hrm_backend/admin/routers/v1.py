"""Version 1 admin APIs for staff account and employee key management."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status

from hrm_backend.admin.dependencies.admin import get_admin_service
from hrm_backend.admin.schemas.requests import (
    AdminCreateEmployeeKeyRequest,
    AdminCreateStaffRequest,
    AdminStaffUpdateRequest,
    EmployeeKeyStatusClaim,
    StaffRoleClaim,
)
from hrm_backend.admin.schemas.responses import (
    AdminEmployeeKeyListItem,
    AdminEmployeeKeyListResponse,
    AdminStaffListResponse,
    EmployeeRegistrationKeyResponse,
    StaffResponse,
)
from hrm_backend.admin.services.admin_service import AdminService
from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
AdminServiceDependency = Annotated[AdminService, Depends(get_admin_service)]
AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
AdminCreateStaffRole = Annotated[Role, Depends(require_permission("admin:staff:create"))]
AdminCreateEmployeeKeyRole = Annotated[
    Role,
    Depends(require_permission("admin:employee_key:create")),
]
AdminListEmployeeKeyRole = Annotated[
    Role,
    Depends(require_permission("admin:employee_key:list")),
]
AdminRevokeEmployeeKeyRole = Annotated[
    Role,
    Depends(require_permission("admin:employee_key:revoke")),
]
AdminStaffListRole = Annotated[Role, Depends(require_permission("admin:staff:list"))]
AdminStaffUpdateRole = Annotated[Role, Depends(require_permission("admin:staff:update"))]


@router.post("/staff", response_model=StaffResponse)
def create_staff(
    payload: AdminCreateStaffRequest,
    request: Request,
    _: AdminCreateStaffRole,
    auth_context: CurrentAuthContext,
    admin_service: AdminServiceDependency,
    audit_service: AuditServiceDependency,
) -> StaffResponse:
    """Create staff account directly via admin privileges."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = admin_service.create_staff_account(
            login=payload.login,
            email=payload.email,
            password=payload.password,
            role=payload.role,
            is_active=payload.is_active,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="admin.staff:create",
            resource_type="staff_account",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=str(exc.detail),
        )
        raise

    audit_service.record_api_event(
        action="admin.staff:create",
        resource_type="staff_account",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=str(response.staff_id),
    )
    return response


@router.get("/staff", response_model=AdminStaffListResponse)
def list_staff(
    request: Request,
    _: AdminStaffListRole,
    auth_context: CurrentAuthContext,
    admin_service: AdminServiceDependency,
    audit_service: AuditServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    search: Annotated[str | None, Query()] = None,
    role: Annotated[StaffRoleClaim | None, Query()] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> AdminStaffListResponse:
    """List staff accounts with pagination and optional filters."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = admin_service.list_staff_accounts(
            limit=limit,
            offset=offset,
            search=search,
            role=role,
            is_active=is_active,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="admin.staff:list",
            resource_type="staff_account",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=_extract_reason_code(exc),
        )
        raise

    audit_service.record_api_event(
        action="admin.staff:list",
        resource_type="staff_account",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
    )
    return response


@router.patch(
    "/staff/{staff_id}",
    response_model=StaffResponse,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Staff account not found"},
        status.HTTP_409_CONFLICT: {"description": "Strict safety guard conflict"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def patch_staff(
    staff_id: UUID,
    payload: AdminStaffUpdateRequest,
    request: Request,
    _: AdminStaffUpdateRole,
    auth_context: CurrentAuthContext,
    admin_service: AdminServiceDependency,
    audit_service: AuditServiceDependency,
) -> StaffResponse:
    """Patch staff account role and/or active-state through admin privileges."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = admin_service.update_staff_account(
            staff_id=staff_id,
            role=payload.role,
            is_active=payload.is_active,
            actor_subject_id=auth_context.subject_id,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="admin.staff:update",
            resource_type="staff_account",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(staff_id),
            reason=_extract_reason_code(exc),
        )
        raise

    audit_service.record_api_event(
        action="admin.staff:update",
        resource_type="staff_account",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=str(response.staff_id),
    )
    return response


@router.post("/employee-keys", response_model=EmployeeRegistrationKeyResponse)
def create_employee_key(
    payload: AdminCreateEmployeeKeyRequest,
    request: Request,
    _: AdminCreateEmployeeKeyRole,
    auth_context: CurrentAuthContext,
    admin_service: AdminServiceDependency,
    audit_service: AuditServiceDependency,
) -> EmployeeRegistrationKeyResponse:
    """Issue one-time employee registration key for self-registration."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = admin_service.create_employee_key(
            target_role=payload.target_role,
            created_by_staff_id=auth_context.subject_id,
            ttl_seconds=payload.ttl_seconds,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="admin.employee_key:create",
            resource_type="employee_registration_key",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=str(exc.detail),
        )
        raise

    audit_service.record_api_event(
        action="admin.employee_key:create",
        resource_type="employee_registration_key",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=str(response.key_id),
    )
    return response


@router.get("/employee-keys", response_model=AdminEmployeeKeyListResponse)
def list_employee_keys(
    request: Request,
    _: AdminListEmployeeKeyRole,
    auth_context: CurrentAuthContext,
    admin_service: AdminServiceDependency,
    audit_service: AuditServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    target_role: Annotated[StaffRoleClaim | None, Query()] = None,
    key_status: Annotated[EmployeeKeyStatusClaim | None, Query(alias="status")] = None,
    created_by_staff_id: Annotated[UUID | None, Query()] = None,
    search: Annotated[str | None, Query()] = None,
) -> AdminEmployeeKeyListResponse:
    """List employee registration keys with pagination and optional filters."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = admin_service.list_employee_keys(
            limit=limit,
            offset=offset,
            target_role=target_role,
            key_status=key_status,
            created_by_staff_id=created_by_staff_id,
            search=search,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="admin.employee_key:list",
            resource_type="employee_registration_key",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=_extract_reason_code(exc),
        )
        raise

    audit_service.record_api_event(
        action="admin.employee_key:list",
        resource_type="employee_registration_key",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
    )
    return response


@router.post(
    "/employee-keys/{key_id}/revoke",
    response_model=AdminEmployeeKeyListItem,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Employee key not found"},
        status.HTTP_409_CONFLICT: {"description": "Employee key is not revocable"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def revoke_employee_key(
    key_id: UUID,
    request: Request,
    _: AdminRevokeEmployeeKeyRole,
    auth_context: CurrentAuthContext,
    admin_service: AdminServiceDependency,
    audit_service: AuditServiceDependency,
) -> AdminEmployeeKeyListItem:
    """Revoke active employee registration key."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = admin_service.revoke_employee_key(
            key_id=key_id,
            revoked_by_staff_id=auth_context.subject_id,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="admin.employee_key:revoke",
            resource_type="employee_registration_key",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(key_id),
            reason=_extract_reason_code(exc),
        )
        raise

    audit_service.record_api_event(
        action="admin.employee_key:revoke",
        resource_type="employee_registration_key",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        resource_id=str(response.key_id),
    )
    return response


def _extract_reason_code(exc: HTTPException) -> str:
    """Normalize `HTTPException.detail` to audit-friendly reason code.

    Args:
        exc: Raised HTTP exception from route business flow.

    Returns:
        str: Reason code to store in audit event payload.
    """
    if isinstance(exc.detail, str) and exc.detail.strip():
        return exc.detail.strip()
    return "validation_failed"
