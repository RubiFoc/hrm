"""Unit tests for KPI snapshot aggregation behavior."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.requests import Request

from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.core.models.base import Base
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.reporting.dao.kpi_aggregation_dao import KpiAggregationDAO
from hrm_backend.reporting.dao.kpi_snapshot_dao import KpiSnapshotDAO
from hrm_backend.reporting.models.kpi_snapshot import KpiSnapshot
from hrm_backend.reporting.services.kpi_snapshot_service import KpiSnapshotService
from hrm_backend.reporting.utils.metrics import KPI_METRIC_KEYS
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy


class _AuditServiceStub:
    """Audit double that stores KPI audit events in memory."""

    def __init__(self) -> None:
        self.events: list[dict[str, object]] = []

    def record_api_event(self, **payload: object) -> None:
        """Capture audit payloads for assertions."""
        self.events.append(payload)


def _build_request(path: str, method: str = "GET") -> Request:
    """Create a minimal Starlette request object for service calls."""
    return Request(
        {
            "type": "http",
            "method": method,
            "path": path,
            "headers": [],
            "client": ("127.0.0.1", 8000),
        }
    )


def _build_auth_context(role: str = "admin") -> AuthContext:
    """Create deterministic auth context for KPI service tests."""
    return AuthContext(
        subject_id=UUID("11111111-1111-4111-8111-111111111111"),
        role=role,
        session_id=uuid4(),
        token_id=uuid4(),
        expires_at=9999999999,
    )


def _build_service(session: Session, audit_service: _AuditServiceStub) -> KpiSnapshotService:
    """Construct KPI snapshot service with test dependencies."""
    return KpiSnapshotService(
        snapshot_dao=KpiSnapshotDAO(session=session),
        aggregation_dao=KpiAggregationDAO(session=session),
        audit_service=audit_service,
    )


def _seed_kpi_sources(session: Session) -> None:
    """Insert one row per KPI source inside March 2026."""
    vacancy_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    candidate_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    offer_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    transition_applied_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    transition_hired_id = "eeeeeeee-eeee-4eee-8eee-eeeeeeeeeeee"
    conversion_id = "ffffffff-ffff-4fff-8fff-ffffffffffff"
    employee_id = "11111111-2222-4333-8444-555555555555"
    onboarding_id = "66666666-7777-4888-8999-000000000000"
    task_id = "12121212-3434-4567-8999-121212121212"

    vacancy = Vacancy(
        vacancy_id=vacancy_id,
        title="Platform Engineer",
        description="Build platform foundations.",
        department="Engineering",
        status="open",
        created_at=datetime(2026, 3, 5, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 5, 9, 0, tzinfo=UTC),
    )
    candidate = CandidateProfile(
        candidate_id=candidate_id,
        owner_subject_id="public",
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone=None,
        location=None,
        current_title=None,
        extra_data={},
        created_at=datetime(2026, 3, 6, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 6, 9, 0, tzinfo=UTC),
    )
    transition_applied = PipelineTransition(
        transition_id=transition_applied_id,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        from_stage=None,
        to_stage="applied",
        reason="public_application",
        changed_by_sub="public",
        changed_by_role="public",
        transitioned_at=datetime(2026, 3, 6, 10, 0, tzinfo=UTC),
    )
    interview = Interview(
        interview_id="99999999-aaaa-4bbb-8ccc-999999999999",
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        status="scheduled",
        calendar_sync_status="pending",
        schedule_version=1,
        scheduled_start_at=datetime(2026, 3, 10, 10, 0, tzinfo=UTC),
        scheduled_end_at=datetime(2026, 3, 10, 11, 0, tzinfo=UTC),
        timezone="UTC",
        location_kind="video",
        location_details=None,
        interviewer_staff_ids_json=["22222222-2222-4222-8222-222222222222"],
        calendar_event_id=None,
        candidate_token_nonce=None,
        candidate_token_hash=None,
        candidate_token_expires_at=None,
        candidate_response_status="pending",
        candidate_response_note=None,
        cancelled_by=None,
        cancel_reason_code=None,
        calendar_sync_reason_code=None,
        calendar_sync_error_detail=None,
        created_by_staff_id="33333333-3333-4333-8333-333333333333",
        updated_by_staff_id="33333333-3333-4333-8333-333333333333",
        created_at=datetime(2026, 3, 7, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 7, 9, 0, tzinfo=UTC),
        last_synced_at=None,
    )
    offer = Offer(
        offer_id=offer_id,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        status="accepted",
        terms_summary="Base offer",
        proposed_start_date=None,
        expires_at=None,
        note=None,
        sent_at=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
        sent_by_staff_id="44444444-4444-4444-8444-444444444444",
        decision_at=datetime(2026, 3, 15, 9, 0, tzinfo=UTC),
        decision_note=None,
        decision_recorded_by_staff_id="44444444-4444-4444-8444-444444444444",
        created_at=datetime(2026, 3, 11, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 15, 9, 0, tzinfo=UTC),
    )
    transition_hired = PipelineTransition(
        transition_id=transition_hired_id,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        from_stage="offer",
        to_stage="hired",
        reason=None,
        changed_by_sub="44444444-4444-4444-8444-444444444444",
        changed_by_role="hr",
        transitioned_at=datetime(2026, 3, 16, 9, 0, tzinfo=UTC),
    )
    conversion = HireConversion(
        conversion_id=conversion_id,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        offer_id=offer_id,
        hired_transition_id=transition_hired_id,
        status="ready",
        candidate_snapshot_json={"first_name": "Ada", "last_name": "Lovelace"},
        offer_snapshot_json={"status": "accepted"},
        converted_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
        converted_by_staff_id="44444444-4444-4444-8444-444444444444",
    )
    employee_profile = EmployeeProfile(
        employee_id=employee_id,
        hire_conversion_id=conversion_id,
        vacancy_id=vacancy_id,
        candidate_id=candidate_id,
        first_name="Ada",
        last_name="Lovelace",
        email="ada@example.com",
        phone=None,
        location=None,
        current_title=None,
        extra_data_json={},
        offer_terms_summary="Base offer",
        start_date=None,
        staff_account_id=None,
        created_by_staff_id="44444444-4444-4444-8444-444444444444",
        created_at=datetime(2026, 3, 16, 12, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 16, 12, 0, tzinfo=UTC),
    )
    onboarding_run = OnboardingRun(
        onboarding_id=onboarding_id,
        employee_id=employee_id,
        hire_conversion_id=conversion_id,
        status="started",
        started_at=datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
        started_by_staff_id="44444444-4444-4444-8444-444444444444",
    )
    onboarding_task = OnboardingTask(
        task_id=task_id,
        onboarding_id=onboarding_id,
        template_id="22222222-3333-4444-8555-666666666666",
        template_item_id="77777777-8888-4999-8aaa-bbbbbbbbbbbb",
        code="welcome",
        title="Welcome",
        description=None,
        sort_order=10,
        is_required=True,
        status="completed",
        assigned_role=None,
        assigned_staff_id=None,
        due_at=None,
        completed_at=datetime(2026, 3, 18, 9, 0, tzinfo=UTC),
        created_at=datetime(2026, 3, 17, 9, 0, tzinfo=UTC),
        updated_at=datetime(2026, 3, 18, 9, 0, tzinfo=UTC),
    )

    session.add_all(
        [
            vacancy,
            candidate,
            transition_applied,
            interview,
            offer,
            transition_hired,
            conversion,
            employee_profile,
            onboarding_run,
            onboarding_task,
        ]
    )
    session.commit()


def test_kpi_snapshot_rebuild_aggregates_all_metrics() -> None:
    """Verify KPI snapshot rebuild aggregates counts from all source domains."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()

    with Session(engine) as session:
        _seed_kpi_sources(session)
        service = _build_service(session, audit_service)
        response = service.rebuild_monthly_snapshot(
            period_month=date(2026, 3, 1),
            auth_context=_build_auth_context(),
            request=_build_request("/api/v1/reporting/kpi-snapshots/rebuild", method="POST"),
        )

        assert {item.metric_key: item.metric_value for item in response.metrics} == {
            "vacancies_created_count": 1,
            "candidates_applied_count": 1,
            "interviews_scheduled_count": 1,
            "offers_sent_count": 1,
            "offers_accepted_count": 1,
            "hires_count": 1,
            "onboarding_started_count": 1,
            "onboarding_tasks_completed_count": 1,
        }


