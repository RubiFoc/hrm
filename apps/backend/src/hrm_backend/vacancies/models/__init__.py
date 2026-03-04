"""SQLAlchemy models for vacancy domain."""

from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy

__all__ = ["Vacancy", "PipelineTransition"]
