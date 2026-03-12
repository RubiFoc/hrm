"""DAO for vacancy persistence operations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.schemas.vacancy import VacancyCreateRequest, VacancyUpdateRequest


class VacancyDAO:
    """Data-access helper for vacancy rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_vacancy(
        self,
        payload: VacancyCreateRequest,
        *,
        hiring_manager_staff_id: str | None = None,
    ) -> Vacancy:
        """Insert vacancy row.

        Args:
            payload: Vacancy create payload.
            hiring_manager_staff_id: Optional assigned manager identifier resolved by service.

        Returns:
            Vacancy: Persisted vacancy entity.
        """
        entity = Vacancy(
            title=payload.title,
            description=payload.description,
            department=payload.department,
            status=payload.status,
            hiring_manager_staff_id=hiring_manager_staff_id,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_by_id(self, vacancy_id: str) -> Vacancy | None:
        """Fetch vacancy by identifier.

        Args:
            vacancy_id: Vacancy identifier.

        Returns:
            Vacancy | None: Matching row or `None`.
        """
        return self._session.get(Vacancy, vacancy_id)

    def list_vacancies(self) -> list[Vacancy]:
        """Load all vacancies sorted by creation order."""
        return list(
            self._session.query(Vacancy)
            .order_by(Vacancy.created_at.asc(), Vacancy.vacancy_id.asc())
            .all()
        )

    def list_by_hiring_manager_staff_id(self, hiring_manager_staff_id: str) -> list[Vacancy]:
        """Load vacancies assigned to one manager.

        Args:
            hiring_manager_staff_id: Manager staff-account identifier that scopes the query.

        Returns:
            list[Vacancy]: Assigned vacancies ordered by most recent update.
        """
        return list(
            self._session.query(Vacancy)
            .filter(Vacancy.hiring_manager_staff_id == hiring_manager_staff_id)
            .order_by(Vacancy.updated_at.desc(), Vacancy.vacancy_id.asc())
            .all()
        )

    def update_vacancy(self, entity: Vacancy, payload: VacancyUpdateRequest) -> Vacancy:
        """Apply partial vacancy update and persist changes.

        Args:
            entity: Existing vacancy row.
            payload: Patch payload.

        Returns:
            Vacancy: Updated vacancy row.
        """
        for field_name, value in payload.model_dump(
            exclude_none=True,
            exclude={"hiring_manager_login"},
        ).items():
            setattr(entity, field_name, value)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
