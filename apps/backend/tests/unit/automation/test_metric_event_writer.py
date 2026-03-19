"""Unit tests for automation KPI metric event writing."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from hrm_backend.automation.models.metric_event import AutomationMetricEvent
from hrm_backend.automation.services.metric_event_writer import AutomationMetricEventWriter
from hrm_backend.core.models.base import Base


def test_metric_event_writer_is_idempotent_by_event_fingerprint() -> None:
    """Verify KPI metric event writer persists one row per unique trigger event."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
        writer = AutomationMetricEventWriter(session_factory=factory)
        event_time = datetime(2026, 3, 19, 10, 0, tzinfo=UTC)
        trigger_event_id = uuid4()

        writer.record_event(
            event_type="pipeline.transition_appended",
            trigger_event_id=trigger_event_id,
            event_time=event_time,
            outcome="success",
            total_hr_operations_count=1,
            automated_hr_operations_count=1,
            planned_action_count=1,
            succeeded_action_count=1,
            deduped_action_count=0,
            failed_action_count=0,
        )
        writer.record_event(
            event_type="pipeline.transition_appended",
            trigger_event_id=trigger_event_id,
            event_time=event_time,
            outcome="deduped",
            total_hr_operations_count=1,
            automated_hr_operations_count=1,
            planned_action_count=1,
            succeeded_action_count=0,
            deduped_action_count=1,
            failed_action_count=0,
        )

        with Session(engine) as session:
            rows = session.query(AutomationMetricEvent).all()
            assert len(rows) == 1
            assert rows[0].outcome == "success"
            assert rows[0].total_hr_operations_count == 1
            assert rows[0].automated_hr_operations_count == 1
            assert rows[0].planned_action_count == 1
            assert rows[0].succeeded_action_count == 1
            assert rows[0].deduped_action_count == 0
            assert rows[0].failed_action_count == 0
    finally:
        engine.dispose()
