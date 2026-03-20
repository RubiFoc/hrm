"""Read-only public vacancy listing service for the careers page."""

from __future__ import annotations

from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.schemas.public_vacancy import (
    PublicVacancyListItemResponse,
    PublicVacancyListResponse,
)


class PublicVacancyService:
    """Expose open vacancies for the public careers board."""

    def __init__(self, *, vacancy_dao: VacancyDAO) -> None:
        """Initialize the service with read-only persistence access.

        Args:
            vacancy_dao: Vacancy DAO used to load open vacancies.
        """
        self._vacancy_dao = vacancy_dao

    def list_public_vacancies(self) -> PublicVacancyListResponse:
        """Return only open vacancies in deterministic display order."""
        vacancies = self._vacancy_dao.list_public_vacancies()
        return PublicVacancyListResponse(
            items=[self._to_public_vacancy_item(entity) for entity in vacancies],
        )

    def _to_public_vacancy_item(self, entity: Vacancy) -> PublicVacancyListItemResponse:
        """Map a vacancy row to a public card payload."""
        return PublicVacancyListItemResponse(
            vacancy_id=entity.vacancy_id,
            title=entity.title,
            description=entity.description,
            department=entity.department,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )
