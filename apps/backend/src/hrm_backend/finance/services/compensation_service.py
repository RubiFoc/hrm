"""Business service for compensation controls and read models."""

from __future__ import annotations

from collections import defaultdict
from datetime import UTC, date, datetime

from fastapi import HTTPException, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.finance.dao.bonus_entry_dao import BonusEntryDAO
from hrm_backend.finance.dao.compensation_raise_confirmation_dao import (
    CompensationRaiseConfirmationDAO,
)
from hrm_backend.finance.dao.compensation_raise_request_dao import CompensationRaiseRequestDAO
from hrm_backend.finance.dao.salary_band_dao import SalaryBandDAO
from hrm_backend.finance.models.bonus_entry import BonusEntry
from hrm_backend.finance.models.compensation_raise_confirmation import (
    CompensationRaiseConfirmation,
)
from hrm_backend.finance.models.compensation_raise_request import CompensationRaiseRequest
from hrm_backend.finance.models.salary_band import SalaryBand
from hrm_backend.finance.schemas.compensation import (
    BandAlignmentStatus,
    BonusEntryResponse,
    BonusUpsertRequest,
    CompensationRaiseCreateRequest,
    CompensationRaiseDecisionRequest,
    CompensationRaiseListResponse,
    CompensationRaiseResponse,
    CompensationRaiseStatus,
    CompensationTableListResponse,
    CompensationTableRowResponse,
    SalaryBandCreateRequest,
    SalaryBandListResponse,
    SalaryBandResponse,
)
from hrm_backend.finance.utils.money import CURRENCY_CODE, normalize_amount, normalize_currency
from hrm_backend.reporting.utils.dates import ensure_month_start
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO

COMPENSATION_READ_ACTION = "compensation:read"
RAISE_CREATE_ACTION = "compensation_raise:create"
RAISE_CONFIRM_ACTION = "compensation_raise:confirm"
RAISE_READ_ACTION = "compensation_raise:read"
RAISE_APPROVE_ACTION = "compensation_raise:approve"
RAISE_REJECT_ACTION = "compensation_raise:reject"
SALARY_BAND_WRITE_ACTION = "salary_band:write"
BONUS_WRITE_ACTION = "bonus:write"

EMPLOYEE_NOT_FOUND = "employee_not_found"
EMPLOYEE_FORBIDDEN = "employee_forbidden"
RAISE_NOT_FOUND = "raise_request_not_found"
RAISE_ALREADY_CONFIRMED = "raise_already_confirmed"
RAISE_ALREADY_DECIDED = "raise_already_decided"
RAISE_QUORUM_NOT_MET = "raise_quorum_not_met"
RAISE_EFFECTIVE_DATE_BACKDATED = "raise_effective_date_backdated"
RAISE_DECISION_FORBIDDEN = "raise_decision_forbidden"
SALARY_BAND_INVALID_RANGE = "salary_band_invalid_range"
SALARY_BAND_VACANCY_NOT_FOUND = "salary_band_vacancy_not_found"
BONUS_INVALID_PERIOD = "bonus_period_invalid"


