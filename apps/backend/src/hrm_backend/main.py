"""Application entrypoint and API wiring for the HRM backend service."""

from fastapi import FastAPI

from hrm_backend.api.auth import router as auth_router
from hrm_backend.api.rbac_demo import router as rbac_demo_router
from hrm_backend.rbac import ROLE_PERMISSION_MATRIX

app = FastAPI(title="HRM Backend", version="0.1.0")
app.include_router(auth_router)
app.include_router(rbac_demo_router)


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
