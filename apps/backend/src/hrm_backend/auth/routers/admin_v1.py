"""Admin APIs for staff account and employee key management."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.dependencies.auth import get_auth_service, get_current_auth_context
from hrm_backend.auth.schemas.requests import AdminCreateEmployeeKeyRequest, AdminCreateStaffRequest
from hrm_backend.auth.schemas.responses import EmployeeRegistrationKeyResponse, StaffResponse
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.auth.services.auth_service import AuthService
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/admin", tags=["admin"])
AuthServiceDependency = Annotated[AuthService, Depends(get_auth_service)]
AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
AdminCreateStaffRole = Annotated[Role, Depends(require_permission("admin:staff:create"))]
AdminCreateEmployeeKeyRole = Annotated[
    Role,
    Depends(require_permission("admin:employee_key:create")),
]


@router.post("/staff", response_model=StaffResponse)
def create_staff(
    payload: AdminCreateStaffRequest,
    request: Request,
    _: AdminCreateStaffRole,
    auth_context: CurrentAuthContext,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> StaffResponse:
    """Create staff account directly via admin privileges."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = auth_service.create_staff_account(
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


@router.post("/employee-keys", response_model=EmployeeRegistrationKeyResponse)
def create_employee_key(
    payload: AdminCreateEmployeeKeyRequest,
    request: Request,
    _: AdminCreateEmployeeKeyRole,
    auth_context: CurrentAuthContext,
    auth_service: AuthServiceDependency,
    audit_service: AuditServiceDependency,
) -> EmployeeRegistrationKeyResponse:
    """Issue one-time employee registration key for self-registration."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = auth_service.create_employee_key(
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
