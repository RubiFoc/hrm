"""Unit tests for deterministic automation rule evaluation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import uuid4

from hrm_backend.automation.schemas.events import (
    OnboardingTaskAssignedEvent,
    OnboardingTaskAssignedPayload,
    PipelineTransitionAppendedEvent,
    PipelineTransitionAppendedPayload,
)
from hrm_backend.automation.services.evaluator import AutomationEvaluator


@dataclass(frozen=True)
class _RuleRow:
    rule_id: str
    conditions_json: dict[str, object] | None
    actions_json: list[dict[str, object]]
    priority: int = 0


@dataclass(frozen=True)
class _AccountRow:
    staff_id: str
    role: str
    login: str
    is_active: bool = True


class _RuleDAO:
    def __init__(self, rows: list[_RuleRow]) -> None:
        self._rows = rows

    def list_active_by_trigger(self, trigger: str) -> list[_RuleRow]:
        return list(self._rows)


class _StaffAccountDAO:
    def __init__(
        self,
        *,
        by_id: dict[str, _AccountRow],
        active_by_role: dict[str, list[_AccountRow]] | None = None,
    ) -> None:
        self._by_id = dict(by_id)
        self._active_by_role = dict(active_by_role or {})

    def get_by_id(self, staff_id: str) -> _AccountRow | None:
        return self._by_id.get(staff_id)

    def list_active_by_role(self, role: str) -> list[_AccountRow]:
        return list(self._active_by_role.get(role, []))


def test_pipeline_transition_plans_notification_for_hiring_manager() -> None:
    """Verify recruitment trigger uses hiring-manager recipient and safe payload fields."""
    rule_id = uuid4()
    transition_id = uuid4()
    vacancy_id = uuid4()
    candidate_id = uuid4()
    hiring_manager_staff_id = uuid4()
    event_time = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
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

    rules = [
        _RuleRow(
            rule_id=str(rule_id),
            conditions_json={"op": "eq", "field": "stage", "value": "screening"},
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "Pipeline moved to {{stage}}",
                    "body_template": "{{vacancy_title}} candidate {{candidate_id_short}}",
                    "payload_template": {
                        "vacancy_title": "{{vacancy_title}}",
                        "stage": "{{stage}}",
                        "candidate_id_short": "{{candidate_id_short}}",
                    },
                }
            ],
        )
    ]
    staff_accounts = {
        str(hiring_manager_staff_id): _AccountRow(
            staff_id=str(hiring_manager_staff_id),
            role="manager",
            login="manager-1",
            is_active=True,
        )
    }
    evaluator = AutomationEvaluator(
        rule_dao=_RuleDAO(rules),  # type: ignore[arg-type]
        staff_account_dao=_StaffAccountDAO(by_id=staff_accounts),  # type: ignore[arg-type]
    )

    plan = evaluator.evaluate(event=event)

    assert len(plan) == 1
    planned = plan[0]
    assert planned.rule_id == rule_id
    assert planned.trigger_event_id == transition_id
    assert planned.event_time == event_time
    assert planned.recipient_staff_id == hiring_manager_staff_id
    assert planned.recipient_role == "manager"
    assert planned.notification_kind == "pipeline_stage_changed"
    assert planned.dedupe_key == f"rule:{rule_id}:{transition_id}:{event_time.isoformat()}"
    assert planned.payload.vacancy_title == "QA Engineer"
    assert planned.payload.stage == "screening"
    assert planned.payload.candidate_id_short == "cafe1234"
    assert planned.payload.offer_status is None


def test_pipeline_transition_fail_closed_without_hiring_manager() -> None:
    """Verify recruitment triggers plan nothing when hiring manager is missing."""
    transition_id = uuid4()
    vacancy_id = uuid4()
    candidate_id = uuid4()
    event = PipelineTransitionAppendedEvent(
        event_type="pipeline.transition_appended",
        event_time=datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC),
        trigger_event_id=transition_id,
        payload=PipelineTransitionAppendedPayload(
            transition_id=transition_id,
            vacancy_id=vacancy_id,
            vacancy_title="QA Engineer",
            candidate_id=candidate_id,
            candidate_id_short="cafe1234",
            from_stage=None,
            to_stage="applied",
            stage="applied",
            hiring_manager_staff_id=None,
            changed_by_staff_id=str(uuid4()),
            changed_by_role="hr",
        ),
    )

    evaluator = AutomationEvaluator(
        rule_dao=_RuleDAO([]),  # type: ignore[arg-type]
        staff_account_dao=_StaffAccountDAO(by_id={}),  # type: ignore[arg-type]
    )

    assert evaluator.evaluate(event=event) == []


def test_invalid_condition_skips_rule_and_preserves_valid_rules() -> None:
    """Verify invalid condition trees are ignored without blocking other rules."""
    rule_id_invalid = uuid4()
    rule_id_valid = uuid4()
    transition_id = uuid4()
    vacancy_id = uuid4()
    candidate_id = uuid4()
    hiring_manager_staff_id = uuid4()
    event_time = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
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

    rules = [
        _RuleRow(
            rule_id=str(rule_id_invalid),
            conditions_json={"op": "eq", "value": "screening"},
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "Stage: {{stage}}",
                    "body_template": "{{vacancy_title}}",
                    "payload_template": {
                        "vacancy_title": "{{vacancy_title}}",
                        "stage": "{{stage}}",
                        "candidate_id_short": "{{candidate_id_short}}",
                    },
                }
            ],
        ),
        _RuleRow(
            rule_id=str(rule_id_valid),
            conditions_json=None,
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "Stage: {{stage}}",
                    "body_template": "{{vacancy_title}}",
                    "payload_template": {
                        "vacancy_title": "{{vacancy_title}}",
                        "stage": "{{stage}}",
                        "candidate_id_short": "{{candidate_id_short}}",
                    },
                }
            ],
        ),
    ]
    staff_accounts = {
        str(hiring_manager_staff_id): _AccountRow(
            staff_id=str(hiring_manager_staff_id),
            role="manager",
            login="manager-1",
            is_active=True,
        )
    }
    evaluator = AutomationEvaluator(
        rule_dao=_RuleDAO(rules),  # type: ignore[arg-type]
        staff_account_dao=_StaffAccountDAO(by_id=staff_accounts),  # type: ignore[arg-type]
    )

    plan = evaluator.evaluate(event=event)

    assert len(plan) == 1
    assert plan[0].rule_id == rule_id_valid


def test_rule_priority_orders_planned_actions() -> None:
    """Verify evaluator orders planned actions by rule priority desc, then rule id."""
    higher_priority_rule = uuid4()
    lower_priority_rule = uuid4()
    transition_id = uuid4()
    vacancy_id = uuid4()
    candidate_id = uuid4()
    hiring_manager_staff_id = uuid4()
    event_time = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
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

    rules = [
        _RuleRow(
            rule_id=str(lower_priority_rule),
            conditions_json=None,
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "Low priority {{stage}}",
                    "body_template": "{{vacancy_title}}",
                    "payload_template": {
                        "vacancy_title": "{{vacancy_title}}",
                        "stage": "{{stage}}",
                        "candidate_id_short": "{{candidate_id_short}}",
                    },
                }
            ],
            priority=1,
        ),
        _RuleRow(
            rule_id=str(higher_priority_rule),
            conditions_json=None,
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "High priority {{stage}}",
                    "body_template": "{{vacancy_title}}",
                    "payload_template": {
                        "vacancy_title": "{{vacancy_title}}",
                        "stage": "{{stage}}",
                        "candidate_id_short": "{{candidate_id_short}}",
                    },
                }
            ],
            priority=10,
        ),
    ]
    staff_accounts = {
        str(hiring_manager_staff_id): _AccountRow(
            staff_id=str(hiring_manager_staff_id),
            role="manager",
            login="manager-1",
            is_active=True,
        )
    }
    evaluator = AutomationEvaluator(
        rule_dao=_RuleDAO(rules),  # type: ignore[arg-type]
        staff_account_dao=_StaffAccountDAO(by_id=staff_accounts),  # type: ignore[arg-type]
    )

    plan = evaluator.evaluate(event=event)

    assert len(plan) == 2
    assert plan[0].rule_id == higher_priority_rule
    assert plan[1].rule_id == lower_priority_rule


def test_recruitment_payload_rejects_non_whitelisted_fields() -> None:
    """Verify evaluator rejects recruitment payload templates that include non-whitelisted keys."""
    rule_id = uuid4()
    transition_id = uuid4()
    vacancy_id = uuid4()
    candidate_id = uuid4()
    hiring_manager_staff_id = uuid4()
    event_time = datetime(2026, 3, 16, 10, 0, 0, tzinfo=UTC)
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

    rules = [
        _RuleRow(
            rule_id=str(rule_id),
            conditions_json=None,
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "pipeline_stage_changed",
                    "title_template": "Pipeline moved to {{stage}}",
                    "body_template": "{{vacancy_title}}",
                    "payload_template": {
                        "vacancy_id": str(vacancy_id),
                        "vacancy_title": "{{vacancy_title}}",
                    },
                }
            ],
        )
    ]
    staff_accounts = {
        str(hiring_manager_staff_id): _AccountRow(
            staff_id=str(hiring_manager_staff_id),
            role="manager",
            login="manager-1",
            is_active=True,
        )
    }
    evaluator = AutomationEvaluator(
        rule_dao=_RuleDAO(rules),  # type: ignore[arg-type]
        staff_account_dao=_StaffAccountDAO(by_id=staff_accounts),  # type: ignore[arg-type]
    )

    assert evaluator.evaluate(event=event) == []


def test_onboarding_task_assigned_resolves_role_and_direct_recipients() -> None:
    """Verify onboarding assignment trigger resolves role-based and direct recipients."""
    rule_id = uuid4()
    task_id = uuid4()
    onboarding_id = uuid4()
    employee_id = uuid4()
    direct_accountant_id = uuid4()
    manager_1_id = uuid4()
    manager_2_id = uuid4()
    event_time = datetime(2026, 3, 16, 12, 0, 0, tzinfo=UTC)
    event = OnboardingTaskAssignedEvent(
        event_type="onboarding.task_assigned",
        event_time=event_time,
        trigger_event_id=task_id,
        payload=OnboardingTaskAssignedPayload(
            task_id=task_id,
            onboarding_id=onboarding_id,
            employee_id=employee_id,
            task_title="Collect documents",
            assigned_role="manager",
            assigned_staff_id=direct_accountant_id,
            previous_assigned_role=None,
            previous_assigned_staff_id=None,
            due_at=None,
            employee_full_name="Employee X",
        ),
    )

    rules = [
        _RuleRow(
            rule_id=str(rule_id),
            conditions_json=None,
            actions_json=[
                {
                    "action": "notification.emit",
                    "notification_kind": "onboarding_task_assigned",
                    "title_template": "Task: {{task_title}}",
                    "body_template": "For {{employee_full_name}}",
                    "payload_template": {
                        "task_title": "{{task_title}}",
                        "employee_full_name": "{{employee_full_name}}",
                    },
                }
            ],
        )
    ]
    accounts_by_id = {
        str(direct_accountant_id): _AccountRow(
            staff_id=str(direct_accountant_id),
            role="accountant",
            login="accountant-1",
            is_active=True,
        ),
        str(manager_1_id): _AccountRow(
            staff_id=str(manager_1_id),
            role="manager",
            login="manager-1",
            is_active=True,
        ),
        str(manager_2_id): _AccountRow(
            staff_id=str(manager_2_id),
            role="manager",
            login="manager-2",
            is_active=True,
        ),
    }
    active_by_role = {
        "manager": [accounts_by_id[str(manager_1_id)], accounts_by_id[str(manager_2_id)]]
    }
    evaluator = AutomationEvaluator(
        rule_dao=_RuleDAO(rules),  # type: ignore[arg-type]
        staff_account_dao=_StaffAccountDAO(
            by_id=accounts_by_id,
            active_by_role=active_by_role,
        ),  # type: ignore[arg-type]
    )

    plan = evaluator.evaluate(event=event)

    recipient_ids = {planned.recipient_staff_id for planned in plan}
    assert recipient_ids == {direct_accountant_id, manager_1_id, manager_2_id}
    for planned in plan:
        assert planned.dedupe_key.startswith(f"rule:{rule_id}:{task_id}:")
        assert planned.payload.task_title == "Collect documents"
        assert planned.payload.employee_full_name == "Employee X"
