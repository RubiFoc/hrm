"""Unit tests for the public vacancy board service."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.core.models.base import Base
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.services.public_vacancy_service import PublicVacancyService


def test_public_vacancy_service_returns_only_open_roles_in_latest_order() -> None:
    """Verify public careers board exposes only open vacancies and keeps display order stable."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            session.add_all(
                [
                    Vacancy(
                        vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                        title="Senior Python Engineer",
                        description="Build public APIs and internal tooling.",
                        department="Engineering",
                        status="open",
                        created_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
                        updated_at=datetime(2026, 3, 12, 8, 30, tzinfo=UTC),
                    ),
                    Vacancy(
                        vacancy_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                        title="Recruiter",
                        description="Keep hiring pipelines healthy.",
                        department="People",
                        status="paused",
                        created_at=datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
                        updated_at=datetime(2026, 3, 11, 8, 30, tzinfo=UTC),
                    ),
                    Vacancy(
                        vacancy_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                        title="Data Analyst",
                        description="Own reporting quality and dashboards.",
                        department="Analytics",
                        status="OPEN",
                        created_at=datetime(2026, 3, 11, 8, 0, tzinfo=UTC),
                        updated_at=datetime(2026, 3, 13, 8, 30, tzinfo=UTC),
                    ),
                ]
            )
            session.commit()

            service = PublicVacancyService(vacancy_dao=VacancyDAO(session=session))
            payload = service.list_public_vacancies()

        assert [item.title for item in payload.items] == [
            "Data Analyst",
            "Senior Python Engineer",
        ]
        assert [item.department for item in payload.items] == ["Analytics", "Engineering"]
        assert all(hasattr(item, "vacancy_id") for item in payload.items)
    finally:
        engine.dispose()
