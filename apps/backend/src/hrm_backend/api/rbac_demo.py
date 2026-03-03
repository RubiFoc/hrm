"""Demo API routes protected by RBAC dependencies.

These handlers validate role access and return deterministic payloads so
integration tests can verify authorization behavior.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends

from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1", tags=["rbac-demo"])


@router.get("/vacancies")
def list_vacancies(role: Role = Depends(require_permission("vacancy:read"))) -> dict[str, object]:
    """Return vacancy listing placeholder for authorized roles.

    Args:
        role: Current role validated by permission dependency.

    Returns:
        dict[str, object]: Empty vacancy data and role metadata.
    """
    return {"items": [], "role": role}


@router.post("/vacancies")
def create_vacancy(role: Role = Depends(require_permission("vacancy:create"))) -> dict[str, str]:
    """Create vacancy placeholder for authorized roles.

    Args:
        role: Current role validated by permission dependency.

    Returns:
        dict[str, str]: Static confirmation payload.
    """
    return {"status": "created", "role": role}


@router.get("/candidate/profile")
def read_own_candidate_profile(
    role: Role = Depends(require_permission("candidate_profile:read_own")),
) -> dict[str, str]:
    """Return own profile placeholder for self-service roles.

    Args:
        role: Current role validated by permission dependency.

    Returns:
        dict[str, str]: Static candidate profile metadata.
    """
    return {"profile": "self", "role": role}


@router.get("/reports/automation")
def read_automation_report(
    role: Role = Depends(require_permission("analytics:read")),
) -> dict[str, object]:
    """Return automation KPI placeholder for reporting roles.

    Args:
        role: Current role validated by permission dependency.

    Returns:
        dict[str, object]: Minimal analytics response.
    """
    return {"metric": "automation_rate", "value": None, "role": role}