def test_kpi_snapshot_rebuild_zero_fills_for_empty_month() -> None:
    """Verify KPI snapshot rebuild materializes zero values when no data exists."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()

    with Session(engine) as session:
        service = _build_service(session, audit_service)
        response = service.rebuild_monthly_snapshot(
            period_month=date(2026, 4, 1),
            auth_context=_build_auth_context(),
            request=_build_request("/api/v1/reporting/kpi-snapshots/rebuild", method="POST"),
        )

        assert len(response.metrics) == len(KPI_METRIC_KEYS)
        assert all(item.metric_value == 0 for item in response.metrics)


def test_kpi_snapshot_rebuild_is_idempotent_and_replaces_month() -> None:
    """Verify rebuild is deterministic and replaces monthly rows atomically."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    audit_service = _AuditServiceStub()

    with Session(engine) as session:
        _seed_kpi_sources(session)
        service = _build_service(session, audit_service)
        first = service.rebuild_monthly_snapshot(
            period_month=date(2026, 3, 1),
            auth_context=_build_auth_context(),
            request=_build_request("/api/v1/reporting/kpi-snapshots/rebuild", method="POST"),
        )
        second = service.rebuild_monthly_snapshot(
            period_month=date(2026, 3, 1),
            auth_context=_build_auth_context(),
            request=_build_request("/api/v1/reporting/kpi-snapshots/rebuild", method="POST"),
        )

        assert {item.metric_key: item.metric_value for item in first.metrics} == {
            item.metric_key: item.metric_value for item in second.metrics
        }

        session.add(
            Vacancy(
                vacancy_id="99999999-9999-4999-8999-999999999999",
                title="Another role",
                description="Extra role",
                department="Engineering",
                status="open",
                created_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
                updated_at=datetime(2026, 3, 20, 9, 0, tzinfo=UTC),
            )
        )
        session.commit()

        third = service.rebuild_monthly_snapshot(
            period_month=date(2026, 3, 1),
            auth_context=_build_auth_context(),
            request=_build_request("/api/v1/reporting/kpi-snapshots/rebuild", method="POST"),
        )

        vacancy_metric = next(
            item for item in third.metrics if item.metric_key == "vacancies_created_count"
        )
        assert vacancy_metric.metric_value == 2

        snapshot_rows = (
            session.query(KpiSnapshot)
            .filter(KpiSnapshot.period_month == date(2026, 3, 1))
            .all()
        )
        assert len(snapshot_rows) == len(KPI_METRIC_KEYS)
