"""DAO helpers for durable automation execution log persistence.

The execution log tables are append-only from the perspective of external callers:
`automation_execution_runs` rows are created and then updated to a terminal state, while
`automation_action_executions` rows are inserted per action attempt.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hrm_backend.automation.models.action_execution import AutomationActionExecution
from hrm_backend.automation.models.execution_run import AutomationExecutionRun


class AutomationExecutionLogDAO:
    """Persist and query automation execution runs and action attempts."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: SQLAlchemy session used exclusively for execution logging.
        """
        self._session = session

    def create_run(
        self,
        *,
        event_type: str,
        trigger_event_id: str,
        event_time: datetime,
        correlation_id: str | None,
        trace_id: str,
        status: str = "running",
        commit: bool = True,
    ) -> AutomationExecutionRun:
        """Insert one execution run row."""
        entity = AutomationExecutionRun(
            event_type=event_type,
            trigger_event_id=trigger_event_id,
            event_time=event_time,
            correlation_id=correlation_id,
            trace_id=trace_id,
            status=status,
            planned_action_count=0,
            succeeded_action_count=0,
            deduped_action_count=0,
            failed_action_count=0,
            started_at=datetime.now(UTC),
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def update_run(
        self,
        *,
        run_id: str,
        status: str,
        planned_action_count: int,
        succeeded_action_count: int,
        deduped_action_count: int,
        failed_action_count: int,
        error_kind: str | None,
        error_text: str | None,
        commit: bool = True,
    ) -> AutomationExecutionRun | None:
        """Update one run row to a new (typically terminal) state."""
        entity = self._session.get(AutomationExecutionRun, run_id)
        if entity is None:
            return None

        now = datetime.now(UTC)
        entity.status = status
        entity.planned_action_count = planned_action_count
        entity.succeeded_action_count = succeeded_action_count
        entity.deduped_action_count = deduped_action_count
        entity.failed_action_count = failed_action_count
        entity.error_kind = error_kind
        entity.error_text = error_text
        if status in {"succeeded", "failed"}:
            entity.finished_at = now
        entity.updated_at = now
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def create_action_executions(
        self,
        *,
        run_id: str,
        items: Sequence[AutomationActionExecution],
        commit: bool = True,
    ) -> list[AutomationActionExecution]:
        """Insert action execution rows linked to one run."""
        if not items:
            return []

        for entity in items:
            entity.run_id = run_id
            self._session.add(entity)

        if commit:
            self._session.commit()
            for entity in items:
                self._session.refresh(entity)
            return list(items)

        self._session.flush()
        return list(items)

    def get_run_by_id(self, *, run_id: str) -> AutomationExecutionRun | None:
        """Fetch one execution run by identifier."""
        return self._session.get(AutomationExecutionRun, run_id)

    def list_runs(
        self,
        *,
        event_type: str | None,
        trigger_event_id: str | None,
        status: str | None,
        correlation_id: str | None,
        trace_id: str | None,
        limit: int,
        offset: int,
    ) -> list[AutomationExecutionRun]:
        """List execution runs ordered newest-first with optional filters."""
        query = self._session.query(AutomationExecutionRun)
        if event_type is not None:
            query = query.filter(AutomationExecutionRun.event_type == event_type)
        if trigger_event_id is not None:
            query = query.filter(AutomationExecutionRun.trigger_event_id == trigger_event_id)
        if status is not None:
            query = query.filter(AutomationExecutionRun.status == status)
        if correlation_id is not None:
            query = query.filter(AutomationExecutionRun.correlation_id == correlation_id)
        if trace_id is not None:
            query = query.filter(AutomationExecutionRun.trace_id == trace_id)
        return list(
            query.order_by(
                AutomationExecutionRun.started_at.desc(),
                AutomationExecutionRun.run_id.desc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_runs(
        self,
        *,
        event_type: str | None,
        trigger_event_id: str | None,
        status: str | None,
        correlation_id: str | None,
        trace_id: str | None,
    ) -> int:
        """Count execution runs matching the provided filters."""
        query = self._session.query(AutomationExecutionRun.run_id)
        if event_type is not None:
            query = query.filter(AutomationExecutionRun.event_type == event_type)
        if trigger_event_id is not None:
            query = query.filter(AutomationExecutionRun.trigger_event_id == trigger_event_id)
        if status is not None:
            query = query.filter(AutomationExecutionRun.status == status)
        if correlation_id is not None:
            query = query.filter(AutomationExecutionRun.correlation_id == correlation_id)
        if trace_id is not None:
            query = query.filter(AutomationExecutionRun.trace_id == trace_id)
        return query.count()

    def get_action_by_id(self, *, action_execution_id: str) -> AutomationActionExecution | None:
        """Fetch one action execution row by identifier."""
        return self._session.get(AutomationActionExecution, action_execution_id)

    def list_actions_by_run_id(
        self,
        *,
        run_id: str,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[AutomationActionExecution]:
        """List action execution rows for one run in deterministic order."""
        query = self._session.query(AutomationActionExecution).filter(
            AutomationActionExecution.run_id == run_id
        )
        if status is not None:
            query = query.filter(AutomationActionExecution.status == status)
        return list(
            query.order_by(
                AutomationActionExecution.created_at.asc(),
                AutomationActionExecution.action_execution_id.asc(),
            )
            .offset(offset)
            .limit(limit)
            .all()
        )

    def count_actions_by_run_id(self, *, run_id: str, status: str | None) -> int:
        """Count action execution rows for one run."""
        query = self._session.query(AutomationActionExecution.action_execution_id).filter(
            AutomationActionExecution.run_id == run_id
        )
        if status is not None:
            query = query.filter(AutomationActionExecution.status == status)
        return query.count()
