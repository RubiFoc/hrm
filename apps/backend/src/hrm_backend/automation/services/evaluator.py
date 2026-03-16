"""Deterministic automation rule evaluator (planning only in TASK-08-01)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from pydantic import TypeAdapter

from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.schemas.actions import NotificationEmitAction
from hrm_backend.automation.schemas.conditions import AutomationCondition
from hrm_backend.automation.schemas.events import (
    AutomationEvent,
    OfferStatusChangedEvent,
    OnboardingTaskAssignedEvent,
    PipelineTransitionAppendedEvent,
)
from hrm_backend.automation.schemas.plans import PlannedNotificationEmitAction
from hrm_backend.automation.utils.conditions import evaluate_condition
from hrm_backend.automation.utils.templates import (
    TemplateRenderError,
    render_json_template,
    render_template,
)
from hrm_backend.notifications.schemas.notification import NotificationPayload
from hrm_backend.notifications.utils.notifications import is_notifiable_recipient_role

_RECRUITMENT_TEMPLATE_FIELDS = frozenset(
    {
        "vacancy_title",
        "stage",
        "offer_status",
        "candidate_id_short",
    }
)

_RECRUITMENT_PAYLOAD_FIELDS = frozenset(
    {
        "vacancy_title",
        "stage",
        "offer_status",
        "candidate_id_short",
    }
)

_CONDITION_ADAPTER = TypeAdapter(AutomationCondition)


class AutomationEvaluator:
    """Evaluate active rules for a trigger event and return planned actions."""

    def __init__(
        self,
        *,
        rule_dao: AutomationRuleDAO,
        staff_account_dao: StaffAccountDAO,
    ) -> None:
        """Initialize evaluator dependencies."""
        self._rule_dao = rule_dao
        self._staff_account_dao = staff_account_dao

    def evaluate(self, *, event: AutomationEvent) -> list[PlannedNotificationEmitAction]:
        """Evaluate active rules and return a deterministically ordered action plan.

        The evaluator has no side effects. Failures are treated as fail-closed: no planned actions.
        """
        rules = self._rule_dao.list_active_by_trigger(event.event_type)

        plan: list[PlannedNotificationEmitAction] = []
        payload_for_conditions = event.payload.model_dump(mode="json")
        template_context = self._build_template_context(event=event)
        recipients = self._resolve_recipients(event=event)
        if not recipients:
            return []

        for rule in rules:
            conditions = _parse_conditions(rule.conditions_json)
            if conditions is not None and not evaluate_condition(
                conditions,
                payload_for_conditions,
            ):
                continue
            actions = _parse_notification_actions(rule.actions_json)
            for action in actions:
                planned = self._plan_notification_emit_actions(
                    rule_id=UUID(rule.rule_id),
                    action=action,
                    event=event,
                    template_context=template_context,
                    recipients=recipients,
                )
                plan.extend(planned)

        return plan

    def _resolve_recipients(self, *, event: AutomationEvent) -> list[tuple[UUID, str]]:
        """Resolve recipients implied by the trigger contract (fail-closed)."""
        if isinstance(event, (PipelineTransitionAppendedEvent, OfferStatusChangedEvent)):
            staff_id = event.payload.hiring_manager_staff_id
            if staff_id is None:
                return []
            account = self._staff_account_dao.get_by_id(str(staff_id))
            if (
                account is None
                or not account.is_active
                or not is_notifiable_recipient_role(account.role)
            ):
                return []
            return [(UUID(account.staff_id), account.role)]

        if isinstance(event, OnboardingTaskAssignedEvent):
            recipients: dict[str, tuple[UUID, str]] = {}
            if event.payload.assigned_role is not None and is_notifiable_recipient_role(
                event.payload.assigned_role
            ):
                for account in self._staff_account_dao.list_active_by_role(
                    event.payload.assigned_role
                ):
                    if is_notifiable_recipient_role(account.role):
                        recipients[account.staff_id] = (
                            UUID(account.staff_id),
                            account.role,
                        )

            if event.payload.assigned_staff_id is not None:
                account = self._staff_account_dao.get_by_id(str(event.payload.assigned_staff_id))
                if (
                    account is not None
                    and account.is_active
                    and is_notifiable_recipient_role(account.role)
                ):
                    recipients[account.staff_id] = (UUID(account.staff_id), account.role)

            return [recipients[key] for key in sorted(recipients.keys())]

        return []

    def _build_template_context(self, *, event: AutomationEvent) -> dict[str, object]:
        """Build a safe template context from event payload."""
        payload = event.payload.model_dump(mode="json")
        if isinstance(event, (PipelineTransitionAppendedEvent, OfferStatusChangedEvent)):
            return {key: payload.get(key) for key in sorted(_RECRUITMENT_TEMPLATE_FIELDS)}
        return payload

    def _plan_notification_emit_actions(
        self,
        *,
        rule_id: UUID,
        action: NotificationEmitAction,
        event: AutomationEvent,
        template_context: dict[str, object],
        recipients: list[tuple[UUID, str]],
    ) -> list[PlannedNotificationEmitAction]:
        """Plan deterministic in-app notification actions for each resolved recipient."""
        planned: list[PlannedNotificationEmitAction] = []
        for recipient_staff_id, recipient_role in sorted(
            recipients,
            key=lambda row: (row[1], row[0].hex),
        ):
            dedupe_key = _build_dedupe_key(
                rule_id=rule_id,
                trigger_event_id=event.trigger_event_id,
                event_time=_normalize_datetime(event.event_time),
            )
            try:
                title = render_template(action.title_template, template_context)
                body = render_template(action.body_template, template_context)
                rendered_payload = render_json_template(
                    action.payload_template,
                    template_context,
                )
            except TemplateRenderError:
                continue

            try:
                payload = NotificationPayload.model_validate(rendered_payload)
            except Exception:
                continue

            if isinstance(event, (PipelineTransitionAppendedEvent, OfferStatusChangedEvent)):
                if not _is_recruitment_payload_allowed(payload):
                    continue

            planned.append(
                PlannedNotificationEmitAction(
                    rule_id=rule_id,
                    trigger_event_id=event.trigger_event_id,
                    event_time=_normalize_datetime(event.event_time),
                    recipient_staff_id=recipient_staff_id,
                    recipient_role=recipient_role,  # type: ignore[arg-type]
                    notification_kind=action.notification_kind,
                    source_type=_resolve_source_type(event),
                    source_id=event.trigger_event_id,
                    dedupe_key=dedupe_key,
                    title=title,
                    body=body,
                    payload=payload,
                )
            )

        return planned


def _normalize_datetime(value: datetime) -> datetime:
    """Normalize datetimes to timezone-aware UTC."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _build_dedupe_key(*, rule_id: UUID, trigger_event_id: UUID, event_time: datetime) -> str:
    """Build idempotency hook key for later executor."""
    suffix = _normalize_datetime(event_time).isoformat()
    return f"rule:{rule_id}:{trigger_event_id}:{suffix}"


