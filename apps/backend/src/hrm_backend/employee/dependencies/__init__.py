"""Dependency providers for employee-domain services."""

from hrm_backend.employee.dependencies.employee import (
    get_employee_onboarding_portal_service,
    get_employee_profile_service,
    get_hire_conversion_service,
    get_onboarding_dashboard_service,
    get_onboarding_task_service,
)

__all__ = [
    "get_hire_conversion_service",
    "get_employee_profile_service",
    "get_employee_onboarding_portal_service",
    "get_onboarding_dashboard_service",
    "get_onboarding_task_service",
]
