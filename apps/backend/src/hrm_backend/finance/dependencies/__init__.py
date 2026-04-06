"""Dependency exports for the finance domain package."""

from hrm_backend.finance.dependencies.accounting import get_accounting_workspace_service
from hrm_backend.finance.dependencies.compensation import get_compensation_service

__all__ = [
    "get_accounting_workspace_service",
    "get_compensation_service",
]
