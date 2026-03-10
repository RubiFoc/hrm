"""PostgreSQL adapters for vacancy domain."""

from hrm_backend.vacancies.dao.offer_dao import OfferDAO
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

__all__ = ["VacancyDAO", "PipelineTransitionDAO", "OfferDAO"]