class CompensationService:
    """Serve compensation read models and sensitive compensation mutations.

    Inputs:
        - authenticated staff context for access decisions;
        - employee profiles with vacancy links and hiring-manager scope;
        - raise requests, confirmations, salary bands, and bonus entries.

    Outputs:
        - unified compensation table rows for manager/HR/accountant visibility;
        - raise request lifecycle responses with quorum progress;
        - salary-band history rows for vacancy governance;
        - bonus entry create/update payloads.

    Side effects:
        - writes raise request, confirmation, salary-band, and bonus-entry rows;
        - emits immutable audit events on read, write, deny, and failure paths.
    """

    def __init__(
        self,
        *,
        settings: AppSettings,
        session: Session,
        raise_request_dao: CompensationRaiseRequestDAO,
        confirmation_dao: CompensationRaiseConfirmationDAO,
        salary_band_dao: SalaryBandDAO,
        bonus_entry_dao: BonusEntryDAO,
        employee_profile_dao: EmployeeProfileDAO,
        vacancy_dao: VacancyDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize compensation service dependencies."""
        self._settings = settings
        self._session = session
        self._raise_request_dao = raise_request_dao
        self._confirmation_dao = confirmation_dao
        self._salary_band_dao = salary_band_dao
        self._bonus_entry_dao = bonus_entry_dao
        self._employee_profile_dao = employee_profile_dao
        self._vacancy_dao = vacancy_dao
        self._audit_service = audit_service

    def list_compensation_table(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        limit: int,
        offset: int,
    ) -> CompensationTableListResponse:
        """Return the unified compensation table for the current actor."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        try:
            profiles, total = self._load_compensation_profiles(
                role=auth_context.role,
                actor_sub=actor_sub,
                limit=limit,
                offset=offset,
            )
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action=COMPENSATION_READ_ACTION,
                resource_type="compensation_table",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=_normalize_reason(exc.detail),
            )
            raise

        employee_ids = [profile.employee_id for profile in profiles]
        vacancy_ids = [profile.vacancy_id for profile in profiles]
        raise_requests = self._raise_request_dao.list_by_employee_ids(employee_ids=employee_ids)
        bonus_entries = self._bonus_entry_dao.list_by_employee_ids(employee_ids=employee_ids)
        salary_bands = self._salary_band_dao.list_by_vacancy_ids(vacancy_ids=vacancy_ids)

        rows = _build_compensation_rows(
            profiles=profiles,
            raise_requests=raise_requests,
            bonus_entries=bonus_entries,
            salary_bands=salary_bands,
        )
        self._audit_service.record_api_event(
            action=COMPENSATION_READ_ACTION,
            resource_type="compensation_table",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return CompensationTableListResponse(items=rows, total=total, limit=limit, offset=offset)

    def list_raise_requests(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        status_filter: CompensationRaiseStatus | None,
        limit: int,
        offset: int,
    ) -> CompensationRaiseListResponse:
        """List raise requests visible to the current actor."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        employee_ids = self._resolve_raise_visibility_scope(
            role=auth_context.role,
            actor_sub=actor_sub,
        )
        items = self._raise_request_dao.list_requests(
            employee_ids=employee_ids,
            status=status_filter,
            limit=limit,
            offset=offset,
        )
        confirmations = self._confirmation_dao.list_by_request_ids(
            [request.request_id for request in items]
        )
        response_items = [
            _to_raise_response(
                request=item,
                confirmations=_group_confirmations(confirmations).get(item.request_id, []),
                confirmation_quorum=self._settings.compensation_raise_manager_quorum,
            )
            for item in items
        ]
        total = self._raise_request_dao.count_requests(
            employee_ids=employee_ids,
            status=status_filter,
        )
        self._audit_service.record_api_event(
            action=RAISE_READ_ACTION,
            resource_type="compensation_raise",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return CompensationRaiseListResponse(
            items=response_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def create_raise_request(
        self,
        *,
        payload: CompensationRaiseCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> CompensationRaiseResponse:
        """Create a manager-initiated raise request."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        employee = self._resolve_employee_for_manager(
            employee_id=str(payload.employee_id),
            actor_sub=actor_sub,
            request=request,
        )
        self._ensure_effective_date_valid(
            payload.effective_date,
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            action=RAISE_CREATE_ACTION,
        )
        normalized_amount = normalize_amount(payload.proposed_base_salary)
        currency = normalize_currency()
        entity = CompensationRaiseRequest(
            employee_id=employee.employee_id,
            requested_by_staff_id=actor_sub,
            requested_at=datetime.now(UTC),
            effective_date=payload.effective_date,
            proposed_base_salary=normalized_amount,
            currency=currency,
            status="pending_confirmations",
        )
        self._raise_request_dao.create(entity=entity, commit=True)
        confirmation_quorum = self._settings.compensation_raise_manager_quorum
        response = _to_raise_response(
            request=entity,
            confirmations=[],
            confirmation_quorum=confirmation_quorum,
        )
        self._audit_service.record_api_event(
            action=RAISE_CREATE_ACTION,
            resource_type="compensation_raise",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.request_id,
            after_snapshot=_raise_snapshot(entity),
        )
        return response

    def confirm_raise_request(
        self,
        *,
        request_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> CompensationRaiseResponse:
        """Record a manager confirmation for a raise request."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        raise_request = self._resolve_raise_request(
            request_id=request_id,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request=request,
            action=RAISE_CONFIRM_ACTION,
        )
        if raise_request.status in {"approved", "rejected"}:
            self._audit_service.record_api_event(
                action=RAISE_CONFIRM_ACTION,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=request_id,
                reason=RAISE_ALREADY_DECIDED,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=RAISE_ALREADY_DECIDED)

        existing_count = self._confirmation_dao.count_by_request_id(raise_request.request_id)
        before_snapshot = _raise_confirmation_snapshot(raise_request, existing_count, None)
        confirmation = CompensationRaiseConfirmation(
            raise_request_id=raise_request.request_id,
            manager_staff_id=actor_sub,
            confirmed_at=datetime.now(UTC),
        )
        try:
            self._confirmation_dao.create(entity=confirmation, commit=True)
        except IntegrityError as exc:
            self._session.rollback()
            self._audit_service.record_api_event(
                action=RAISE_CONFIRM_ACTION,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=request_id,
                reason=RAISE_ALREADY_CONFIRMED,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=RAISE_ALREADY_CONFIRMED,
            ) from exc

        confirmation_count = self._confirmation_dao.count_by_request_id(raise_request.request_id)
        quorum = self._settings.compensation_raise_manager_quorum
        if confirmation_count >= quorum and raise_request.status == "pending_confirmations":
            raise_request.status = "awaiting_leader"
            self._raise_request_dao.update(entity=raise_request, commit=True)

        confirmations = self._confirmation_dao.list_by_request_id(raise_request.request_id)
        response = _to_raise_response(
            request=raise_request,
            confirmations=confirmations,
            confirmation_quorum=quorum,
        )
        self._audit_service.record_api_event(
            action=RAISE_CONFIRM_ACTION,
            resource_type="compensation_raise",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=request_id,
            before_snapshot=before_snapshot,
            after_snapshot=_raise_confirmation_snapshot(
                raise_request,
                confirmation_count,
                response.status,
            ),
        )
        return response

    def approve_raise_request(
        self,
        *,
        request_id: str,
        payload: CompensationRaiseDecisionRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> CompensationRaiseResponse:
        """Approve a raise request after quorum is reached."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        raise_request, confirmation_count = self._resolve_raise_for_leader_decision(
            request_id=request_id,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request=request,
            action=RAISE_APPROVE_ACTION,
        )
        self._ensure_effective_date_valid(
            raise_request.effective_date,
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            action=RAISE_APPROVE_ACTION,
        )
        before_snapshot = _raise_snapshot(raise_request)
        raise_request.status = "approved"
        raise_request.leader_decision_by_staff_id = actor_sub
        raise_request.leader_decision_at = datetime.now(UTC)
        raise_request.leader_decision_note = payload.note
        self._raise_request_dao.update(entity=raise_request, commit=True)
        confirmations = self._confirmation_dao.list_by_request_id(raise_request.request_id)
        response = _to_raise_response(
            request=raise_request,
            confirmations=confirmations,
            confirmation_quorum=self._settings.compensation_raise_manager_quorum,
        )
        self._audit_service.record_api_event(
            action=RAISE_APPROVE_ACTION,
            resource_type="compensation_raise",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=request_id,
            before_snapshot=before_snapshot,
            after_snapshot=_raise_snapshot(raise_request),
            reason=f"confirmations={confirmation_count}",
        )
        return response

    def reject_raise_request(
        self,
        *,
        request_id: str,
        payload: CompensationRaiseDecisionRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> CompensationRaiseResponse:
        """Reject a raise request after quorum is reached."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        raise_request, confirmation_count = self._resolve_raise_for_leader_decision(
            request_id=request_id,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request=request,
            action=RAISE_REJECT_ACTION,
        )
        before_snapshot = _raise_snapshot(raise_request)
        raise_request.status = "rejected"
        raise_request.leader_decision_by_staff_id = actor_sub
        raise_request.leader_decision_at = datetime.now(UTC)
        raise_request.leader_decision_note = payload.note
        self._raise_request_dao.update(entity=raise_request, commit=True)
        confirmations = self._confirmation_dao.list_by_request_id(raise_request.request_id)
        response = _to_raise_response(
            request=raise_request,
            confirmations=confirmations,
            confirmation_quorum=self._settings.compensation_raise_manager_quorum,
        )
        self._audit_service.record_api_event(
            action=RAISE_REJECT_ACTION,
            resource_type="compensation_raise",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=request_id,
            before_snapshot=before_snapshot,
            after_snapshot=_raise_snapshot(raise_request),
            reason=f"confirmations={confirmation_count}",
        )
        return response

    def list_salary_bands(
        self,
        *,
        vacancy_id: str,
    ) -> SalaryBandListResponse:
        """Return salary-band history for one vacancy."""
        items = [
            _to_salary_band_response(item)
            for item in self._salary_band_dao.list_by_vacancy_id(vacancy_id)
        ]
        return SalaryBandListResponse(items=items)

    def create_salary_band(
        self,
        *,
        payload: SalaryBandCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> SalaryBandResponse:
        """Create a new salary band version for a vacancy."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        vacancy = self._vacancy_dao.get_by_id(str(payload.vacancy_id))
        if vacancy is None:
            self._audit_service.record_api_event(
                action=SALARY_BAND_WRITE_ACTION,
                resource_type="salary_band",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=SALARY_BAND_VACANCY_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=SALARY_BAND_VACANCY_NOT_FOUND,
            )

        normalized_min = normalize_amount(payload.min_amount)
        normalized_max = normalize_amount(payload.max_amount)
        if normalized_min > normalized_max:
            self._audit_service.record_api_event(
                action=SALARY_BAND_WRITE_ACTION,
                resource_type="salary_band",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=SALARY_BAND_INVALID_RANGE,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=SALARY_BAND_INVALID_RANGE,
            )

        currency = normalize_currency()
        version = self._salary_band_dao.get_latest_version(vacancy.vacancy_id) + 1
        previous = self._latest_band_for_vacancy(vacancy.vacancy_id)
        entity = SalaryBand(
            vacancy_id=vacancy.vacancy_id,
            band_version=version,
            min_amount=normalized_min,
            max_amount=normalized_max,
            currency=currency,
            created_by_staff_id=actor_sub,
            created_at=datetime.now(UTC),
        )
        self._salary_band_dao.create(entity=entity, commit=True)
        response = _to_salary_band_response(entity)
        self._audit_service.record_api_event(
            action=SALARY_BAND_WRITE_ACTION,
            resource_type="salary_band",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.band_id,
            before_snapshot=_salary_band_snapshot(previous) if previous else None,
            after_snapshot=_salary_band_snapshot(entity),
        )
        return response

    def upsert_bonus_entry(
        self,
        *,
        payload: BonusUpsertRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> BonusEntryResponse:
        """Create or update a manual bonus entry."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        employee = self._employee_profile_dao.get_by_id(str(payload.employee_id))
        if employee is None:
            self._audit_service.record_api_event(
                action=BONUS_WRITE_ACTION,
                resource_type="bonus_entry",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=EMPLOYEE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_NOT_FOUND,
            )

        try:
            ensure_month_start(payload.period_month)
        except ValueError as exc:
            self._audit_service.record_api_event(
                action=BONUS_WRITE_ACTION,
                resource_type="bonus_entry",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=BONUS_INVALID_PERIOD,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=BONUS_INVALID_PERIOD,
            ) from exc

        normalized_amount = normalize_amount(payload.amount)
        currency = normalize_currency()
        existing = self._bonus_entry_dao.get_by_employee_and_month(
            employee_id=employee.employee_id,
            period_month=payload.period_month,
        )
        if existing is None:
            entity = BonusEntry(
                employee_id=employee.employee_id,
                period_month=payload.period_month,
                amount=normalized_amount,
                currency=currency,
                note=payload.note,
                created_by_staff_id=actor_sub,
                updated_by_staff_id=actor_sub,
                created_at=datetime.now(UTC),
                updated_at=datetime.now(UTC),
            )
            self._bonus_entry_dao.create(entity=entity, commit=True)
            response = _to_bonus_response(entity)
            self._audit_service.record_api_event(
                action=BONUS_WRITE_ACTION,
                resource_type="bonus_entry",
                result="success",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=entity.bonus_id,
                after_snapshot=_bonus_snapshot(entity),
            )
            return response

        before_snapshot = _bonus_snapshot(existing)
        existing.amount = normalized_amount
        existing.currency = currency
        existing.note = payload.note
        existing.updated_by_staff_id = actor_sub
        existing.updated_at = datetime.now(UTC)
        self._bonus_entry_dao.update(entity=existing, commit=True)
        response = _to_bonus_response(existing)
        self._audit_service.record_api_event(
            action=BONUS_WRITE_ACTION,
            resource_type="bonus_entry",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=existing.bonus_id,
            before_snapshot=before_snapshot,
            after_snapshot=_bonus_snapshot(existing),
        )
        return response

    def _load_compensation_profiles(
        self,
        *,
        role: str,
        actor_sub: str,
        limit: int,
        offset: int,
    ) -> tuple[list[EmployeeProfile], int]:
        """Resolve employee profile scope for compensation reads."""
        if role == "manager":
            vacancies = self._vacancy_dao.list_by_hiring_manager_staff_id(actor_sub)
            vacancy_ids = [vacancy.vacancy_id for vacancy in vacancies]
            profiles = self._employee_profile_dao.list_by_vacancy_ids(
                vacancy_ids=vacancy_ids,
                limit=limit,
                offset=offset,
                include_dismissed=False,
            )
            total = self._employee_profile_dao.count_by_vacancy_ids(
                vacancy_ids=vacancy_ids,
                include_dismissed=False,
            )
            return profiles, total

        profiles = self._employee_profile_dao.list_directory(
            limit=limit,
            offset=offset,
            include_dismissed=False,
        )
        total = self._employee_profile_dao.count_directory(include_dismissed=False)
        return profiles, total

    def _resolve_employee_for_manager(
        self,
        *,
        employee_id: str,
        actor_sub: str,
        request: Request,
    ) -> EmployeeProfile:
        """Load employee profile and enforce manager vacancy scope."""
        employee = self._employee_profile_dao.get_by_id(employee_id)
        if employee is None:
            self._audit_service.record_api_event(
                action=RAISE_CREATE_ACTION,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role="manager",
                reason=EMPLOYEE_NOT_FOUND,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EMPLOYEE_NOT_FOUND)

        vacancy = self._vacancy_dao.get_by_id(employee.vacancy_id)
        if vacancy is None or vacancy.hiring_manager_staff_id != actor_sub:
            self._audit_service.record_api_event(
                action=RAISE_CREATE_ACTION,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role="manager",
                reason=EMPLOYEE_FORBIDDEN,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=EMPLOYEE_NOT_FOUND)
        return employee

    def _resolve_raise_request(
        self,
        *,
        request_id: str,
        actor_sub: str,
        actor_role: str,
        request: Request,
        action: str,
    ) -> CompensationRaiseRequest:
        """Load raise request or return a standardized 404."""
        raise_request = self._raise_request_dao.get_by_id(request_id)
        if raise_request is None:
            self._audit_service.record_api_event(
                action=action,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=RAISE_NOT_FOUND,
            )
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=RAISE_NOT_FOUND)
        return raise_request

    def _resolve_raise_for_leader_decision(
        self,
        *,
        request_id: str,
        actor_sub: str,
        actor_role: str,
        request: Request,
        action: str,
    ) -> tuple[CompensationRaiseRequest, int]:
        """Load raise request and validate quorum/decision rules for leader actions."""
        raise_request = self._resolve_raise_request(
            request_id=request_id,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request=request,
            action=action,
        )
        if raise_request.requested_by_staff_id == actor_sub:
            self._audit_service.record_api_event(
                action=action,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=request_id,
                reason=RAISE_DECISION_FORBIDDEN,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=RAISE_DECISION_FORBIDDEN,
            )

        if raise_request.status in {"approved", "rejected"}:
            self._audit_service.record_api_event(
                action=action,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=request_id,
                reason=RAISE_ALREADY_DECIDED,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=RAISE_ALREADY_DECIDED)

        confirmation_count = self._confirmation_dao.count_by_request_id(raise_request.request_id)
        if confirmation_count < self._settings.compensation_raise_manager_quorum:
            self._audit_service.record_api_event(
                action=action,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=request_id,
                reason=RAISE_QUORUM_NOT_MET,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=RAISE_QUORUM_NOT_MET)

        return raise_request, confirmation_count

    def _resolve_raise_visibility_scope(self, *, role: str, actor_sub: str) -> list[str] | None:
        """Resolve employee identifiers visible for raise list reads."""
        if role == "manager":
            vacancies = self._vacancy_dao.list_by_hiring_manager_staff_id(actor_sub)
            vacancy_ids = [vacancy.vacancy_id for vacancy in vacancies]
            profiles = self._employee_profile_dao.list_by_vacancy_ids(
                vacancy_ids=vacancy_ids,
                limit=10_000,
                offset=0,
                include_dismissed=False,
            )
            return [profile.employee_id for profile in profiles]
        if role == "leader":
            return None
        return []

    def _latest_band_for_vacancy(self, vacancy_id: str) -> SalaryBand | None:
        """Load the latest salary band for one vacancy."""
        bands = self._salary_band_dao.list_by_vacancy_id(vacancy_id)
        return bands[0] if bands else None

    def _ensure_effective_date_valid(
        self,
        effective_date: date,
        request: Request,
        actor_sub: str,
        actor_role: str,
        action: str,
    ) -> None:
        """Validate effective date policy and raise 422 when backdated."""
        today = datetime.now(UTC).date()
        if effective_date < today:
            self._audit_service.record_api_event(
                action=action,
                resource_type="compensation_raise",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=RAISE_EFFECTIVE_DATE_BACKDATED,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=RAISE_EFFECTIVE_DATE_BACKDATED,
            )


def _build_compensation_rows(
    *,
    profiles: list[EmployeeProfile],
    raise_requests: list[CompensationRaiseRequest],
    bonus_entries: list[BonusEntry],
    salary_bands: list[SalaryBand],
) -> list[CompensationTableRowResponse]:
    """Map persisted entities into compensation table rows."""
    raise_by_employee: dict[str, list[CompensationRaiseRequest]] = defaultdict(list)
    for request in raise_requests:
        raise_by_employee[request.employee_id].append(request)

    bonus_by_employee: dict[str, BonusEntry] = {}
    for entry in bonus_entries:
        existing = bonus_by_employee.get(entry.employee_id)
        if existing is None or entry.period_month > existing.period_month:
            bonus_by_employee[entry.employee_id] = entry

    band_by_vacancy: dict[str, SalaryBand] = {}
    for band in salary_bands:
        existing = band_by_vacancy.get(band.vacancy_id)
        if existing is None or band.band_version > existing.band_version:
            band_by_vacancy[band.vacancy_id] = band

    rows: list[CompensationTableRowResponse] = []
    today = datetime.now(UTC).date()
    for profile in profiles:
        raise_history = raise_by_employee.get(profile.employee_id, [])
        latest_request = raise_history[0] if raise_history else None
        approved = [
            request
            for request in raise_history
            if request.status == "approved" and request.effective_date <= today
        ]
        approved.sort(
            key=lambda request: (request.effective_date, request.requested_at),
            reverse=True,
        )
        base_salary = approved[0].proposed_base_salary if approved else None
        bonus_entry = bonus_by_employee.get(profile.employee_id)
        salary_band = band_by_vacancy.get(profile.vacancy_id)
        band_status = _resolve_band_alignment(base_salary, salary_band)
        rows.append(
            CompensationTableRowResponse(
                employee_id=profile.employee_id,
                full_name=f"{profile.first_name} {profile.last_name}",
                department=profile.department,
                position_title=profile.position_title,
                currency=CURRENCY_CODE,
                base_salary=base_salary,
                bonus_amount=bonus_entry.amount if bonus_entry else None,
                bonus_period_month=bonus_entry.period_month if bonus_entry else None,
                salary_band_min=salary_band.min_amount if salary_band else None,
                salary_band_max=salary_band.max_amount if salary_band else None,
                band_alignment_status=band_status,
                last_raise_effective_date=latest_request.effective_date if latest_request else None,
                last_raise_status=latest_request.status if latest_request else None,
            )
        )
    return rows


def _resolve_band_alignment(
    base_salary: float | None,
    salary_band: SalaryBand | None,
) -> BandAlignmentStatus | None:
    """Resolve band alignment status for one salary/band pair."""
    if base_salary is None or salary_band is None:
        return None
    if base_salary < salary_band.min_amount:
        return "below_band"
    if base_salary > salary_band.max_amount:
        return "above_band"
    return "within_band"


def _to_raise_response(
    *,
    request: CompensationRaiseRequest,
    confirmations: list[CompensationRaiseConfirmation],
    confirmation_quorum: int,
) -> CompensationRaiseResponse:
    """Convert raise request entity and confirmations into response payload."""
    return CompensationRaiseResponse(
        request_id=request.request_id,
        employee_id=request.employee_id,
        requested_by_staff_id=request.requested_by_staff_id,
        requested_at=request.requested_at,
        effective_date=request.effective_date,
        proposed_base_salary=request.proposed_base_salary,
        currency=request.currency,
        status=request.status,  # type: ignore[arg-type]
        confirmation_count=len(confirmations),
        confirmation_quorum=confirmation_quorum,
        leader_decision_by_staff_id=request.leader_decision_by_staff_id,
        leader_decision_at=request.leader_decision_at,
        leader_decision_note=request.leader_decision_note,
    )


def _to_salary_band_response(entity: SalaryBand) -> SalaryBandResponse:
    """Convert salary band entity into response payload."""
    return SalaryBandResponse(
        band_id=entity.band_id,
        vacancy_id=entity.vacancy_id,
        band_version=entity.band_version,
        min_amount=entity.min_amount,
        max_amount=entity.max_amount,
        currency=entity.currency,
        created_by_staff_id=entity.created_by_staff_id,
        created_at=entity.created_at,
    )


def _to_bonus_response(entity: BonusEntry) -> BonusEntryResponse:
    """Convert bonus entry entity into response payload."""
    return BonusEntryResponse(
        bonus_id=entity.bonus_id,
        employee_id=entity.employee_id,
        period_month=entity.period_month,
        amount=entity.amount,
        currency=entity.currency,
        note=entity.note,
        created_by_staff_id=entity.created_by_staff_id,
        updated_by_staff_id=entity.updated_by_staff_id,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _group_confirmations(
    confirmations: list[CompensationRaiseConfirmation],
) -> dict[str, list[CompensationRaiseConfirmation]]:
    """Group confirmations by raise request identifier."""
    grouped: dict[str, list[CompensationRaiseConfirmation]] = defaultdict(list)
    for confirmation in confirmations:
        grouped[confirmation.raise_request_id].append(confirmation)
    return grouped


def _normalize_reason(detail: object) -> str:
    """Normalize error detail payload into a reason string."""
    if isinstance(detail, str) and detail.strip():
        return detail.strip()
    return "compensation_error"


def _raise_snapshot(request: CompensationRaiseRequest) -> dict[str, object]:
    """Build a monetary snapshot for a raise request."""
    return {
        "employee_id": request.employee_id,
        "proposed_base_salary": request.proposed_base_salary,
        "currency": request.currency,
        "effective_date": request.effective_date.isoformat(),
        "status": request.status,
    }


def _raise_confirmation_snapshot(
    request: CompensationRaiseRequest,
    confirmation_count: int,
    status_override: str | None,
) -> dict[str, object]:
    """Build a snapshot for raise confirmation progress."""
    return {
        "request_id": request.request_id,
        "confirmation_count": confirmation_count,
        "status": status_override or request.status,
    }


def _salary_band_snapshot(entity: SalaryBand) -> dict[str, object]:
    """Build a monetary snapshot for a salary band entry."""
    return {
        "vacancy_id": entity.vacancy_id,
        "band_version": entity.band_version,
        "min_amount": entity.min_amount,
        "max_amount": entity.max_amount,
        "currency": entity.currency,
    }


def _bonus_snapshot(entity: BonusEntry) -> dict[str, object]:
    """Build a monetary snapshot for a bonus entry."""
    return {
        "employee_id": entity.employee_id,
        "period_month": entity.period_month.isoformat(),
        "amount": entity.amount,
        "currency": entity.currency,
    }
