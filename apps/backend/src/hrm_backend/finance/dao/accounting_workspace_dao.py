"""Read helpers for accountant workspace visibility."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.employee.models.onboarding import OnboardingRun
from hrm_backend.employee.models.profile import EmployeeProfile


class AccountingWorkspaceDAO:
    """Load onboarding/profile pairs used by accountant workspace reads.

    Purpose:
        Provide the finance adapter with one deterministic read shape derived from the existing
        employee and onboarding tables.

    Inputs:
        session: Active SQLAlchemy session.

    Outputs:
        Joined onboarding-run and employee-profile rows ordered by the accountant workspace sort
        contract.
    """

    def __init__(self, session: Session) -> None:
        """Initialize DAO with an active SQLAlchemy session."""
        self._session = session

    def list_runs_with_profiles(self) -> list[tuple[OnboardingRun, EmployeeProfile]]:
        """Load onboarding runs joined with employee profiles in deterministic workspace order.

        Returns:
            list[tuple[OnboardingRun, EmployeeProfile]]: Joined rows ordered by
            `last_name`, `first_name`, and `employee_id`.
        """
        return list(
            self._session.query(OnboardingRun, EmployeeProfile)
            .join(EmployeeProfile, EmployeeProfile.employee_id == OnboardingRun.employee_id)
            .order_by(
                EmployeeProfile.last_name.asc(),
                EmployeeProfile.first_name.asc(),
                EmployeeProfile.employee_id.asc(),
            )
            .all()
        )
