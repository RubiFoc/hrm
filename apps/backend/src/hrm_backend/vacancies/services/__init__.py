"""Vacancy service exports with lazy imports to prevent import cycles.

The package re-exports public service classes while keeping module initialization
lightweight for unit and integration test collection.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hrm_backend.vacancies.services.application_service import VacancyApplicationService
    from hrm_backend.vacancies.services.public_apply_policy import PublicApplyPolicyService
    from hrm_backend.vacancies.services.public_apply_rate_limiter import PublicApplyRateLimiter
    from hrm_backend.vacancies.services.vacancy_service import VacancyService

__all__ = [
    "VacancyService",
    "VacancyApplicationService",
    "PublicApplyRateLimiter",
    "PublicApplyPolicyService",
]


def __getattr__(name: str) -> Any:
    """Resolve public vacancy service symbols lazily on first access."""
    if name == "VacancyService":
        from hrm_backend.vacancies.services.vacancy_service import VacancyService

        return VacancyService
    if name == "VacancyApplicationService":
        from hrm_backend.vacancies.services.application_service import VacancyApplicationService

        return VacancyApplicationService
    if name == "PublicApplyRateLimiter":
        from hrm_backend.vacancies.services.public_apply_rate_limiter import PublicApplyRateLimiter

        return PublicApplyRateLimiter
    if name == "PublicApplyPolicyService":
        from hrm_backend.vacancies.services.public_apply_policy import PublicApplyPolicyService

        return PublicApplyPolicyService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
