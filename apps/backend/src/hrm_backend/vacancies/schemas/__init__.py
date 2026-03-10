"""Pydantic schemas for vacancy and pipeline APIs."""

from hrm_backend.vacancies.schemas.application import PublicVacancyApplicationResponse
from hrm_backend.vacancies.schemas.offer import (
    OfferDecisionRequest,
    OfferResponse,
    OfferUpsertRequest,
)
from hrm_backend.vacancies.schemas.pipeline import (
    PipelineTransitionCreateRequest,
    PipelineTransitionResponse,
)
from hrm_backend.vacancies.schemas.vacancy import (
    VacancyCreateRequest,
    VacancyListResponse,
    VacancyResponse,
    VacancyUpdateRequest,
)

__all__ = [
    "VacancyCreateRequest",
    "VacancyUpdateRequest",
    "VacancyResponse",
    "VacancyListResponse",
    "PipelineTransitionCreateRequest",
    "PipelineTransitionResponse",
    "PublicVacancyApplicationResponse",
    "OfferUpsertRequest",
    "OfferDecisionRequest",
    "OfferResponse",
]
