"""Unit tests for automation action executor (TASK-08-02)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.models.staff_account import StaffAccount
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
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

            created = executor.handle_event(event=event)
            assert created == 1

            rows = session.query(Notification).all()
            assert len(rows) == 1
            assert UUID(rows[0].recipient_staff_id) == hiring_manager_staff_id
            assert rows[0].kind == "pipeline_stage_changed"
            assert rows[0].dedupe_key == (
                f"rule:{UUID(rule.rule_id)}:{transition_id}:{event_time.isoformat()}"
            )

            created_again = executor.handle_event(event=event)
            assert created_again == 0
            assert session.query(Notification).count() == 1
    finally:
        engine.dispose()

