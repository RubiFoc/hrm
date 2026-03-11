"""Role and permission matrix for API authorization checks.

This module defines the initial RBAC baseline for Phase 1 roles and exposes
runtime helpers that the API layer can use to enforce access policies.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated, Final, Literal

from fastapi import Depends, HTTPException, Request, status

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext

Role = Literal["admin", "hr", "manager", "employee", "leader", "accountant"]
Permission = Literal[
    "admin:staff:create",
    "admin:staff:list",
    "admin:staff:update",
    "admin:employee_key:create",
    "admin:employee_key:list",
    "admin:employee_key:revoke",
    "vacancy:read",
    "vacancy:create",
    "vacancy:update",
    "pipeline:read",
    "pipeline:update",
    "pipeline:transition",
    "match_score:create",
    "match_score:read",
    "candidate_profile:create",
    "candidate_profile:read",
    "candidate_profile:update",
    "candidate_profile:list",
    "employee_profile:create",
    "employee_profile:read",
    "employee_portal:read",
    "employee_portal:update",
    "onboarding_dashboard:read",
    "onboarding_task:list",
    "onboarding_task:update",
    "onboarding_task:backfill",
    "onboarding_template:create",
    "onboarding_template:list",
    "onboarding_template:read",
    "onboarding_template:update",
    "candidate_cv:upload",
    "candidate_cv:read",
    "candidate_cv:parsing_status",
    # Backward-compatible aliases retained for existing integrations.
    "candidate_profile:read_all",
    "interview:manage",
    "candidate_cv:parse",
    "analytics:read",
    "accounting:read",
]

ROLE_PERMISSION_MATRIX: Final[dict[Role, set[Permission]]] = {
    "admin": {
        "admin:staff:create",
        "admin:staff:list",
        "admin:staff:update",
        "admin:employee_key:create",
        "admin:employee_key:list",
        "admin:employee_key:revoke",
        "vacancy:read",
        "vacancy:create",
        "vacancy:update",
        "pipeline:read",
        "pipeline:update",
        "pipeline:transition",
        "match_score:create",
        "match_score:read",
        "candidate_profile:create",
        "candidate_profile:read",
        "candidate_profile:update",
        "candidate_profile:list",
        "employee_profile:create",
        "employee_profile:read",
        "onboarding_task:list",
        "onboarding_task:update",
        "onboarding_task:backfill",
        "onboarding_dashboard:read",
        "onboarding_template:create",
        "onboarding_template:list",
        "onboarding_template:read",
        "onboarding_template:update",
        "candidate_cv:upload",
        "candidate_cv:read",
        "candidate_cv:parsing_status",
        "candidate_cv:parse",
        "candidate_profile:read_all",
        "interview:manage",
        "analytics:read",
        "accounting:read",
    },
    "hr": {
        "admin:employee_key:create",
        "admin:employee_key:list",
        "admin:employee_key:revoke",
        "vacancy:read",
        "vacancy:create",
        "vacancy:update",
        "pipeline:read",
        "pipeline:update",
        "pipeline:transition",
        "match_score:create",
        "match_score:read",
        "candidate_profile:create",
        "candidate_profile:read",
        "candidate_profile:update",
        "candidate_profile:list",
        "employee_profile:create",
        "employee_profile:read",
        "onboarding_task:list",
        "onboarding_task:update",
        "onboarding_task:backfill",
        "onboarding_dashboard:read",
        "onboarding_template:create",
        "onboarding_template:list",
        "onboarding_template:read",
        "onboarding_template:update",
        "candidate_cv:upload",
        "candidate_cv:read",
        "candidate_cv:parsing_status",
        "candidate_cv:parse",
        "candidate_profile:read_all",
        "interview:manage",
        "analytics:read",
    },
    "manager": {
        "vacancy:read",
        "pipeline:read",
        "onboarding_dashboard:read",
        "interview:manage",
        "analytics:read",
    },
    "employee": {
        "employee_portal:read",
        "employee_portal:update",
        "analytics:read",
    },
    "leader": {
        "vacancy:read",
        "pipeline:read",
        "analytics:read",
    },
    "accountant": {
        "accounting:read",
        "analytics:read",
    },
}


@dataclass(frozen=True)
class PolicyDecision:
    """Permission decision returned by centralized policy evaluator.

    Attributes:
        role: Evaluated role.
        permission: Evaluated permission.
        allowed: Whether permission is granted.
        reason: Optional deny reason.
    """

    role: Role
    permission: Permission
    allowed: bool
    reason: str | None = None


class BackgroundAccessDeniedError(RuntimeError):
    """Raised when background operation is not authorized by policy evaluator."""


def parse_role(raw_role: str | None) -> Role:
    """Parse and validate role claim value.

    Args:
        raw_role: Role claim from authenticated context.

    Returns:
        Role: Valid normalized role.

    Raises:
        HTTPException: If role is missing or unknown.
    """
    if raw_role is None or not raw_role.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing role claim in authenticated session",
        )

    candidate = raw_role.strip().lower()
    if candidate not in ROLE_PERMISSION_MATRIX:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Unknown role claim: {raw_role}",
        )

    return candidate  # type: ignore[return-value]


def evaluate_permission(role: Role, permission: Permission) -> PolicyDecision:
    """Evaluate role permission against baseline RBAC matrix.

    Args:
        role: Parsed role claim.
        permission: Required permission.

    Returns:
        PolicyDecision: Allow/deny decision with deny reason when applicable.
    """
    allowed = permission in ROLE_PERMISSION_MATRIX[role]
    if allowed:
        return PolicyDecision(role=role, permission=permission, allowed=True)
    return PolicyDecision(
        role=role,
        permission=permission,
        allowed=False,
        reason=f"Role '{role}' has no permission '{permission}'",
    )


def get_current_role(
    auth_context: Annotated[AuthContext, Depends(get_current_auth_context)],
) -> Role:
    """Extract current role from validated authentication context.

    Args:
        auth_context: Validated authentication context.

    Returns:
        Role: Authenticated role resolved from access token claims.
    """
    return parse_role(auth_context.role)


def require_permission(permission: Permission) -> Callable[[Role], Role]:
    """Build dependency that validates role permission for an endpoint.

    Args:
        permission: Permission required to execute route handler.

    Returns:
        Callable[[Role], Role]: Dependency function returning validated role.

    Raises:
        HTTPException: If role does not contain required permission.
    """

    def dependency(
        request: Request,
        auth_context: Annotated[AuthContext, Depends(get_current_auth_context)],
        audit_service: Annotated[AuditService, Depends(get_audit_service)],
    ) -> Role:
        try:
            role = parse_role(auth_context.role)
        except HTTPException as exc:
            audit_service.record_permission_decision(
                permission=permission,
                role=auth_context.role,
                allowed=False,
                request=request,
                actor_sub=str(auth_context.subject_id),
                reason=str(exc.detail),
            )
            raise
        decision = evaluate_permission(role=role, permission=permission)
        audit_service.record_permission_decision(
            permission=permission,
            role=role,
            allowed=decision.allowed,
            request=request,
            actor_sub=str(auth_context.subject_id),
            reason=decision.reason,
        )
        if not decision.allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=decision.reason,
            )
        return role

    return dependency


def enforce_background_permission(
    *,
    subject_id: str | None,
    role: str | None,
    permission: Permission,
    audit_service: AuditService,
    correlation_id: str | None,
) -> None:
    """Enforce RBAC permission for background operation context.

    Args:
        subject_id: Actor subject identifier, if available.
        role: Actor role value.
        permission: Required permission for background operation.
        audit_service: Audit service dependency.
        correlation_id: Background execution correlation identifier.

    Raises:
        BackgroundAccessDeniedError: If role is invalid or permission is not granted.
    """
    try:
        parsed_role = parse_role(role)
    except HTTPException as exc:
        audit_service.record_permission_decision(
            permission=permission,
            role=role,
            allowed=False,
            actor_sub=subject_id,
            correlation_id=correlation_id,
            reason=str(exc.detail),
        )
        raise BackgroundAccessDeniedError(str(exc.detail)) from exc

    decision = evaluate_permission(parsed_role, permission)
    audit_service.record_permission_decision(
        permission=permission,
        role=parsed_role,
        allowed=decision.allowed,
        actor_sub=subject_id,
        correlation_id=correlation_id,
        reason=decision.reason,
    )
    if not decision.allowed:
        raise BackgroundAccessDeniedError(decision.reason or "Background access denied")
