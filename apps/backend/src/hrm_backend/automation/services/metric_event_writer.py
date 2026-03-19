"""Best-effort writer for durable automation KPI metric events."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal
from uuid import UUID

from sqlalchemy.orm import Session, sessionmaker

from hrm_backend.automation.dao.metric_event_dao import AutomationMetricEventDAO
from hrm_backend.automation.utils.execution_logs import normalize_datetime_utc

logger = logging.getLogger(__name__)

AutomationMetricEventOutcome = Literal["no_rules", "success", "deduped", "failed"]


class AutomationMetricEventWriter:
    """Persist automation KPI metric events in isolated transactions."""

    def __init__(self, *, session_factory: sessionmaker[Session]) -> None:
        """Initialize writer.

        Args:
            session_factory: Session factory bound to the application database engine.
        """
        self._session_factory = session_factory

    def record_event(
        self,
        *,
        event_type: str,
        trigger_event_id: UUID,
        event_time: datetime,
        outcome: AutomationMetricEventOutcome,
        total_hr_operations_count: int,
        automated_hr_operations_count: int,
        planned_action_count: int,
        succeeded_action_count: int,
        deduped_action_count: int,
        failed_action_count: int,
    ) -> None:
        """Persist one metric event row.

        The writer is best-effort: failures are logged and do not escape to callers.
        """
        try:
            with self._session_factory() as session:
                dao = AutomationMetricEventDAO(session=session)
                dao.create_event(
                    event_type=event_type,
                    trigger_event_id=str(trigger_event_id),
                    event_time=normalize_datetime_utc(event_time),
                    outcome=outcome,
                    total_hr_operations_count=total_hr_operations_count,
                    automated_hr_operations_count=automated_hr_operations_count,
                    planned_action_count=planned_action_count,
                    succeeded_action_count=succeeded_action_count,
                    deduped_action_count=deduped_action_count,
                    failed_action_count=failed_action_count,
                )
        except Exception:
            logger.exception(
                "Failed to persist automation KPI metric event for trigger '%s' (%s)",
                event_type,
                trigger_event_id,
            )
