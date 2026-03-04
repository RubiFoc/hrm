"""Role and permission matrix for API authorization checks.

This module defines the initial RBAC baseline for Phase 1 roles and exposes
runtime helpers that the API layer can use to enforce access policies.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Annotated, Final, Literal

from fastapi import Depends, HTTPException, status

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext

Role = Literal["hr", "candidate", "manager", "employee", "leader", "accountant"]
Permission = Literal[
    "vacancy:read",
    "vacancy:create",
    "pipeline:read",
    "pipeline:update",
    "candidate_profile:read_own",
    "candidate_profile:update_own",
    "candidate_profile:read_all",
    "interview:register",
    "interview:manage",
    "analytics:read",
    "accounting:read",
]

ROLE_PERMISSION_MATRIX: Final[dict[Role, set[Permission]]] = {
    "hr": {
        "vacancy:read",
        "vacancy:create",
        "pipeline:read",
        "pipeline:update",
        "candidate_profile:read_all",
        "interview:manage",
        "analytics:read",
    },
    "candidate": {
        "candidate_profile:read_own",
        "candidate_profile:update_own",
        "interview:register",
    },
    "manager": {
        "vacancy:read",
        "pipeline:read",
        "interview:manage",
        "analytics:read",
    },
    "employee": {
        "candidate_profile:read_own",
        "candidate_profile:update_own",
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

    def dependency(role: Annotated[Role, Depends(get_current_role)]) -> Role:
        if permission not in ROLE_PERMISSION_MATRIX[role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role}' has no permission '{permission}'",
            )
        return role

    return dependency
