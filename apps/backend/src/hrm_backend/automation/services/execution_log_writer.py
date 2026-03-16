"""Best-effort writer for durable automation execution logs (TASK-08-03)."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from hrm_backend.automation.dao.execution_log_dao import AutomationExecutionLogDAO
from hrm_backend.automation.models.action_execution import AutomationActionExecution
from hrm_backend.automation.schemas.plans import PlannedNotificationEmitAction
from hrm_backend.automation.utils.execution_logs import normalize_datetime_utc, sanitize_error_text

logger = logging.getLogger(__name__)

ActionExecutionStatus = Literal["succeeded", "deduped", "failed"]
RunExecutionStatus = Literal["running", "succeeded", "failed"]


@dataclass(frozen=True)
class ActionExecutionResult:
    """One action execution result captured by the automation executor.

    Attributes:
        planned_action: Original planned action (used for identifiers only).
        status: Terminal action status.
        attempt_count: Attempt count for the action.
        trace_id: Owning run trace id.
        result_notification_id: Created notification id when action succeeded.
        error_kind: Sanitized error kind when action failed.
        error_text: Sanitized error text when action failed.
    """

    planned_action: PlannedNotificationEmitAction
    status: ActionExecutionStatus
    attempt_count: int
    trace_id: str
    result_notification_id: str | None = None
    error_kind: str | None = None
    error_text: str | None = None


class AutomationExecutionLogWriter:
    """Persist durable automation execution logs in isolated transactions."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        """Initialize writer.

        Args:
            session_factory: Session factory bound to the application database engine.
        """
        self._session_factory = session_factory

    def start_run(
        self,
        *,
        event_type: str,
        trigger_event_id: UUID,
        event_time: datetime,
        correlation_id: str | None,
        trace_id: str,
    ) -> str | None:
        """Create execution run row and return `run_id`.

        Returns:
            str | None: Run identifier or `None` when logging is unavailable.
        """
        try:
            with self._session_factory() as session:
                dao = AutomationExecutionLogDAO(session=session)
                entity = dao.create_run(
                    event_type=event_type,
                    trigger_event_id=str(trigger_event_id),
                    event_time=normalize_datetime_utc(event_time),
                    correlation_id=correlation_id,
                    trace_id=trace_id,
                    status="running",
                )
                return entity.run_id
        except Exception:
            logger.exception(
                "Failed to create automation execution run log for event '%s' (%s, trace_id=%s)",
                event_type,
                trigger_event_id,
                trace_id,
            )
            return None

    def finish_run(
        self,
        *,
        run_id: str,
        status: RunExecutionStatus,
        planned_action_count: int,
        succeeded_action_count: int,
        deduped_action_count: int,
        failed_action_count: int,
        error: Exception | None = None,
    ) -> None:
        """Mark execution run row as terminal."""
        error_kind = None
        error_text = None
        if error is not None:
            error_kind = error.__class__.__name__
            error_text = sanitize_error_text(str(error))

        try:
            with self._session_factory() as session:
                dao = AutomationExecutionLogDAO(session=session)
                dao.update_run(
                    run_id=run_id,
                    status=status,
                    planned_action_count=planned_action_count,
                    succeeded_action_count=succeeded_action_count,
                    deduped_action_count=deduped_action_count,
                    failed_action_count=failed_action_count,
                    error_kind=error_kind,
                    error_text=error_text,
                )
        except Exception:
            logger.exception(
                "Failed to update automation execution run '%s' (status=%s)",
                run_id,
                status,
            )

    def record_actions(self, *, run_id: str, results: list[ActionExecutionResult]) -> None:
        """Insert action execution attempt rows for one run."""
        if not results:
            return

        entities: list[AutomationActionExecution] = []
        now = datetime.now(UTC)
        for item in results:
            planned = item.planned_action
            entities.append(
                AutomationActionExecution(
                    run_id=run_id,
                    action=planned.action,
                    rule_id=str(planned.rule_id),
                    recipient_staff_id=str(planned.recipient_staff_id),
                    recipient_role=str(planned.recipient_role),
                    source_type=planned.source_type,
                    source_id=str(planned.source_id),
                    dedupe_key=planned.dedupe_key,
                    status=item.status,
                    attempt_count=item.attempt_count,
                    trace_id=item.trace_id,
                    result_notification_id=item.result_notification_id,
                    error_kind=item.error_kind,
                    error_text=item.error_text,
                    created_at=now,
                    updated_at=now,
                )
            )

        try:
            with self._session_factory() as session:
                dao = AutomationExecutionLogDAO(session=session)
                dao.create_action_executions(run_id=run_id, items=entities)
        except Exception:
            logger.exception(
                "Failed to persist automation action execution logs for run '%s'",
                run_id,
            )
