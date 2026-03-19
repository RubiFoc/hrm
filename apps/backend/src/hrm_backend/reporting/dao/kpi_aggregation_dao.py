"""Read-only aggregation queries for KPI snapshot generation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.automation.models.metric_event import AutomationMetricEvent
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun, OnboardingTask
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy


class KpiAggregationDAO:
    """Aggregate KPI counts from durable transactional tables."""

    def __init__(self, session: Session) -> None:
        """Initialize aggregation DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def count_vacancies_created(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count vacancies created inside the provided window."""
        return _count(
            self._session.query(func.count(Vacancy.vacancy_id))
            .filter(Vacancy.created_at >= start_at, Vacancy.created_at < end_at)
            .scalar()
        )

    def count_candidates_applied(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count candidate applications based on pipeline transitions to `applied`."""
        return _count(
            self._session.query(func.count(PipelineTransition.transition_id))
            .filter(
                PipelineTransition.to_stage == "applied",
                PipelineTransition.transitioned_at >= start_at,
                PipelineTransition.transitioned_at < end_at,
            )
            .scalar()
        )

    def count_interviews_scheduled(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count interviews scheduled (created) inside the provided window."""
        return _count(
            self._session.query(func.count(Interview.interview_id))
            .filter(Interview.created_at >= start_at, Interview.created_at < end_at)
            .scalar()
        )

    def count_offers_sent(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count offers sent inside the provided window."""
        return _count(
            self._session.query(func.count(Offer.offer_id))
            .filter(
                Offer.sent_at.is_not(None),
                Offer.sent_at >= start_at,
                Offer.sent_at < end_at,
            )
            .scalar()
        )

    def count_offers_accepted(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count offers accepted inside the provided window."""
        return _count(
            self._session.query(func.count(Offer.offer_id))
            .filter(
                Offer.status == "accepted",
                Offer.decision_at.is_not(None),
                Offer.decision_at >= start_at,
                Offer.decision_at < end_at,
            )
            .scalar()
        )

    def count_hires(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count hires based on durable hire conversion rows."""
        return _count(
            self._session.query(func.count(HireConversion.conversion_id))
            .filter(
                HireConversion.converted_at >= start_at,
                HireConversion.converted_at < end_at,
            )
            .scalar()
        )

    def count_onboarding_started(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count onboarding runs started inside the provided window."""
        return _count(
            self._session.query(func.count(OnboardingRun.onboarding_id))
            .filter(
                OnboardingRun.started_at >= start_at,
                OnboardingRun.started_at < end_at,
            )
            .scalar()
        )

    def count_onboarding_tasks_completed(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count onboarding tasks completed inside the provided window."""
        return _count(
            self._session.query(func.count(OnboardingTask.task_id))
            .filter(
                OnboardingTask.status == "completed",
                OnboardingTask.completed_at.is_not(None),
                OnboardingTask.completed_at >= start_at,
                OnboardingTask.completed_at < end_at,
            )
            .scalar()
        )

    def count_total_hr_operations(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count total HR operations from durable automation metric events."""
        return _count(
            self._session.query(
                func.coalesce(func.sum(AutomationMetricEvent.total_hr_operations_count), 0)
            )
            .filter(
                AutomationMetricEvent.event_time >= start_at,
                AutomationMetricEvent.event_time < end_at,
            )
            .scalar()
        )

    def count_automated_hr_operations(self, *, start_at: datetime, end_at: datetime) -> int:
        """Count automated HR operations from durable automation metric events."""
        return _count(
            self._session.query(
                func.coalesce(func.sum(AutomationMetricEvent.automated_hr_operations_count), 0)
            )
            .filter(
                AutomationMetricEvent.event_time >= start_at,
                AutomationMetricEvent.event_time < end_at,
            )
            .scalar()
        )


def _count(value: int | None) -> int:
    """Normalize nullable SQL count results into a stable integer.

    Args:
        value: Raw count returned from SQLAlchemy.

    Returns:
        int: Normalized non-null count.
    """
    return int(value or 0)
