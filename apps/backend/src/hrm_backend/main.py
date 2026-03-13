"""Application entrypoint and API wiring for the HRM backend service."""

from __future__ import annotations

from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from hrm_backend.admin.routers.v1 import router as admin_router
from hrm_backend.audit.routers.v1 import router as audit_router
from hrm_backend.auth.routers.v1 import router as auth_router
from hrm_backend.candidates.routers.v1 import public_router as candidate_public_router
from hrm_backend.candidates.routers.v1 import router as candidate_router
from hrm_backend.employee.routers.v1 import router as employee_router
from hrm_backend.finance.routers.v1 import router as finance_router
from hrm_backend.interviews.routers.v1 import public_router as interview_public_router
from hrm_backend.interviews.routers.v1 import router as interview_router
from hrm_backend.notifications.routers.v1 import router as notification_router
from hrm_backend.rbac import ROLE_PERMISSION_MATRIX
from hrm_backend.reporting.routers.v1 import router as reporting_router
from hrm_backend.scoring.routers.v1 import router as scoring_router
from hrm_backend.settings import get_settings
from hrm_backend.vacancies.routers.v1 import router as vacancy_router

settings = get_settings()
app = FastAPI(title="HRM Backend", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allowed_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(auth_router)
app.include_router(admin_router)
app.include_router(audit_router)
app.include_router(candidate_router)
app.include_router(candidate_public_router)
app.include_router(employee_router)
app.include_router(finance_router)
app.include_router(notification_router)
app.include_router(reporting_router)
app.include_router(vacancy_router)
app.include_router(scoring_router)
app.include_router(interview_router)
app.include_router(interview_public_router)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    """Attach correlation ID to request state and outgoing response headers.

    Args:
        request: Incoming HTTP request.
        call_next: Next middleware/route handler in chain.

    Returns:
        Response: Outgoing HTTP response enriched with `X-Request-ID` header.
    """
    request_id = request.headers.get("X-Request-ID") or uuid4().hex
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response


@app.get("/health")
def health() -> dict[str, str]:
    """Return a lightweight service health response.

    Returns:
        dict[str, str]: Static health status payload used by monitoring checks.
    """
    return {"status": "ok"}


@app.get("/rbac/matrix")
def get_rbac_matrix() -> dict[str, list[str]]:
    """Expose sorted RBAC matrix for operational inspection.

    Returns:
        dict[str, list[str]]: Roles mapped to granted permissions.
    """
    return {role: sorted(permissions) for role, permissions in ROLE_PERMISSION_MATRIX.items()}
