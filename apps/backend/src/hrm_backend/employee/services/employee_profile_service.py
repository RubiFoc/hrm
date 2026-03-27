"""Business service for employee profile bootstrap, onboarding trigger, and reads."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status
from pydantic import ValidationError
from sqlalchemy.orm import Session

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.dao.hire_conversion_dao import HireConversionDAO
from hrm_backend.employee.models.hire_conversion import HireConversion
from hrm_backend.employee.models.onboarding import OnboardingRun
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.conversion import (
    HireConversionCandidateSnapshot,
    HireConversionOfferSnapshot,
)
from hrm_backend.employee.schemas.profile import (
    EmployeeProfileCreate,
    EmployeeProfileCreateRequest,
    EmployeeProfileResponse,
)
from hrm_backend.employee.services.onboarding_service import OnboardingRunService
from hrm_backend.employee.services.onboarding_task_service import (
    ONBOARDING_TEMPLATE_NOT_CONFIGURED,
    OnboardingTaskService,
    OnboardingTemplateNotConfiguredError,
)
from hrm_backend.employee.utils.conversions import HIRE_CONVERSION_STATUS_READY

HIRE_CONVERSION_NOT_FOUND = "hire_conversion_not_found"
HIRE_CONVERSION_INVALID = "hire_conversion_invalid"
EMPLOYEE_PROFILE_NOT_FOUND = "employee_profile_not_found"
EMPLOYEE_PROFILE_ALREADY_EXISTS = "employee_profile_already_exists"


class EmployeeProfileService:
    """Create and read employee profiles from durable hire-conversion handoffs."""

    def __init__(
        self,
        *,
        session: Session,
        hire_conversion_dao: HireConversionDAO,
        profile_dao: EmployeeProfileDAO,
        onboarding_service: OnboardingRunService,
        onboarding_task_service: OnboardingTaskService,
        audit_service: AuditService,
    ) -> None:
        """Initialize employee profile service dependencies.

        Args:
            session: SQLAlchemy session used to bundle profile and onboarding writes atomically.
            hire_conversion_dao: DAO for durable hire-conversion handoffs.
            profile_dao: DAO for employee profile rows.
            onboarding_service: Service for onboarding-start artifacts.
            onboarding_task_service: Service for onboarding task materialization.
            audit_service: Audit service for success and failure traces.
        """
        self._session = session
        self._hire_conversion_dao = hire_conversion_dao
        self._profile_dao = profile_dao
        self._onboarding_service = onboarding_service
        self._onboarding_task_service = onboarding_task_service
        self._audit_service = audit_service

    def build_create_payload(
        self,
        *,
        conversion: HireConversion,
        created_by_staff_id: str,
    ) -> EmployeeProfileCreate:
        """Build a deterministic employee-profile payload from one hire conversion.

        Args:
            conversion: Durable hire-conversion row.
            created_by_staff_id: Staff subject creating the employee profile.

        Returns:
            EmployeeProfileCreate: Typed profile payload ready for persistence.

        Raises:
            ValueError: If the conversion is not in `ready` state or identifiers are malformed.
            ValidationError: If frozen snapshots do not satisfy the expected schema.
        """
        if conversion.status != HIRE_CONVERSION_STATUS_READY:
            raise ValueError("Employee profile bootstrap requires a ready hire conversion")

        candidate_snapshot = HireConversionCandidateSnapshot.model_validate(
            conversion.candidate_snapshot_json
        )
        offer_snapshot = HireConversionOfferSnapshot.model_validate(conversion.offer_snapshot_json)

        return EmployeeProfileCreate(
            hire_conversion_id=UUID(conversion.conversion_id),
            vacancy_id=UUID(conversion.vacancy_id),
            candidate_id=UUID(conversion.candidate_id),
            first_name=candidate_snapshot.first_name,
            last_name=candidate_snapshot.last_name,
            email=candidate_snapshot.email,
            phone=candidate_snapshot.phone,
            location=candidate_snapshot.location,
            current_title=candidate_snapshot.current_title,
            extra_data=dict(candidate_snapshot.extra_data),
            offer_terms_summary=offer_snapshot.terms_summary,
            start_date=offer_snapshot.proposed_start_date,
            created_by_staff_id=UUID(created_by_staff_id),
        )

    def create_profile(
        self,
        *,
        payload: EmployeeProfileCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeProfileResponse:
        """Create one employee profile bundle in one transaction.

        Args:
            payload: Employee profile create request.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeProfileResponse: Persisted employee profile payload with onboarding metadata.

        Raises:
            HTTPException: If the source conversion is missing, invalid, already consumed, or no
                active onboarding template is configured for task generation.
        """
        vacancy_key = str(payload.vacancy_id)
        candidate_key = str(payload.candidate_id)
        conversion = self._hire_conversion_dao.get_by_pair(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
        )
        if conversion is None:
            self._audit_failure(
                action="employee_profile:create",
                auth_context=auth_context,
                request=request,
                reason=HIRE_CONVERSION_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=HIRE_CONVERSION_NOT_FOUND,
            )

        existing = self._profile_dao.get_by_hire_conversion_id(conversion.conversion_id)
        if existing is not None:
            self._audit_failure(
                action="employee_profile:create",
                auth_context=auth_context,
                request=request,
                resource_id=existing.employee_id,
                reason=EMPLOYEE_PROFILE_ALREADY_EXISTS,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMPLOYEE_PROFILE_ALREADY_EXISTS,
            )

        actor_sub, _ = actor_from_auth_context(auth_context)
        try:
            create_payload = self.build_create_payload(
                conversion=conversion,
                created_by_staff_id=actor_sub,
            )
        except (ValidationError, ValueError) as exc:
            self._audit_failure(
                action="employee_profile:create",
                auth_context=auth_context,
                request=request,
                reason=HIRE_CONVERSION_INVALID,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=HIRE_CONVERSION_INVALID,
            ) from exc

        try:
            entity, onboarding = self._persist_create_bundle(
                create_payload=create_payload,
                started_by_staff_id=actor_sub,
            )
        except OnboardingTemplateNotConfiguredError as exc:
            self._audit_failure(
                action="employee_profile:create",
                auth_context=auth_context,
                request=request,
                reason=ONBOARDING_TEMPLATE_NOT_CONFIGURED,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=ONBOARDING_TEMPLATE_NOT_CONFIGURED,
            ) from exc
        self._audit_success(
            action="employee_profile:create",
            auth_context=auth_context,
            request=request,
            resource_id=entity.employee_id,
        )
        return _to_employee_profile_response(entity, onboarding)

    def get_profile(
        self,
        *,
        employee_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeProfileResponse:
        """Read one employee profile by identifier.

        Args:
            employee_id: Employee profile identifier.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeProfileResponse: Employee profile payload with onboarding metadata when present.

        Raises:
            HTTPException: If the employee profile does not exist.
        """
        entity = self._profile_dao.get_by_id(str(employee_id))
        if entity is None:
            self._audit_failure(
                action="employee_profile:read",
                auth_context=auth_context,
                request=request,
                reason=EMPLOYEE_PROFILE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )

        onboarding = self._onboarding_service.get_run_by_employee_id(entity.employee_id)
        self._audit_success(
            action="employee_profile:read",
            auth_context=auth_context,
            request=request,
            resource_id=entity.employee_id,
        )
        return _to_employee_profile_response(entity, onboarding)

    def _persist_create_bundle(
        self,
        *,
        create_payload: EmployeeProfileCreate,
        started_by_staff_id: str,
    ) -> tuple[EmployeeProfile, OnboardingRun]:
        """Persist employee profile bootstrap, onboarding trigger, and tasks in one transaction."""
        try:
            entity = self._profile_dao.create_profile(payload=create_payload, commit=False)
            onboarding = self._onboarding_service.create_started_run(
                employee_profile=entity,
                started_by_staff_id=started_by_staff_id,
                commit=False,
            )
            self._onboarding_task_service.create_tasks_from_active_template(
                onboarding_run=onboarding,
                commit=False,
            )
            self._session.commit()
        except Exception:
            self._session.rollback()
            raise

        self._session.refresh(entity)
        self._session.refresh(onboarding)
        return entity, onboarding

    def _audit_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str,
    ) -> None:
        """Record one successful employee-profile audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="employee_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
        )

    def _audit_failure(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        reason: str,
        resource_id: str | None = None,
    ) -> None:
        """Record one failed employee-profile audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="employee_profile",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
            reason=reason,
        )


def _to_employee_profile_response(
    entity: EmployeeProfile,
    onboarding: OnboardingRun | None,
) -> EmployeeProfileResponse:
    """Map employee profile entity to API response schema."""
    return EmployeeProfileResponse(
        employee_id=entity.employee_id,
        hire_conversion_id=entity.hire_conversion_id,
        vacancy_id=entity.vacancy_id,
        candidate_id=entity.candidate_id,
        first_name=entity.first_name,
        last_name=entity.last_name,
        email=entity.email,
        phone=entity.phone,
        location=entity.location,
        current_title=entity.current_title,
        extra_data=dict(entity.extra_data_json or {}),
        offer_terms_summary=entity.offer_terms_summary,
        start_date=entity.start_date,
        avatar_url=_to_avatar_url(entity),
        avatar_updated_at=entity.avatar_updated_at,
        is_dismissed=entity.is_dismissed,
        onboarding_id=onboarding.onboarding_id if onboarding is not None else None,
        onboarding_status=onboarding.status if onboarding is not None else None,
        created_by_staff_id=entity.created_by_staff_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _to_avatar_url(entity: EmployeeProfile) -> str | None:
    """Build canonical employee-avatar API route for profile payloads."""
    if not entity.avatar_object_key:
        return None
    return f"/api/v1/employees/{entity.employee_id}/avatar"
