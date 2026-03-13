"""Dependency exports for the finance adapter package."""

from hrm_backend.finance.dependencies.accounting import get_accounting_workspace_service

__all__ = ["get_accounting_workspace_service"]
