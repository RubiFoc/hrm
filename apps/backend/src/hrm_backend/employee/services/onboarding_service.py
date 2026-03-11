"""Business service for durable onboarding-start artifacts."""

from __future__ import annotations

from uuid import UUID

from hrm_backend.employee.dao.onboarding_run_dao import OnboardingRunDAO
from hrm_backend.employee.models.onboarding import OnboardingRun
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.onboarding import OnboardingRunCreate


class OnboardingRunService:
    """Create and read minimal onboarding-start artifacts after employee bootstrap."""

    def __init__(self, *, dao: OnboardingRunDAO) -> None:
        """Initialize onboarding service with DAO dependency.

        Args:
            dao: DAO for onboarding-start rows.
        """
        self._dao = dao

    def build_create_payload(
        self,
        *,
        employee_profile: EmployeeProfile,
        started_by_staff_id: str,
    ) -> OnboardingRunCreate:
        """Build a deterministic onboarding-start payload from one employee profile.

        Args:
            employee_profile: Persisted employee profile that starts onboarding.
            started_by_staff_id: Staff subject that triggered employee bootstrap.

        Returns:
            OnboardingRunCreate: Fully-typed onboarding payload ready for persistence.

        Raises:
            ValueError: If stored identifiers are not valid UUID values.
        """
        return OnboardingRunCreate(
            employee_id=UUID(employee_profile.employee_id),
            hire_conversion_id=UUID(employee_profile.hire_conversion_id),
            started_by_staff_id=UUID(started_by_staff_id),
        )

    def create_started_run(
        self,
        *,
        employee_profile: EmployeeProfile,
        started_by_staff_id: str,
        commit: bool = True,
    ) -> OnboardingRun:
        """Persist one started onboarding artifact for a bootstrapped employee profile.

        Args:
            employee_profile: Persisted employee profile that owns the onboarding run.
            started_by_staff_id: Staff subject that triggered employee bootstrap.
            commit: When `True`, commit immediately; otherwise participate in the caller's
                transaction bundle.

        Returns:
            OnboardingRun: Persisted onboarding artifact.
        """
        payload = self.build_create_payload(
            employee_profile=employee_profile,
            started_by_staff_id=started_by_staff_id,
        )
        return self._dao.create_run(payload=payload, commit=commit)

    def get_run_by_employee_id(self, employee_id: str) -> OnboardingRun | None:
        """Read one onboarding artifact by employee profile identifier.

        Args:
            employee_id: Employee profile identifier.

        Returns:
            OnboardingRun | None: Matching onboarding artifact or `None`.
        """
        return self._dao.get_by_employee_id(employee_id)
