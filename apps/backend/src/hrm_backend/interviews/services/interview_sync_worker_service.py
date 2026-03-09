"""Worker service for asynchronous interview calendar synchronization."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from hrm_backend.audit.services.audit_service import AuditService
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.interviews.dao.calendar_binding_dao import InterviewCalendarBindingDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.infra.google_calendar import InterviewCalendarAdapter
from hrm_backend.interviews.models.interview import Interview
from hrm_backend.interviews.utils.tokens import InterviewTokenManager
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO


@dataclass(frozen=True)
class InterviewSyncWorkerResult:
    """Outcome returned from one worker iteration."""

    status: str
    processed_interview_id: str | None = None
    reason_code: str | None = None


class InterviewSyncWorkerService:
    """Process queued interview sync actions against external calendars."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        interview_dao: InterviewDAO,
        binding_dao: InterviewCalendarBindingDAO,
        vacancy_dao: VacancyDAO,
        candidate_profile_dao: CandidateProfileDAO,
        transition_dao: PipelineTransitionDAO,
        calendar_adapter: InterviewCalendarAdapter,
        token_manager: InterviewTokenManager,
        audit_service: AuditService,
    ) -> None:
        """Initialize worker dependencies."""
        self._settings = settings
        self._interview_dao = interview_dao
        self._binding_dao = binding_dao
        self._vacancy_dao = vacancy_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._transition_dao = transition_dao
        self._calendar_adapter = calendar_adapter
        self._token_manager = token_manager
        self._audit_service = audit_service

    def process_interview_by_id(self, *, interview_id: str) -> InterviewSyncWorkerResult:
        """Claim and process one queued interview sync by interview id."""
        entity = self._interview_dao.claim_by_id(interview_id)
        if entity is None:
            return InterviewSyncWorkerResult(status="idle")
        bindings = self._binding_dao.list_for_interview(entity.interview_id)

        if entity.status == "cancelled":
            return self._process_cancellation(entity=entity, bindings_count=len(bindings))
        return self._process_schedule_sync(entity=entity, bindings_count=len(bindings))

    def _process_schedule_sync(
        self,
        *,
        entity: Interview,
        bindings_count: int,
    ) -> InterviewSyncWorkerResult:
        """Create or update external calendar events for one interview schedule."""
        bindings = self._binding_dao.list_for_interview(entity.interview_id)
        vacancy = self._vacancy_dao.get_by_id(entity.vacancy_id)
        candidate = self._candidate_profile_dao.get_by_id(entity.candidate_id)
        if vacancy is None or candidate is None:
            entity.calendar_sync_status = "failed"
            entity.calendar_sync_reason_code = "interview_sync_reference_missing"
            entity.calendar_sync_error_detail = "Vacancy or candidate row is missing"
            entity.updated_at = datetime.now(UTC)
            self._interview_dao.save(entity)
            self._audit_service.record_background_event(
                action="interview:sync",
                resource_type="interview",
                result="failure",
                correlation_id=entity.interview_id,
                resource_id=entity.interview_id,
                reason="interview_sync_reference_missing",
            )
            return InterviewSyncWorkerResult(
                status="failed",
                processed_interview_id=entity.interview_id,
                reason_code="interview_sync_reference_missing",
            )

        try:
            result = self._calendar_adapter.sync_schedule(
                interview=entity,
                vacancy_title=vacancy.title,
                candidate_display_name=f"{candidate.first_name} {candidate.last_name}".strip(),
                existing_bindings=bindings,
            )
        except Exception as exc:  # noqa: BLE001
            entity.calendar_sync_status = "failed"
            entity.calendar_sync_reason_code = "calendar_sync_failed"
            entity.calendar_sync_error_detail = str(exc)[:2048]
            entity.updated_at = datetime.now(UTC)
            self._interview_dao.save(entity)
            self._audit_service.record_background_event(
                action="interview:sync",
                resource_type="interview",
                result="failure",
                correlation_id=entity.interview_id,
                resource_id=entity.interview_id,
                reason="calendar_sync_failed",
            )
            return InterviewSyncWorkerResult(
                status="failed",
                processed_interview_id=entity.interview_id,
                reason_code="calendar_sync_failed",
            )

        if result.status == "conflict":
            entity.status = "reschedule_requested"
            entity.calendar_sync_status = "conflict"
            entity.calendar_sync_reason_code = result.reason_code
            entity.calendar_sync_error_detail = result.error_detail
            entity.candidate_token_nonce = None
            entity.candidate_token_hash = None
            entity.candidate_token_expires_at = None
            entity.calendar_event_id = None
            entity.last_synced_at = datetime.now(UTC)
            entity.updated_at = datetime.now(UTC)
            self._interview_dao.save(entity)
            self._audit_service.record_background_event(
                action="interview:sync",
                resource_type="interview",
                result="failure",
                correlation_id=entity.interview_id,
                resource_id=entity.interview_id,
                reason=result.reason_code or "calendar_conflict",
            )
            return InterviewSyncWorkerResult(
                status="conflict",
                processed_interview_id=entity.interview_id,
                reason_code=result.reason_code or "calendar_conflict",
            )

        if result.status != "synced":
            entity.calendar_sync_status = "failed"
            entity.calendar_sync_reason_code = result.reason_code or "calendar_sync_failed"
            entity.calendar_sync_error_detail = result.error_detail
            entity.updated_at = datetime.now(UTC)
            self._interview_dao.save(entity)
            self._audit_service.record_background_event(
                action="interview:sync",
                resource_type="interview",
                result="failure",
                correlation_id=entity.interview_id,
                resource_id=entity.interview_id,
                reason=result.reason_code or "calendar_sync_failed",
            )
            return InterviewSyncWorkerResult(
                status="failed",
                processed_interview_id=entity.interview_id,
                reason_code=result.reason_code or "calendar_sync_failed",
            )

        for binding in result.bindings:
            self._binding_dao.upsert_binding(
                interview_id=entity.interview_id,
                interviewer_staff_id=binding.interviewer_staff_id,
                calendar_id=binding.calendar_id,
                calendar_event_id=binding.calendar_event_id,
                schedule_version=entity.schedule_version,
            )

        issued = self._token_manager.issue_token(
            interview_id=entity.interview_id,
            schedule_version=entity.schedule_version,
            scheduled_end_at=entity.scheduled_end_at,
        )
        entity.status = "awaiting_candidate_confirmation"
        entity.calendar_sync_status = "synced"
        entity.calendar_sync_reason_code = None
        entity.calendar_sync_error_detail = None
        entity.calendar_event_id = result.primary_calendar_event_id
        entity.location_details = result.resolved_location_details
        entity.last_synced_at = datetime.now(UTC)
        entity.updated_at = datetime.now(UTC)
        entity.candidate_token_nonce = issued.token_nonce
        entity.candidate_token_hash = issued.token_hash
        entity.candidate_token_expires_at = issued.expires_at
        self._interview_dao.save(entity)
        self._append_pipeline_transition_if_needed(entity)
        self._audit_service.record_background_event(
            action="interview:sync",
            resource_type="interview",
            result="success",
            correlation_id=entity.interview_id,
            resource_id=entity.interview_id,
            reason=f"bindings={bindings_count}->{len(result.bindings)}",
        )
        return InterviewSyncWorkerResult(
            status="synced",
            processed_interview_id=entity.interview_id,
        )

    def _process_cancellation(
        self,
        *,
        entity: Interview,
        bindings_count: int,
    ) -> InterviewSyncWorkerResult:
        """Delete external events after cancellation and clear stored bindings."""
        bindings = self._binding_dao.list_for_interview(entity.interview_id)
        try:
            result = self._calendar_adapter.cancel_schedule(interview=entity, existing_bindings=bindings)
        except Exception as exc:  # noqa: BLE001
            entity.calendar_sync_status = "failed"
            entity.calendar_sync_reason_code = "calendar_sync_failed"
            entity.calendar_sync_error_detail = str(exc)[:2048]
            entity.updated_at = datetime.now(UTC)
            self._interview_dao.save(entity)
            self._audit_service.record_background_event(
                action="interview:sync",
                resource_type="interview",
                result="failure",
                correlation_id=entity.interview_id,
                resource_id=entity.interview_id,
                reason="calendar_sync_failed",
            )
            return InterviewSyncWorkerResult(
                status="failed",
                processed_interview_id=entity.interview_id,
                reason_code="calendar_sync_failed",
            )

        if result.status != "synced":
            entity.calendar_sync_status = "failed"
            entity.calendar_sync_reason_code = result.reason_code or "calendar_sync_failed"
            entity.calendar_sync_error_detail = result.error_detail
            entity.updated_at = datetime.now(UTC)
            self._interview_dao.save(entity)
            self._audit_service.record_background_event(
                action="interview:sync",
                resource_type="interview",
                result="failure",
                correlation_id=entity.interview_id,
                resource_id=entity.interview_id,
                reason=result.reason_code or "calendar_sync_failed",
            )
            return InterviewSyncWorkerResult(
                status="failed",
                processed_interview_id=entity.interview_id,
                reason_code=result.reason_code or "calendar_sync_failed",
            )

        self._binding_dao.delete_all(entity.interview_id)
        entity.calendar_sync_status = "synced"
        entity.calendar_sync_reason_code = None
        entity.calendar_sync_error_detail = None
        entity.calendar_event_id = None
        entity.last_synced_at = datetime.now(UTC)
        entity.updated_at = datetime.now(UTC)
        self._interview_dao.save(entity)
        self._audit_service.record_background_event(
            action="interview:sync",
            resource_type="interview",
            result="success",
            correlation_id=entity.interview_id,
            resource_id=entity.interview_id,
            reason=f"deleted_bindings={bindings_count}",
        )
        return InterviewSyncWorkerResult(
            status="synced",
            processed_interview_id=entity.interview_id,
        )

    def _append_pipeline_transition_if_needed(self, entity: Interview) -> None:
        """Append one shortlist->interview transition on first successful sync when needed."""
        previous = self._transition_dao.get_last_transition(
            vacancy_id=entity.vacancy_id,
            candidate_id=entity.candidate_id,
        )
        current_stage = None if previous is None else previous.to_stage
        if current_stage != "shortlist":
            return
        self._transition_dao.create_transition(
            vacancy_id=entity.vacancy_id,
            candidate_id=entity.candidate_id,
            from_stage="shortlist",
            to_stage="interview",
            reason="interview_sync_success",
            changed_by_sub=entity.updated_by_staff_id,
            changed_by_role="system",
        )
