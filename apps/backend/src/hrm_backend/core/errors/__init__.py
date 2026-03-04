"""Shared error factories for HTTP-facing backend components."""

from hrm_backend.core.errors.http import service_unavailable, unauthorized

__all__ = ["unauthorized", "service_unavailable"]
