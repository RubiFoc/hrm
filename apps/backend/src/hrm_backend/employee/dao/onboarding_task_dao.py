"""Data-access helpers for materialized onboarding task persistence."""

from __future__ import annotations

from collections.abc import Sequence

from sqlalchemy.orm import Session

from hrm_backend.employee.models.onboarding import OnboardingTask
from hrm_backend.employee.schemas.onboarding import OnboardingTaskCreate


class OnboardingTaskDAO:
    """Persist and query materialized onboarding tasks."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: Active request or job session.
        """
        self._session = session

    def list_by_onboarding_id(self, onboarding_id: str) -> list[OnboardingTask]:
        """Load onboarding tasks for one onboarding run in deterministic order."""
        return list(
            self._session.query(OnboardingTask)
            .filter(OnboardingTask.onboarding_id == onboarding_id)
            .order_by(
                OnboardingTask.sort_order.asc(),
                OnboardingTask.task_id.asc(),
            )
            .all()
        )

    def list_by_onboarding_ids(self, onboarding_ids: Sequence[str]) -> list[OnboardingTask]:
        """Load onboarding tasks for multiple onboarding runs in deterministic order."""
        if not onboarding_ids:
            return []
        return list(
            self._session.query(OnboardingTask)
            .filter(OnboardingTask.onboarding_id.in_(list(onboarding_ids)))
            .order_by(
                OnboardingTask.onboarding_id.asc(),
                OnboardingTask.sort_order.asc(),
                OnboardingTask.task_id.asc(),
            )
            .all()
        )

    def get_by_onboarding_and_id(
        self,
        *,
        onboarding_id: str,
        task_id: str,
    ) -> OnboardingTask | None:
        """Load one onboarding task scoped to its onboarding run."""
        return (
            self._session.query(OnboardingTask)
            .filter(
                OnboardingTask.onboarding_id == onboarding_id,
                OnboardingTask.task_id == task_id,
            )
            .first()
        )

    def create_tasks(
        self,
        *,
        payloads: Sequence[OnboardingTaskCreate],
        commit: bool = True,
    ) -> list[OnboardingTask]:
        """Insert one or more onboarding task rows."""
        entities = [
            OnboardingTask(
                onboarding_id=str(payload.onboarding_id),
                template_id=str(payload.template_id),
                template_item_id=str(payload.template_item_id),
                code=payload.code,
                title=payload.title,
                description=payload.description,
                sort_order=payload.sort_order,
                is_required=payload.is_required,
                status=payload.status,
                assigned_role=payload.assigned_role,
                assigned_staff_id=str(payload.assigned_staff_id)
                if payload.assigned_staff_id is not None
                else None,
                due_at=payload.due_at,
            )
            for payload in payloads
        ]
        for entity in entities:
            self._session.add(entity)

        if commit:
            self._session.commit()
            for entity in entities:
                self._session.refresh(entity)
            return entities

        self._session.flush()
        return entities

    def update_task(
        self,
        *,
        entity: OnboardingTask,
        commit: bool = True,
    ) -> OnboardingTask:
        """Persist in-memory changes made to one onboarding task entity."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity
