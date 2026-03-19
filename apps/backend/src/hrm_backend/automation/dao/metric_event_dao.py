"""DAO helpers for durable automation KPI metric event persistence."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hrm_backend.automation.models.metric_event import AutomationMetricEvent
from hrm_backend.automation.utils.execution_logs import normalize_datetime_utc


class AutomationMetricEventDAO:
    """Persist and query automation KPI metric event rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session."""
        self._session = session

    def create_event(
        self,
        *,
        event_type: str,
        trigger_event_id: str,
        event_time: datetime,
        outcome: str,
        total_hr_operations_count: int,
        automated_hr_operations_count: int,
        planned_action_count: int,
        succeeded_action_count: int,
        deduped_action_count: int,
        failed_action_count: int,
        commit: bool = True,
    ) -> AutomationMetricEvent:
        """Insert one metric event row, returning the persisted entity.

        Duplicate event fingerprints are treated as idempotent and return the existing row.
        """
        existing = self.get_by_event_fingerprint(
            event_type=event_type,
            trigger_event_id=trigger_event_id,
        )
        if existing is not None:
            return existing

        entity = AutomationMetricEvent(
            event_type=event_type,
            trigger_event_id=trigger_event_id,
            event_time=normalize_datetime_utc(event_time),
            outcome=outcome,
            total_hr_operations_count=total_hr_operations_count,
            automated_hr_operations_count=automated_hr_operations_count,
            planned_action_count=planned_action_count,
            succeeded_action_count=succeeded_action_count,
            deduped_action_count=deduped_action_count,
            failed_action_count=failed_action_count,
        )
        self._session.add(entity)
        try:
            if commit:
                self._session.commit()
                self._session.refresh(entity)
                return entity
            self._session.flush()
            return entity
        except IntegrityError:
            self._session.rollback()
            existing = self.get_by_event_fingerprint(
                event_type=event_type,
                trigger_event_id=trigger_event_id,
            )
            if existing is not None:
                return existing
            raise

    def get_by_event_fingerprint(
        self,
        *,
        event_type: str,
        trigger_event_id: str,
    ) -> AutomationMetricEvent | None:
        """Return one metric event row by event fingerprint."""
        return (
            self._session.query(AutomationMetricEvent)
            .filter(
                AutomationMetricEvent.event_type == event_type,
                AutomationMetricEvent.trigger_event_id == trigger_event_id,
            )
            .one_or_none()
        )
