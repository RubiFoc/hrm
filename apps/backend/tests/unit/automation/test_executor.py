"""Unit tests for automation action executor (TASK-08-02)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.models.action_execution import AutomationActionExecution
from hrm_backend.automation.models.execution_run import AutomationExecutionRun
from hrm_backend.automation.models.metric_event import AutomationMetricEvent
from hrm_backend.automation.schemas.events import (
    PipelineTransitionAppendedEvent,
    PipelineTransitionAppendedPayload,
)
from hrm_backend.automation.services.evaluator import AutomationEvaluator
from hrm_backend.automation.services.executor import AutomationActionExecutor
from hrm_backend.core.models.base import Base
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.notifications.models.notification import Notification


def test_executor_creates_notification_and_is_idempotent() -> None:
    """Verify executor writes in-app notifications and skips duplicates by dedupe_key."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            hiring_manager_staff_id = uuid4()
            session.add(
                StaffAccount(
                    staff_id=str(hiring_manager_staff_id),
                    login="manager-1",
                    email="manager@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                )
            )
            session.commit()

            rule_dao = AutomationRuleDAO(session=session)
            rule = rule_dao.create_rule(
                name="Notify hiring manager on screening",
                trigger="pipeline.transition_appended",
                conditions_json={"op": "eq", "field": "stage", "value": "screening"},
                actions_json=[
                    {
                        "action": "notification.emit",
                        "notification_kind": "pipeline_stage_changed",
                        "title_template": "Stage: {{stage}}",
                        "body_template": "{{vacancy_title}} / {{candidate_id_short}}",
                        "payload_template": {
                            "vacancy_title": "{{vacancy_title}}",
                            "stage": "{{stage}}",
                            "candidate_id_short": "{{candidate_id_short}}",
                        },
                    }
                ],
                priority=10,
                created_by_staff_id=str(hiring_manager_staff_id),
            )
            rule = rule_dao.set_active(
                entity=rule,
                is_active=True,
                updated_by_staff_id=str(hiring_manager_staff_id),
            )

            evaluator = AutomationEvaluator(
                rule_dao=rule_dao,
                staff_account_dao=StaffAccountDAO(session=session),
            )
            executor = AutomationActionExecutor(
                evaluator=evaluator,
                notification_dao=NotificationDAO(session=session),
            )

            transition_id = uuid4()
            vacancy_id = uuid4()
            candidate_id = uuid4()
            event_time = datetime(2026, 3, 16, 10, 0, tzinfo=UTC)
            event = PipelineTransitionAppendedEvent(
                event_type="pipeline.transition_appended",
                event_time=event_time,
                trigger_event_id=transition_id,
                payload=PipelineTransitionAppendedPayload(
                    transition_id=transition_id,
                    vacancy_id=vacancy_id,
                    vacancy_title="QA Engineer",
                    candidate_id=candidate_id,
                    candidate_id_short="cafe1234",
                    from_stage="applied",
                    to_stage="screening",
                    stage="screening",
                    hiring_manager_staff_id=hiring_manager_staff_id,
                    changed_by_staff_id=str(uuid4()),
                    changed_by_role="hr",
                ),
            )

            created = executor.handle_event(event=event, correlation_id="req-1")
            assert created == 1

            rows = session.query(Notification).all()
            assert len(rows) == 1
            assert UUID(rows[0].recipient_staff_id) == hiring_manager_staff_id
            assert rows[0].kind == "pipeline_stage_changed"
            assert rows[0].dedupe_key == (
                f"rule:{UUID(rule.rule_id)}:{transition_id}:{event_time.isoformat()}"
            )

            created_again = executor.handle_event(event=event, correlation_id="req-2")
            assert created_again == 0
            assert session.query(Notification).count() == 1

            runs = (
                session.query(AutomationExecutionRun)
                .order_by(AutomationExecutionRun.started_at.asc())
                .all()
            )
            assert len(runs) == 2
            assert runs[0].status == "succeeded"
            assert runs[0].planned_action_count == 1
            assert runs[0].succeeded_action_count == 1
            assert runs[0].deduped_action_count == 0
            assert runs[0].failed_action_count == 0
            assert runs[0].correlation_id == "req-1"

            assert runs[1].status == "succeeded"
            assert runs[1].planned_action_count == 1
            assert runs[1].succeeded_action_count == 0
            assert runs[1].deduped_action_count == 1
            assert runs[1].failed_action_count == 0
            assert runs[1].correlation_id == "req-2"

            action_rows = (
                session.query(AutomationActionExecution)
                .order_by(AutomationActionExecution.created_at.asc())
                .all()
            )
            assert len(action_rows) == 2
            assert action_rows[0].status == "succeeded"
            assert action_rows[0].attempt_count == 1
            assert action_rows[0].result_notification_id is not None
            assert action_rows[1].status == "deduped"
            assert action_rows[1].attempt_count == 1
            assert action_rows[1].result_notification_id is None

            metric_rows = (
                session.query(AutomationMetricEvent)
                .order_by(AutomationMetricEvent.created_at.asc())
                .all()
            )
            assert len(metric_rows) == 1
            assert metric_rows[0].event_type == "pipeline.transition_appended"
            assert metric_rows[0].outcome == "success"
            assert metric_rows[0].total_hr_operations_count == 1
            assert metric_rows[0].automated_hr_operations_count == 1
            assert metric_rows[0].planned_action_count == 1
            assert metric_rows[0].succeeded_action_count == 1
            assert metric_rows[0].deduped_action_count == 0
            assert metric_rows[0].failed_action_count == 0
    finally:
        engine.dispose()


def test_executor_records_failed_action_and_sanitizes_error_text() -> None:
    """Verify executor captures failed status and redacts basic PII from error strings."""
    engine = create_engine("sqlite+pysqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)

    class _FailingNotificationDAO:
        def __init__(self, session: Session) -> None:
            self._session = session

        @property
        def session(self) -> Session:
            return self._session

        def create_notifications(self, *, payloads, commit: bool = True):  # noqa: ANN001
            raise RuntimeError("Email test@example.com phone +1234567890")

        def rollback(self) -> None:
            self._session.rollback()

    try:
        with Session(engine) as session:
            hiring_manager_staff_id = uuid4()
            session.add(
                StaffAccount(
                    staff_id=str(hiring_manager_staff_id),
                    login="manager-1",
                    email="manager@example.com",
                    password_hash="hash",
                    role="manager",
                    is_active=True,
                )
            )
            session.commit()

            rule_dao = AutomationRuleDAO(session=session)
            rule = rule_dao.create_rule(
                name="Notify hiring manager on screening",
                trigger="pipeline.transition_appended",
                conditions_json={"op": "eq", "field": "stage", "value": "screening"},
                actions_json=[
                    {
                        "action": "notification.emit",
                        "notification_kind": "pipeline_stage_changed",
                        "title_template": "Stage: {{stage}}",
                        "body_template": "{{vacancy_title}} / {{candidate_id_short}}",
                        "payload_template": {
                            "vacancy_title": "{{vacancy_title}}",
                            "stage": "{{stage}}",
                            "candidate_id_short": "{{candidate_id_short}}",
                        },
                    }
                ],
                priority=10,
                created_by_staff_id=str(hiring_manager_staff_id),
            )
            rule_dao.set_active(
                entity=rule,
                is_active=True,
                updated_by_staff_id=str(hiring_manager_staff_id),
            )

            evaluator = AutomationEvaluator(
                rule_dao=rule_dao,
                staff_account_dao=StaffAccountDAO(session=session),
            )
            executor = AutomationActionExecutor(
                evaluator=evaluator,
                notification_dao=_FailingNotificationDAO(session=session),  # type: ignore[arg-type]
            )

            transition_id = uuid4()
            vacancy_id = uuid4()
            candidate_id = uuid4()
            event_time = datetime(2026, 3, 16, 10, 0, tzinfo=UTC)
            event = PipelineTransitionAppendedEvent(
                event_type="pipeline.transition_appended",
                event_time=event_time,
                trigger_event_id=transition_id,
                payload=PipelineTransitionAppendedPayload(
                    transition_id=transition_id,
                    vacancy_id=vacancy_id,
                    vacancy_title="QA Engineer",
                    candidate_id=candidate_id,
                    candidate_id_short="cafe1234",
                    from_stage="applied",
                    to_stage="screening",
                    stage="screening",
                    hiring_manager_staff_id=hiring_manager_staff_id,
                    changed_by_staff_id=str(uuid4()),
                    changed_by_role="hr",
                ),
            )

            created = executor.handle_event(event=event, correlation_id="req-3")
            assert created == 0

            run = session.query(AutomationExecutionRun).first()
            assert run is not None
            assert run.status == "failed"
            assert run.failed_action_count == 1
            assert run.error_text is not None
            assert "<redacted_email>" in run.error_text
            assert "<redacted_phone>" in run.error_text

            action = session.query(AutomationActionExecution).first()
            assert action is not None
            assert action.status == "failed"
            assert action.error_text is not None
            assert "<redacted_email>" in action.error_text
            assert "<redacted_phone>" in action.error_text

            metric_rows = session.query(AutomationMetricEvent).all()
            assert len(metric_rows) == 1
            assert metric_rows[0].outcome == "failed"
            assert metric_rows[0].total_hr_operations_count == 1
            assert metric_rows[0].automated_hr_operations_count == 0
            assert metric_rows[0].planned_action_count == 1
            assert metric_rows[0].succeeded_action_count == 0
            assert metric_rows[0].deduped_action_count == 0
            assert metric_rows[0].failed_action_count == 1
    finally:
        engine.dispose()
