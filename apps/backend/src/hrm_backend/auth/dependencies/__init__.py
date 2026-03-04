"""Dependency providers for auth domain."""

from hrm_backend.auth.dependencies.auth import get_auth_service, get_current_auth_context

__all__ = ["get_auth_service", "get_current_auth_context"]
