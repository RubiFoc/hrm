"""Data-access helpers for durable onboarding-start artifacts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.employee.models.onboarding import OnboardingRun
from hrm_backend.employee.schemas.onboarding import OnboardingRunCreate


class OnboardingRunDAO:
    """Persist and query onboarding-start rows for employee bootstrap flows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session.

        Args:
            session: Active request or job session.
        """
        self._session = session

    def get_by_employee_id(self, employee_id: str) -> OnboardingRun | None:
        """Load one onboarding run by owning employee identifier.

        Args:
            employee_id: Employee profile identifier.

        Returns:
            OnboardingRun | None: Matching onboarding run or `None`.
        """
        return (
            self._session.query(OnboardingRun)
            .filter(OnboardingRun.employee_id == employee_id)
            .first()
        )

    def get_by_id(self, onboarding_id: str) -> OnboardingRun | None:
        """Load one onboarding run by identifier."""
        return self._session.get(OnboardingRun, onboarding_id)

    def list_runs(self) -> list[OnboardingRun]:
        """Load onboarding runs in deterministic dashboard order."""
        return list(
            self._session.query(OnboardingRun)
            .order_by(
                OnboardingRun.started_at.desc(),
                OnboardingRun.onboarding_id.asc(),
            )
            .all()
        )

    def create_run(
        self,
        *,
        payload: OnboardingRunCreate,
        commit: bool = True,
    ) -> OnboardingRun:
        """Insert one onboarding-start row.

        Args:
            payload: Typed onboarding payload.
            commit: When `True`, commit immediately; otherwise only flush into the current
                transaction so callers can bundle writes atomically.

        Returns:
            OnboardingRun: Persisted onboarding run entity.
        """
        entity = OnboardingRun(
            employee_id=str(payload.employee_id),
            hire_conversion_id=str(payload.hire_conversion_id),
            status=payload.status,
            started_by_staff_id=str(payload.started_by_staff_id),
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity
