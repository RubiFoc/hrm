"""Routers for auth and admin API endpoints."""

from hrm_backend.auth.routers.admin_v1 import router as admin_router
from hrm_backend.auth.routers.v1 import router as auth_router

__all__ = ["auth_router", "admin_router"]