def _resolve_source_type(event: AutomationEvent) -> str:
    """Map trigger event to notification `source_type`."""
    if isinstance(event, PipelineTransitionAppendedEvent):
        return "pipeline_transition"
    if isinstance(event, OfferStatusChangedEvent):
        return "offer"
    if isinstance(event, OnboardingTaskAssignedEvent):
        return "onboarding_task"
    return "automation"


def _parse_conditions(raw: dict[str, object] | None) -> AutomationCondition | None:
    """Parse stored condition JSON into typed schema (fail-closed)."""
    if raw is None:
        return None
    try:
        return _CONDITION_ADAPTER.validate_python(raw)
    except Exception:
        return None


def _parse_notification_actions(raw: list[dict[str, object]]) -> list[NotificationEmitAction]:
    """Parse stored action JSON list into typed actions (fail-closed)."""
    actions: list[NotificationEmitAction] = []
    for item in raw:
        try:
            action = NotificationEmitAction.model_validate(item)
        except Exception:
            continue
        actions.append(action)
    return actions


def _is_recruitment_payload_allowed(payload: NotificationPayload) -> bool:
    """Enforce PII-safe notification payload for recruitment triggers."""
    payload_json = payload.model_dump(mode="python")
    for key, value in payload_json.items():
        if value is None:
            continue
        if key not in _RECRUITMENT_PAYLOAD_FIELDS:
            return False
    return True
