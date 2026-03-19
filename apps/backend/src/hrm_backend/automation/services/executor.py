"""Automation action executor (TASK-08-02).

This module executes the deterministic action plan produced by
``AutomationEvaluator.evaluate(event)``.

Supported actions in this slice:
- ``notification.emit`` (in-app notifications only).
"""

from __future__ import annotations

import logging
from uuid import uuid4

from sqlalchemy.orm import sessionmaker

from hrm_backend.automation.schemas.events import AutomationEvent
from hrm_backend.automation.schemas.plans import PlannedNotificationEmitAction
from hrm_backend.automation.services.evaluator import AutomationEvaluator
from hrm_backend.automation.services.execution_log_writer import (
    ActionExecutionResult,
    AutomationExecutionLogWriter,
)
from hrm_backend.automation.services.metric_event_writer import AutomationMetricEventWriter
from hrm_backend.automation.utils.execution_logs import sanitize_error_text
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
        session_factory = sessionmaker(
            bind=notification_dao.session.bind,
            autoflush=False,
            autocommit=False,
            future=True,
        )
        self._execution_log_writer = AutomationExecutionLogWriter(session_factory=session_factory)
        self._metric_event_writer = AutomationMetricEventWriter(session_factory=session_factory)

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

    def handle_event(self, *, event: AutomationEvent, correlation_id: str | None = None) -> int:
        """Plan and execute actions for one automation event (fail-closed).

        Args:
            event: Trigger event envelope + payload.
            correlation_id: Optional request correlation id (`X-Request-ID`) for traceability.

        Returns:
            int: Number of newly created notifications.
        """
        trace_id = uuid4().hex
        run_id = self._execution_log_writer.start_run(
            event_type=event.event_type,
            trigger_event_id=event.trigger_event_id,
            event_time=event.event_time,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )

        try:
            plan = self._evaluator.evaluate(event=event)
        except Exception as exc:
            logger.exception(
                "Failed to plan automation actions for event '%s' (%s, trace_id=%s)",
                event.event_type,
                event.trigger_event_id,
                trace_id,
            )
            if run_id is not None:
                self._execution_log_writer.finish_run(
                    run_id=run_id,
                    status="failed",
                    planned_action_count=0,
                    succeeded_action_count=0,
                    deduped_action_count=0,
                    failed_action_count=0,
                    error=exc,
                )
            self._record_metric_event(
                event=event,
                outcome="failed",
                planned_action_count=0,
                succeeded_action_count=0,
                deduped_action_count=0,
                failed_action_count=0,
            )
            return 0

        if not plan:
            if run_id is not None:
                self._execution_log_writer.finish_run(
                    run_id=run_id,
                    status="succeeded",
                    planned_action_count=0,
                    succeeded_action_count=0,
                    deduped_action_count=0,
                    failed_action_count=0,
                    error=None,
                )
            self._record_metric_event(
                event=event,
                outcome="no_rules",
                planned_action_count=0,
                succeeded_action_count=0,
                deduped_action_count=0,
                failed_action_count=0,
            )
            return 0

        created_count, results, exec_error = self._execute_notification_plan(
            plan=plan,
            commit=True,
            trace_id=trace_id,
        )

        succeeded = sum(1 for item in results if item.status == "succeeded")
        deduped = sum(1 for item in results if item.status == "deduped")
        failed = sum(1 for item in results if item.status == "failed")
        run_status = "failed" if failed else "succeeded"

        if run_id is not None:
            self._execution_log_writer.record_actions(run_id=run_id, results=results)
            self._execution_log_writer.finish_run(
                run_id=run_id,
                status=run_status,
                planned_action_count=len(results),
                succeeded_action_count=succeeded,
                deduped_action_count=deduped,
                failed_action_count=failed,
                error=exec_error if run_status == "failed" else None,
            )
        self._record_metric_event(
            event=event,
            outcome=self._resolve_metric_outcome(
                planned_action_count=len(results),
                succeeded_action_count=succeeded,
                deduped_action_count=deduped,
                failed_action_count=failed,
            ),
            planned_action_count=len(results),
            succeeded_action_count=succeeded,
            deduped_action_count=deduped,
            failed_action_count=failed,
        )

        return created_count

    def _execute_notification_plan(
        self,
        *,
        plan: list[PlannedNotificationEmitAction],
        commit: bool,
        trace_id: str,
    ) -> tuple[int, list[ActionExecutionResult], Exception | None]:
        """Execute a notification-only plan and return per-action results.

        Args:
            plan: Planned actions produced by the evaluator.
            commit: Whether to commit notification writes immediately.
            trace_id: Owning execution trace id.

        Returns:
            tuple[int, list[ActionExecutionResult], Exception | None]:
                - number of newly created notifications,
                - per-action execution results,
                - execution error when the plan failed.
        """
        payloads: list[NotificationCreate] = []
        planned_by_pair: dict[tuple[str, str], PlannedNotificationEmitAction] = {}
        ordered_pairs: list[tuple[str, str]] = []
        for item in plan:
            if item.action != "notification.emit":
                continue
            payloads.append(
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
            )
            pair = (str(item.recipient_staff_id), item.dedupe_key)
            planned_by_pair[pair] = item
            ordered_pairs.append(pair)

        if not payloads:
            return 0, [], None

        try:
            created = self._notification_dao.create_notifications(payloads=payloads, commit=commit)
        except Exception as exc:
            try:
                self._notification_dao.rollback()
            except Exception:
                logger.exception(
                    (
                        "Failed to rollback session after automation execution failure '%s' "
                        "(trace_id=%s)"
                    ),
                    plan[0].trigger_event_id,
                    trace_id,
                )
            logger.exception(
                "Failed to execute automation actions for trigger_event_id '%s' (trace_id=%s)",
                plan[0].trigger_event_id,
                trace_id,
            )
            error_kind = exc.__class__.__name__
            error_text = sanitize_error_text(str(exc))
            results = [
                ActionExecutionResult(
                    planned_action=planned_by_pair[pair],
                    status="failed",
                    attempt_count=1,
                    trace_id=trace_id,
                    error_kind=error_kind,
                    error_text=error_text,
                )
                for pair in ordered_pairs
            ]
            return 0, results, exc

        created_by_pair: dict[tuple[str, str], str] = {
            (row.recipient_staff_id, row.dedupe_key): row.notification_id for row in created
        }
        results: list[ActionExecutionResult] = []
        for pair in ordered_pairs:
            planned = planned_by_pair[pair]
            created_notification_id = created_by_pair.get(pair)
            if created_notification_id is None:
                results.append(
                    ActionExecutionResult(
                        planned_action=planned,
                        status="deduped",
                        attempt_count=1,
                        trace_id=trace_id,
                    )
                )
                continue
            results.append(
                ActionExecutionResult(
                    planned_action=planned,
                    status="succeeded",
                    attempt_count=1,
                    trace_id=trace_id,
                    result_notification_id=created_notification_id,
                )
            )

        return len(created), results, None

    def _record_metric_event(
        self,
        *,
        event: AutomationEvent,
        outcome: str,
        planned_action_count: int,
        succeeded_action_count: int,
        deduped_action_count: int,
        failed_action_count: int,
    ) -> None:
        """Persist an automation KPI metric event as a best-effort side effect."""
        automated_hr_operations_count = (
            1 if (succeeded_action_count > 0 or deduped_action_count > 0) else 0
        )
        self._metric_event_writer.record_event(
            event_type=event.event_type,
            trigger_event_id=event.trigger_event_id,
            event_time=event.event_time,
            outcome=outcome,
            total_hr_operations_count=1,
            automated_hr_operations_count=automated_hr_operations_count,
            planned_action_count=planned_action_count,
            succeeded_action_count=succeeded_action_count,
            deduped_action_count=deduped_action_count,
            failed_action_count=failed_action_count,
        )

    @staticmethod
    def _resolve_metric_outcome(
        *,
        planned_action_count: int,
        succeeded_action_count: int,
        deduped_action_count: int,
        failed_action_count: int,
    ) -> str:
        """Derive the persisted automation KPI outcome label for one handled event."""
        if planned_action_count == 0:
            return "no_rules"
        if succeeded_action_count > 0:
            return "success"
        if deduped_action_count > 0:
            return "deduped"
        if failed_action_count > 0:
            return "failed"
        return "failed"
