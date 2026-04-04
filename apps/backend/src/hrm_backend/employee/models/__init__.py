"""SQLAlchemy models for employee-domain persistence."""

from hrm_backend.employee.models.avatar import EmployeeProfileAvatar
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.models.template import OnboardingTemplate, OnboardingTemplateItem

__all__ = [
    "HireConversion",
    "EmployeeProfile",
    "EmployeeProfileAvatar",
    "OnboardingRun",
    "OnboardingTask",
    "OnboardingTemplate",
    "OnboardingTemplateItem",
]
