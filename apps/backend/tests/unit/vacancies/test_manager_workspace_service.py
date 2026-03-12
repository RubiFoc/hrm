"""Unit tests for manager workspace vacancy visibility and snapshot ordering."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.services.manager_workspace_service import (
    MANAGER_WORKSPACE_VACANCY_NOT_FOUND,
    ManagerWorkspaceService,
)


class _AuditServiceStub(AuditService):
    """Audit double used for focused manager workspace tests."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_api_event(self, **kwargs) -> None:  # type: ignore[override]
        """Capture API audit payloads for assertions when needed."""
        self.events.append(kwargs)


def _build_request(path: str) -> Request:
    """Create minimal Starlette request object for service calls."""
    return Request(
        {
            "type": "http",
            "method": "GET",
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
    )


def _build_auth_context(subject_id: str) -> AuthContext:
    """Create deterministic manager auth context for tests."""
    return AuthContext(
        subject_id=UUID(subject_id),
        role="manager",
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


def _seed_manager_workspace(session: Session) -> dict[str, str]:
    """Insert staff, vacancy, candidate, document, pipeline, and interview fixtures."""
    manager_one_id = "11111111-1111-4111-8111-111111111111"
    manager_two_id = "22222222-2222-4222-8222-222222222222"
    session.add_all(
        [
            StaffAccount(
                staff_id=manager_one_id,
                login="manager-alpha",
                email="manager-alpha@example.com",
                password_hash="hash",
                role="manager",
                is_active=True,
            ),
            StaffAccount(
                staff_id=manager_two_id,
                login="manager-beta",
                email="manager-beta@example.com",
                password_hash="hash",
                role="manager",
                is_active=True,
            ),
        ]
    )
    session.add_all(
        [
            Vacancy(
                vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                title="Platform Engineer",
                description="Build internal platforms.",
                department="Engineering",
                status="open",
                hiring_manager_staff_id=manager_one_id,
                created_at=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 12, 8, 30, tzinfo=UTC),
            ),
            Vacancy(
                vacancy_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                title="QA Lead",
                description="Own release quality.",
                department="Quality",
                status="paused",
                hiring_manager_staff_id=manager_one_id,
                created_at=datetime(2026, 3, 9, 8, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 11, 8, 30, tzinfo=UTC),
            ),
            Vacancy(
                vacancy_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                title="Data Engineer",
                description="Build data pipelines.",
                department="Data",
                status="open",
                hiring_manager_staff_id=manager_two_id,
                created_at=datetime(2026, 3, 8, 8, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 8, 12, 0, tzinfo=UTC),
            ),
        ]
    )
    session.add_all(
        [
            CandidateProfile(
                candidate_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                owner_subject_id="candidate-alpha",
                first_name="Ada",
                last_name="Lovelace",
                email="ada@example.com",
                phone=None,
                location="Minsk",
                current_title="Backend Engineer",
                extra_data={},
                updated_at=datetime(2026, 3, 12, 8, 45, tzinfo=UTC),
            ),
            CandidateProfile(
                candidate_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                owner_subject_id="candidate-beta",
                first_name="Grace",
                last_name="Hopper",
                email="grace@example.com",
                phone=None,
                location="Brest",
                current_title="Staff Engineer",
                extra_data={},
                updated_at=datetime(2026, 3, 12, 9, 10, tzinfo=UTC),
            ),
            CandidateProfile(
                candidate_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
                owner_subject_id="candidate-gamma",
                first_name="Katherine",
                last_name="Johnson",
                email="katherine@example.com",
                phone=None,
                location="Gomel",
                current_title="QA Manager",
                extra_data={},
                updated_at=datetime(2026, 3, 11, 9, 10, tzinfo=UTC),
            ),
            CandidateProfile(
                candidate_id="12121212-1212-4212-8212-121212121212",
                owner_subject_id="candidate-delta",
                first_name="Tim",
                last_name="Berners-Lee",
                email="tim@example.com",
                phone=None,
                location="Mogilev",
                current_title="Data Engineer",
                extra_data={},
                updated_at=datetime(2026, 3, 8, 9, 0, tzinfo=UTC),
            ),
        ]
    )
    session.add_all(
        [
            CandidateDocument(
                candidate_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                object_key="cv/ada.pdf",
                filename="ada.pdf",
                mime_type="application/pdf",
                size_bytes=100,
                checksum_sha256="a" * 64,
                is_active=True,
                parsed_profile_json={
                    "skills": ["python", "systems design"],
                    "experience": {"years_total": 6},
                },
                evidence_json=[],
                detected_language="en",
                parsed_at=datetime(2026, 3, 12, 8, 40, tzinfo=UTC),
            ),
            CandidateDocument(
                candidate_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                object_key="cv/grace.pdf",
                filename="grace.pdf",
                mime_type="application/pdf",
                size_bytes=100,
                checksum_sha256="b" * 64,
                is_active=True,
                parsed_profile_json=None,
                evidence_json=None,
                detected_language="unknown",
                parsed_at=None,
            ),
        ]
    )
    session.add_all(
        [
            PipelineTransition(
                transition_id="13131313-1313-4313-8313-131313131313",
                vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                candidate_id="dddddddd-dddd-4ddd-8ddd-dddddddddddd",
                from_stage=None,
                to_stage="screening",
                reason="initial review",
                changed_by_sub="hr-1",
                changed_by_role="hr",
                transitioned_at=datetime(2026, 3, 12, 8, 50, tzinfo=UTC),
            ),
            PipelineTransition(
                transition_id="14141414-1414-4414-8414-141414141414",
                vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                candidate_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                from_stage="screening",
                to_stage="shortlist",
                reason="technical match",
                changed_by_sub="hr-1",
                changed_by_role="hr",
                transitioned_at=datetime(2026, 3, 12, 9, 20, tzinfo=UTC),
            ),
            PipelineTransition(
                transition_id="15151515-1515-4515-8515-151515151515",
                vacancy_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                candidate_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
                from_stage="shortlist",
                to_stage="interview",
                reason="panel approved",
                changed_by_sub="hr-2",
                changed_by_role="hr",
                transitioned_at=datetime(2026, 3, 11, 10, 0, tzinfo=UTC),
            ),
            PipelineTransition(
                transition_id="16161616-1616-4616-8616-161616161616",
                vacancy_id="cccccccc-cccc-4ccc-8ccc-cccccccccccc",
                candidate_id="12121212-1212-4212-8212-121212121212",
                from_stage=None,
                to_stage="applied",
                reason="new application",
                changed_by_sub="hr-3",
                changed_by_role="hr",
                transitioned_at=datetime(2026, 3, 8, 9, 30, tzinfo=UTC),
            ),
        ]
    )
    session.add_all(
        [
            Interview(
                interview_id="17171717-1717-4717-8717-171717171717",
                vacancy_id="aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                candidate_id="eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                status="awaiting_candidate_confirmation",
                calendar_sync_status="synced",
                schedule_version=1,
                scheduled_start_at=datetime.now(UTC) + timedelta(days=1),
                scheduled_end_at=datetime.now(UTC) + timedelta(days=1, hours=1),
                timezone="Europe/Minsk",
                location_kind="google_meet",
                location_details="meet",
                interviewer_staff_ids_json=[manager_one_id],
                candidate_response_status="pending",
                created_by_staff_id="hr-1",
                updated_by_staff_id="hr-1",
                created_at=datetime(2026, 3, 12, 9, 25, tzinfo=UTC),
                updated_at=datetime(2026, 3, 12, 9, 25, tzinfo=UTC),
                last_synced_at=datetime(2026, 3, 12, 9, 25, tzinfo=UTC),
            ),
            Interview(
                interview_id="18181818-1818-4818-8818-181818181818",
                vacancy_id="bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
                candidate_id="ffffffff-ffff-4fff-8fff-ffffffffffff",
                status="confirmed",
                calendar_sync_status="synced",
                schedule_version=1,
                scheduled_start_at=datetime.now(UTC) + timedelta(days=2),
                scheduled_end_at=datetime.now(UTC) + timedelta(days=2, hours=1),
                timezone="Europe/Minsk",
                location_kind="onsite",
                location_details="HQ",
                interviewer_staff_ids_json=[manager_one_id],
                candidate_response_status="confirmed",
                created_by_staff_id="hr-2",
                updated_by_staff_id="hr-2",
                created_at=datetime(2026, 3, 11, 10, 5, tzinfo=UTC),
                updated_at=datetime(2026, 3, 11, 10, 5, tzinfo=UTC),
                last_synced_at=datetime(2026, 3, 11, 10, 5, tzinfo=UTC),
            ),
        ]
    )
    session.commit()
    return {
        "manager_one_id": manager_one_id,
        "manager_two_vacancy_id": "cccccccc-cccc-4ccc-8ccc-cccccccccccc",
        "manager_one_primary_vacancy_id": "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
    }


def test_manager_workspace_overview_is_scoped_and_sorted() -> None:
    """Verify overview returns only assigned vacancies with aggregate hiring counters."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            seeded = _seed_manager_workspace(session)
            service = ManagerWorkspaceService(
                vacancy_dao=VacancyDAO(session=session),
                transition_dao=PipelineTransitionDAO(session=session),
                profile_dao=CandidateProfileDAO(session=session),
                document_dao=CandidateDocumentDAO(session=session),
                interview_dao=InterviewDAO(session=session),
                staff_account_dao=StaffAccountDAO(session=session),
                audit_service=_AuditServiceStub(),
            )

            response = service.get_overview(
                auth_context=_build_auth_context(seeded["manager_one_id"]),
                request=_build_request("/api/v1/vacancies/manager-workspace"),
            )

            assert response.summary.vacancy_count == 2
            assert response.summary.open_vacancy_count == 1
            assert response.summary.candidate_count == 3
            assert response.summary.active_interview_count == 2
            assert response.summary.upcoming_interview_count == 2
            assert [str(item.vacancy_id) for item in response.items] == [
                "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
                "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb",
            ]
            assert response.items[0].hiring_manager_login == "manager-alpha"
            assert response.items[0].candidate_count == 2
            assert response.items[1].candidate_count == 1
    finally:
        engine.dispose()


def test_manager_workspace_candidate_snapshot_filters_outside_scope_and_orders_rows() -> None:
    """Verify vacancy snapshot respects scope, stage counts, and deterministic ordering."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            seeded = _seed_manager_workspace(session)
            service = ManagerWorkspaceService(
                vacancy_dao=VacancyDAO(session=session),
                transition_dao=PipelineTransitionDAO(session=session),
                profile_dao=CandidateProfileDAO(session=session),
                document_dao=CandidateDocumentDAO(session=session),
                interview_dao=InterviewDAO(session=session),
                staff_account_dao=StaffAccountDAO(session=session),
                audit_service=_AuditServiceStub(),
            )

            response = service.get_candidate_snapshot(
                vacancy_id=UUID(seeded["manager_one_primary_vacancy_id"]),
                auth_context=_build_auth_context(seeded["manager_one_id"]),
                request=_build_request(
                    "/api/v1/vacancies/aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa/manager-workspace/candidates"
                ),
            )

            assert response.summary.candidate_count == 2
            assert response.summary.active_interview_count == 1
            assert response.summary.stage_counts.screening == 1
            assert response.summary.stage_counts.shortlist == 1
            assert [str(item.candidate_id) for item in response.items] == [
                "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee",
                "dddddddd-dddd-4ddd-8ddd-dddddddddddd",
            ]
            assert response.items[0].analysis_ready is False
            assert response.items[1].analysis_ready is True
            assert response.items[1].years_experience == 6
            assert response.items[1].skills == ["python", "systems design"]

            with pytest.raises(HTTPException) as exc_info:
                service.get_candidate_snapshot(
                    vacancy_id=UUID(seeded["manager_two_vacancy_id"]),
                    auth_context=_build_auth_context(seeded["manager_one_id"]),
                    request=_build_request(
                        "/api/v1/vacancies/cccccccc-cccc-4ccc-8ccc-cccccccccccc/manager-workspace/candidates"
                    ),
                )
            assert exc_info.value.status_code == 404
            assert exc_info.value.detail == MANAGER_WORKSPACE_VACANCY_NOT_FOUND
    finally:
        engine.dispose()
