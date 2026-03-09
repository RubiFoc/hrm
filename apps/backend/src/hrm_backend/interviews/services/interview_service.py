"""Business service for HR interview scheduling and public token workflows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.core.errors.http import service_unavailable
from hrm_backend.interviews.dao.calendar_binding_dao import InterviewCalendarBindingDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.infra.celery.dispatch import enqueue_interview_sync
from hrm_backend.interviews.infra.google_calendar import InterviewCalendarAdapter
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.interviews.schemas.interview import (
    HRInterviewListResponse,
    HRInterviewResponse,
    InterviewCancelRequest,
    InterviewCreateRequest,
    InterviewRescheduleRequest,
    PublicInterviewActionRequest,
    PublicInterviewRegistrationResponse,
)
from hrm_backend.interviews.utils.lifecycle import (
    can_candidate_cancel,
    can_candidate_confirm,
    can_candidate_request_reschedule,
    can_hr_cancel,
    can_hr_reschedule,
)
from hrm_backend.interviews.utils.scheduling import normalize_schedule_window
from hrm_backend.interviews.utils.tokens import InterviewTokenManager
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO


class InterviewService:
    """Orchestrates HR interview scheduling and public token workflows."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        vacancy_dao: VacancyDAO,
        candidate_profile_dao: CandidateProfileDAO,
        transition_dao: PipelineTransitionDAO,
        interview_dao: InterviewDAO,
        binding_dao: InterviewCalendarBindingDAO,
        calendar_adapter: InterviewCalendarAdapter,
        token_manager: InterviewTokenManager,
        audit_service: AuditService,
    ) -> None:
        """Initialize service dependencies."""
        self._settings = settings
        self._vacancy_dao = vacancy_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._transition_dao = transition_dao
        self._interview_dao = interview_dao
        self._binding_dao = binding_dao
        self._calendar_adapter = calendar_adapter
        self._token_manager = token_manager
        self._audit_service = audit_service

    def create_interview(
        self,
        *,
        vacancy_id: UUID,
        payload: InterviewCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> HRInterviewResponse:
        """Create one active interview row and enqueue calendar sync."""
        self._ensure_calendar_adapter_enabled()
        self._get_vacancy_candidate_or_404(
            vacancy_id=str(vacancy_id),
            candidate_id=str(payload.candidate_id),
        )
        self._ensure_pipeline_stage_allows_create(
            vacancy_id=str(vacancy_id),
            candidate_id=str(payload.candidate_id),
        )
        self._ensure_no_active_interview(vacancy_id=str(vacancy_id), candidate_id=str(payload.candidate_id))
        interviewer_staff_ids = self._normalize_and_validate_interviewers(payload.interviewer_staff_ids)
        scheduled_start_at, scheduled_end_at, timezone_name = normalize_schedule_window(
            scheduled_start_local=payload.scheduled_start_local,
            scheduled_end_local=payload.scheduled_end_local,
            timezone_name=payload.timezone,
        )
        entity = self._interview_dao.create_interview(
            vacancy_id=str(vacancy_id),
            candidate_id=str(payload.candidate_id),
            scheduled_start_at=scheduled_start_at,
            scheduled_end_at=scheduled_end_at,
            timezone=timezone_name,
            location_kind=payload.location_kind,
            location_details=_normalize_optional_text(payload.location_details),
            interviewer_staff_ids=interviewer_staff_ids,
            created_by_staff_id=str(auth_context.subject_id),
        )
        enqueue_interview_sync(interview_id=entity.interview_id)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="interview:create",
            resource_type="interview",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.interview_id,
        )
        return self._build_hr_response(entity=entity)

    def list_interviews(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID | None,
        interview_status: str | None,
        auth_context: AuthContext,
        request: Request,
    ) -> HRInterviewListResponse:
        """List interview rows for one vacancy with optional filters."""
        self._get_vacancy_or_404(str(vacancy_id))
        if candidate_id is not None:
            self._get_candidate_or_404(str(candidate_id))
        items = self._interview_dao.list_for_vacancy(
            vacancy_id=str(vacancy_id),
            candidate_id=None if candidate_id is None else str(candidate_id),
            status=interview_status,
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="interview:read",
            resource_type="interview",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(vacancy_id),
        )
        return HRInterviewListResponse(items=[self._build_hr_response(entity=item) for item in items])

    def get_interview(
        self,
        *,
        vacancy_id: UUID,
        interview_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> HRInterviewResponse:
        """Read one interview row by vacancy-scoped identifier."""
        entity = self._get_interview_for_vacancy_or_404(
            vacancy_id=str(vacancy_id),
            interview_id=str(interview_id),
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="interview:read",
            resource_type="interview",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.interview_id,
        )
        return self._build_hr_response(entity=entity)

    def reschedule_interview(
        self,
        *,
        vacancy_id: UUID,
        interview_id: UUID,
        payload: InterviewRescheduleRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> HRInterviewResponse:
        """Replace schedule window and enqueue interview sync again."""
        self._ensure_calendar_adapter_enabled()
        entity = self._get_interview_for_vacancy_or_404(
            vacancy_id=str(vacancy_id),
            interview_id=str(interview_id),
        )
        if not can_hr_reschedule(entity.status):  # type: ignore[arg-type]
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="interview_terminal")
        interviewer_staff_ids = self._normalize_and_validate_interviewers(payload.interviewer_staff_ids)
        scheduled_start_at, scheduled_end_at, timezone_name = normalize_schedule_window(
            scheduled_start_local=payload.scheduled_start_local,
            scheduled_end_local=payload.scheduled_end_local,
            timezone_name=payload.timezone,
        )
        entity.schedule_version += 1
        entity.status = "pending_sync"
        entity.calendar_sync_status = "queued"
        entity.scheduled_start_at = scheduled_start_at
        entity.scheduled_end_at = scheduled_end_at
        entity.timezone = timezone_name
        entity.location_kind = payload.location_kind
        entity.location_details = _normalize_optional_text(payload.location_details)
        entity.interviewer_staff_ids_json = interviewer_staff_ids
        entity.updated_by_staff_id = str(auth_context.subject_id)
        entity.calendar_event_id = None
        entity.calendar_sync_reason_code = None
        entity.calendar_sync_error_detail = None
        entity.candidate_response_status = "pending"
        entity.candidate_response_note = None
        self._invalidate_candidate_token(entity)
        entity = self._interview_dao.save(entity)
        enqueue_interview_sync(interview_id=entity.interview_id)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="interview:update",
            resource_type="interview",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.interview_id,
        )
        return self._build_hr_response(entity=entity)

    def cancel_interview(
        self,
        *,
        vacancy_id: UUID,
        interview_id: UUID,
        payload: InterviewCancelRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> HRInterviewResponse:
        """Cancel one interview and remove public access immediately."""
        entity = self._get_interview_for_vacancy_or_404(
            vacancy_id=str(vacancy_id),
            interview_id=str(interview_id),
        )
        if not can_hr_cancel(entity.status):  # type: ignore[arg-type]
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="interview_terminal")

        bindings = self._binding_dao.list_for_interview(entity.interview_id)
        if bindings and not self._calendar_adapter.is_configured():
            raise service_unavailable("calendar_not_configured")

        entity.status = "cancelled"
        entity.cancelled_by = "staff"
        entity.cancel_reason_code = payload.cancel_reason_code.strip()
        entity.updated_by_staff_id = str(auth_context.subject_id)
        self._invalidate_candidate_token(entity)
        if bindings:
            entity.calendar_sync_status = "queued"
        else:
            entity.calendar_sync_status = "synced"
            entity.last_synced_at = datetime.now(UTC)
            entity.calendar_event_id = None
        entity = self._interview_dao.save(entity)
        if bindings:
            enqueue_interview_sync(interview_id=entity.interview_id)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="interview:cancel",
            resource_type="interview",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.interview_id,
            reason=payload.cancel_reason_code.strip(),
        )
        return self._build_hr_response(entity=entity)

    def resend_invite(
        self,
        *,
        vacancy_id: UUID,
        interview_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> HRInterviewResponse:
        """Issue a fresh token for the current synchronized schedule version."""
        entity = self._get_interview_for_vacancy_or_404(
            vacancy_id=str(vacancy_id),
            interview_id=str(interview_id),
        )
        if entity.calendar_sync_status != "synced":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="invite_not_available_until_calendar_synced",
            )
        if entity.status not in {"awaiting_candidate_confirmation", "confirmed"}:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="interview_state_does_not_allow_invite_resend",
            )
        self._issue_candidate_token(entity)
        entity.updated_by_staff_id = str(auth_context.subject_id)
        entity = self._interview_dao.save(entity)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="interview:resend_invite",
            resource_type="interview",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.interview_id,
        )
        return self._build_hr_response(entity=entity)

    def get_public_registration(
        self,
        *,
        token: str,
        request: Request,
    ) -> PublicInterviewRegistrationResponse:
        """Load candidate-facing interview registration payload for one token."""
        entity = self._get_interview_by_token_or_error(token)
        vacancy = self._get_vacancy_or_404(entity.vacancy_id)
        self._audit_service.record_api_event(
            action="interview_registration:read",
            resource_type="interview",
            result="success",
            request=request,
            resource_id=entity.interview_id,
        )
        return self._build_public_response(entity=entity, vacancy_title=vacancy.title)

    def confirm_public_registration(
        self,
        *,
        token: str,
        request: Request,
    ) -> PublicInterviewRegistrationResponse:
        """Confirm current interview schedule via public token."""
        entity = self._get_interview_by_token_or_error(token)
        if not can_candidate_confirm(entity.status):  # type: ignore[arg-type]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="interview_state_does_not_allow_confirmation",
            )
        entity.status = "confirmed"
        entity.candidate_response_status = "confirmed"
        entity.candidate_response_note = None
        entity = self._interview_dao.save(entity)
        vacancy = self._get_vacancy_or_404(entity.vacancy_id)
        self._audit_service.record_api_event(
            action="interview_registration:confirm",
            resource_type="interview",
            result="success",
            request=request,
            resource_id=entity.interview_id,
        )
        return self._build_public_response(entity=entity, vacancy_title=vacancy.title)

    def request_public_reschedule(
        self,
        *,
        token: str,
        payload: PublicInterviewActionRequest,
        request: Request,
    ) -> PublicInterviewRegistrationResponse:
        """Request a new slot via public token without changing the current schedule."""
        entity = self._get_interview_by_token_or_error(token)
        if not can_candidate_request_reschedule(entity.status):  # type: ignore[arg-type]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="interview_state_does_not_allow_reschedule_request",
            )
        entity.status = "reschedule_requested"
        entity.candidate_response_status = "reschedule_requested"
        entity.candidate_response_note = _normalize_optional_text(payload.note)
        entity = self._interview_dao.save(entity)
        vacancy = self._get_vacancy_or_404(entity.vacancy_id)
        self._audit_service.record_api_event(
            action="interview_registration:request_reschedule",
            resource_type="interview",
            result="success",
            request=request,
            resource_id=entity.interview_id,
            reason="candidate_reschedule_requested",
        )
        return self._build_public_response(entity=entity, vacancy_title=vacancy.title)

    def cancel_public_registration(
        self,
        *,
        token: str,
        payload: PublicInterviewActionRequest,
        request: Request,
    ) -> PublicInterviewRegistrationResponse:
        """Decline interview via public token and enqueue calendar cleanup when needed."""
        entity = self._get_interview_by_token_or_error(token)
        if not can_candidate_cancel(entity.status):  # type: ignore[arg-type]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="interview_state_does_not_allow_cancellation",
            )
        bindings = self._binding_dao.list_for_interview(entity.interview_id)
        if bindings and not self._calendar_adapter.is_configured():
            raise service_unavailable("calendar_not_configured")
        entity.status = "cancelled"
        entity.cancelled_by = "candidate"
        entity.cancel_reason_code = "candidate_declined"
        entity.candidate_response_status = "declined"
        entity.candidate_response_note = _normalize_optional_text(payload.note)
        self._invalidate_candidate_token(entity)
        if bindings:
            entity.calendar_sync_status = "queued"
        else:
            entity.calendar_sync_status = "synced"
            entity.last_synced_at = datetime.now(UTC)
            entity.calendar_event_id = None
        entity = self._interview_dao.save(entity)
        if bindings:
            enqueue_interview_sync(interview_id=entity.interview_id)
        vacancy = self._get_vacancy_or_404(entity.vacancy_id)
        self._audit_service.record_api_event(
            action="interview_registration:cancel",
            resource_type="interview",
            result="success",
            request=request,
            resource_id=entity.interview_id,
            reason="candidate_declined",
        )
        return self._build_public_response(entity=entity, vacancy_title=vacancy.title)

    def _ensure_calendar_adapter_enabled(self) -> None:
        """Ensure runtime calendar integration is enabled for sync-dependent actions."""
        if not self._calendar_adapter.is_configured():
            raise service_unavailable("calendar_not_configured")

    def _normalize_and_validate_interviewers(self, interviewer_staff_ids: list[UUID]) -> list[str]:
        """Validate interviewer list, reject duplicates, and ensure calendar mapping exists."""
        raw_ids = [str(item) for item in interviewer_staff_ids]
        if len(raw_ids) != len(set(raw_ids)):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="duplicate_interviewer_list",
            )
        normalized = sorted(raw_ids)
        self._calendar_adapter.ensure_ready_for_interviewers(normalized)
        return normalized

    def _ensure_pipeline_stage_allows_create(self, *, vacancy_id: str, candidate_id: str) -> None:
        """Ensure candidate is currently in shortlist or interview pipeline stage."""
        previous = self._transition_dao.get_last_transition(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        stage = None if previous is None else previous.to_stage
        if stage not in {"shortlist", "interview"}:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="invalid_pipeline_stage",
            )

    def _ensure_no_active_interview(self, *, vacancy_id: str, candidate_id: str) -> None:
        """Reject creation when one active interview already exists for the pair."""
        existing = self._interview_dao.find_active_for_pair(vacancy_id=vacancy_id, candidate_id=candidate_id)
        if existing is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="active_interview_already_exists",
            )

    def _get_vacancy_candidate_or_404(self, *, vacancy_id: str, candidate_id: str):
        """Return vacancy and candidate rows or raise 404."""
        vacancy = self._get_vacancy_or_404(vacancy_id)
        candidate = self._get_candidate_or_404(candidate_id)
        return vacancy, candidate

    def _get_vacancy_or_404(self, vacancy_id: str):
        """Load vacancy row or raise standardized 404."""
        vacancy = self._vacancy_dao.get_by_id(vacancy_id)
        if vacancy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="vacancy_not_found")
        return vacancy

    def _get_candidate_or_404(self, candidate_id: str):
        """Load candidate profile row or raise standardized 404."""
        candidate = self._candidate_profile_dao.get_by_id(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="candidate_not_found")
        return candidate

    def _get_interview_for_vacancy_or_404(self, *, vacancy_id: str, interview_id: str) -> Interview:
        """Load interview row scoped to vacancy or raise 404."""
        entity = self._interview_dao.get_by_id(interview_id)
        if entity is None or entity.vacancy_id != vacancy_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="interview_not_found")
        return entity

    def _get_interview_by_token_or_error(self, token: str) -> Interview:
        """Resolve public token to interview row with revoked/expiry checks."""
        token_hash = self._token_manager.hash_token(token)
        entity = self._interview_dao.get_by_token_hash(token_hash)
        if entity is None or entity.candidate_token_expires_at is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="interview_registration_not_found",
            )
        if _ensure_aware_utc(entity.candidate_token_expires_at) <= datetime.now(UTC):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="interview_registration_token_expired",
            )
        return entity

    def _issue_candidate_token(self, entity: Interview) -> None:
        """Issue one candidate token for current schedule version and persist it on interview row."""
        issued = self._token_manager.issue_token(
            interview_id=entity.interview_id,
            schedule_version=entity.schedule_version,
            scheduled_end_at=entity.scheduled_end_at,
        )
        entity.candidate_token_nonce = issued.token_nonce
        entity.candidate_token_hash = issued.token_hash
        entity.candidate_token_expires_at = issued.expires_at

    def _invalidate_candidate_token(self, entity: Interview) -> None:
        """Revoke current candidate token state on interview row."""
        entity.candidate_token_nonce = None
        entity.candidate_token_hash = None
        entity.candidate_token_expires_at = None

    def _build_hr_response(self, *, entity: Interview) -> HRInterviewResponse:
        """Map interview row to HR-facing API response."""
        candidate_invite_url = None
        if entity.candidate_token_nonce and entity.candidate_token_expires_at:
            raw_token = self._token_manager.compose_token(
                interview_id=entity.interview_id,
                schedule_version=entity.schedule_version,
                token_nonce=entity.candidate_token_nonce,
            )
            candidate_invite_url = (
                f"{self._settings.public_frontend_base_url.rstrip('/')}/candidate"
                f"?interviewToken={raw_token}"
            )
        return HRInterviewResponse(
            interview_id=UUID(entity.interview_id),
            vacancy_id=UUID(entity.vacancy_id),
            candidate_id=UUID(entity.candidate_id),
            status=entity.status,  # type: ignore[arg-type]
            calendar_sync_status=entity.calendar_sync_status,  # type: ignore[arg-type]
            schedule_version=entity.schedule_version,
            scheduled_start_at=_ensure_aware_utc(entity.scheduled_start_at),
            scheduled_end_at=_ensure_aware_utc(entity.scheduled_end_at),
            timezone=entity.timezone,
            location_kind=entity.location_kind,  # type: ignore[arg-type]
            location_details=entity.location_details,
            interviewer_staff_ids=[UUID(item) for item in entity.interviewer_staff_ids_json],
            candidate_response_status=entity.candidate_response_status,  # type: ignore[arg-type]
            candidate_response_note=entity.candidate_response_note,
            candidate_token_expires_at=(
                None
                if entity.candidate_token_expires_at is None
                else _ensure_aware_utc(entity.candidate_token_expires_at)
            ),
            candidate_invite_url=candidate_invite_url,
            calendar_event_id=entity.calendar_event_id,
            last_synced_at=None if entity.last_synced_at is None else _ensure_aware_utc(entity.last_synced_at),
            cancelled_by=entity.cancelled_by,  # type: ignore[arg-type]
            cancel_reason_code=entity.cancel_reason_code,
            created_at=_ensure_aware_utc(entity.created_at),
            updated_at=_ensure_aware_utc(entity.updated_at),
        )

    def _build_public_response(
        self,
        *,
        entity: Interview,
        vacancy_title: str,
    ) -> PublicInterviewRegistrationResponse:
        """Map interview row to public candidate-facing payload."""
        return PublicInterviewRegistrationResponse(
            interview_id=UUID(entity.interview_id),
            vacancy_id=UUID(entity.vacancy_id),
            vacancy_title=vacancy_title,
            status=entity.status,  # type: ignore[arg-type]
            calendar_sync_status=entity.calendar_sync_status,  # type: ignore[arg-type]
            schedule_version=entity.schedule_version,
            scheduled_start_at=_ensure_aware_utc(entity.scheduled_start_at),
            scheduled_end_at=_ensure_aware_utc(entity.scheduled_end_at),
            timezone=entity.timezone,
            location_kind=entity.location_kind,  # type: ignore[arg-type]
            location_details=entity.location_details,
            candidate_response_status=entity.candidate_response_status,  # type: ignore[arg-type]
            candidate_response_note=entity.candidate_response_note,
            candidate_token_expires_at=(
                None
                if entity.candidate_token_expires_at is None
                else _ensure_aware_utc(entity.candidate_token_expires_at)
            ),
            cancelled_by=entity.cancelled_by,  # type: ignore[arg-type]
            cancel_reason_code=entity.cancel_reason_code,
            updated_at=_ensure_aware_utc(entity.updated_at),
        )


def _normalize_optional_text(value: str | None) -> str | None:
    """Trim optional text fields and collapse empty strings to null."""
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _ensure_aware_utc(value: datetime) -> datetime:
    """Normalize persisted interview timestamps to aware UTC datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
