"""Automation action executor (TASK-08-02).

This module executes the deterministic action plan produced by
``AutomationEvaluator.evaluate(event)``.

Supported actions in this slice:
- ``notification.emit`` (in-app notifications only).
"""

from __future__ import annotations

import logging

from hrm_backend.automation.schemas.events import AutomationEvent
from hrm_backend.automation.schemas.plans import PlannedNotificationEmitAction
from hrm_backend.automation.services.evaluator import AutomationEvaluator
from hrm_backend.notifications.dao.notification_dao import NotificationDAO
from hrm_backend.notifications.schemas.notification import NotificationCreate

logger = logging.getLogger(__name__)


class AutomationActionExecutor:
    """Execute planned automation actions with fail-closed semantics.

    The executor is responsible for side effects, while the evaluator remains planning-only.
    """

    def __init__(
        self,
        *,
        evaluator: AutomationEvaluator,
        notification_dao: NotificationDAO,
    ) -> None:
        """Initialize executor dependencies.

        Args:
            evaluator: Deterministic planning evaluator (no side effects).
            notification_dao: Notification DAO used to persist ``notification.emit`` actions.
        """
        self._evaluator = evaluator
        self._notification_dao = notification_dao

    def plan(self, *, event: AutomationEvent) -> list[PlannedNotificationEmitAction]:
        """Build a deterministic action plan for one event.

        Args:
            event: Trigger event envelope + payload.

        Returns:
            list[PlannedNotificationEmitAction]: Deterministically ordered planned actions.
        """
        try:
            return self._evaluator.evaluate(event=event)
        except Exception:
            logger.exception(
                "Failed to plan automation actions for event '%s' (%s)",
                event.event_type,
                event.trigger_event_id,
            )
            return []

    def execute_plan(
        self,
        *,
        plan: list[PlannedNotificationEmitAction],
        commit: bool = True,
    ) -> int:
        """Execute a planned action list.

        Args:
            plan: Planned actions produced by the evaluator.
            commit: Whether to commit notification writes immediately.

        Returns:
            int: Number of newly created notification rows.

        Side effects:
            Writes to the ``notifications`` table.
        """
        if not plan:
            return 0

        payloads = [
            NotificationCreate(
                recipient_staff_id=item.recipient_staff_id,
                recipient_role=item.recipient_role,
                kind=item.notification_kind,
                source_type=item.source_type,
                source_id=item.source_id,
                dedupe_key=item.dedupe_key,
                title=item.title,
                body=item.body,
                payload=item.payload,
            )
            for item in plan
            if item.action == "notification.emit"
        ]
        if not payloads:
            return 0

        try:
            created = self._notification_dao.create_notifications(payloads=payloads, commit=commit)
        except Exception:
            try:
                self._notification_dao.rollback()
            except Exception:
                logger.exception(
                    "Failed to rollback session after automation execution failure '%s'",
                    plan[0].trigger_event_id,
                )
            logger.exception(
                "Failed to execute automation actions for trigger_event_id '%s'",
                plan[0].trigger_event_id,
            )
            return 0

        return len(created)

    def handle_event(self, *, event: AutomationEvent) -> int:
        """Plan and execute actions for one automation event (fail-closed).

        Args:
            event: Trigger event envelope + payload.

        Returns:
            int: Number of newly created notifications.
        """
        plan = self.plan(event=event)
        return self.execute_plan(plan=plan)
