"""Business service for offer lifecycle reads and staff actions."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import (
    AuditService,
    actor_from_auth_context,
    get_request_id,
)
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.schemas.events import (
    OfferStatusChangedEvent,
    OfferStatusChangedPayload,
)
from hrm_backend.automation.services.executor import AutomationActionExecutor
from hrm_backend.automation.utils.identifiers import candidate_id_to_short
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.vacancies.dao.offer_dao import OfferDAO
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.schemas.offer import (
    OfferDecisionRequest,
    OfferResponse,
    OfferStatus,
    OfferUpsertRequest,
)
from hrm_backend.vacancies.utils.offers import (
    OFFER_REASON_NOT_FOUND,
    OFFER_REASON_STAGE_NOT_ACTIVE,
    OFFER_REASON_TERMS_MISSING,
    resolve_offer_action_conflict,
)


class OfferService:
    """Orchestrate offer lifecycle reads and staff-only mutations."""

    def __init__(
        self,
        *,
        vacancy_dao: VacancyDAO,
        candidate_profile_dao: CandidateProfileDAO,
        transition_dao: PipelineTransitionDAO,
        offer_dao: OfferDAO,
        automation_executor: AutomationActionExecutor,
        audit_service: AuditService,
    ) -> None:
        """Initialize offer service dependencies."""
        self._vacancy_dao = vacancy_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._transition_dao = transition_dao
        self._offer_dao = offer_dao
        self._automation_executor = automation_executor
        self._audit_service = audit_service

    def get_offer(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> OfferResponse:
        """Read one offer row and auto-provision a draft when stage `offer` is active."""
        vacancy_key, candidate_key = self._ensure_context(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        entity = self._offer_dao.get_by_pair(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
        )
        if entity is None:
            current_stage = self._get_current_pipeline_stage(
                vacancy_id=vacancy_key,
                candidate_id=candidate_key,
            )
            if current_stage != "offer":
                self._audit_failure(
                    auth_context=auth_context,
                    request=request,
                    vacancy_id=vacancy_key,
                    candidate_id=candidate_key,
                    reason=OFFER_REASON_STAGE_NOT_ACTIVE,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=OFFER_REASON_STAGE_NOT_ACTIVE,
                )
            entity = self._offer_dao.create_offer(
                vacancy_id=vacancy_key,
                candidate_id=candidate_key,
            )
        self._audit_success(
            action="offer:read",
            auth_context=auth_context,
            request=request,
            resource_id=entity.offer_id,
        )
        return _to_offer_response(entity)

    def upsert_offer_draft(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        payload: OfferUpsertRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> OfferResponse:
        """Create or update draft offer fields for the selected pair."""
        vacancy_key, candidate_key = self._ensure_context(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        self._ensure_offer_stage_active(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
            auth_context=auth_context,
            request=request,
        )
        entity = self._offer_dao.get_by_pair(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
        )
        if entity is None:
            entity = self._offer_dao.create_offer(
                vacancy_id=vacancy_key,
                candidate_id=candidate_key,
                terms_summary=payload.terms_summary,
                proposed_start_date=payload.proposed_start_date,
                expires_at=payload.expires_at,
                note=payload.note,
            )
        else:
            conflict_reason = resolve_offer_action_conflict(status=entity.status, action="edit")
            if conflict_reason is not None:
                self._audit_failure(
                    auth_context=auth_context,
                    request=request,
                    vacancy_id=vacancy_key,
                    candidate_id=candidate_key,
                    reason=conflict_reason,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=conflict_reason,
                )
            entity = self._offer_dao.update_offer_draft(
                entity=entity,
                terms_summary=payload.terms_summary,
                proposed_start_date=payload.proposed_start_date,
                expires_at=payload.expires_at,
                note=payload.note,
            )
        self._audit_success(
            action="offer:write",
            auth_context=auth_context,
            request=request,
            resource_id=entity.offer_id,
        )
        return _to_offer_response(entity)

    def send_offer(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> OfferResponse:
        """Move one draft offer to `sent` after validating mutable fields are present."""
        vacancy_key, candidate_key = self._ensure_context(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        self._ensure_offer_stage_active(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
            auth_context=auth_context,
            request=request,
        )
        entity = self._require_offer_or_404(vacancy_id=vacancy_key, candidate_id=candidate_key)
        previous_status = entity.status
        conflict_reason = resolve_offer_action_conflict(status=entity.status, action="send")
        if conflict_reason is not None:
            self._audit_failure(
                auth_context=auth_context,
                request=request,
                vacancy_id=vacancy_key,
                candidate_id=candidate_key,
                reason=conflict_reason,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_reason)
        if entity.terms_summary is None or not entity.terms_summary.strip():
            self._audit_failure(
                auth_context=auth_context,
                request=request,
                vacancy_id=vacancy_key,
                candidate_id=candidate_key,
                reason=OFFER_REASON_TERMS_MISSING,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=OFFER_REASON_TERMS_MISSING,
            )
        actor_sub, _ = actor_from_auth_context(auth_context)
        entity = self._offer_dao.mark_sent(entity=entity, sent_by_staff_id=actor_sub)
        self._evaluate_automation_offer_status_changed(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
            previous_status=previous_status,
            entity=entity,
            auth_context=auth_context,
            correlation_id=get_request_id(request),
        )
        self._audit_success(
            action="offer:send",
            auth_context=auth_context,
            request=request,
            resource_id=entity.offer_id,
        )
        return _to_offer_response(entity)

    def accept_offer(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        payload: OfferDecisionRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> OfferResponse:
        """Record accepted status for one sent offer."""
        return self._record_offer_decision(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            payload=payload,
            auth_context=auth_context,
            request=request,
            action="accept",
            target_status="accepted",
        )

    def decline_offer(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        payload: OfferDecisionRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> OfferResponse:
        """Record declined status for one sent offer."""
        return self._record_offer_decision(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            payload=payload,
            auth_context=auth_context,
            request=request,
            action="decline",
            target_status="declined",
        )

    def _record_offer_decision(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        payload: OfferDecisionRequest,
        auth_context: AuthContext,
        request: Request,
        action: str,
        target_status: OfferStatus,
    ) -> OfferResponse:
        """Record one terminal lifecycle decision for a sent offer."""
        vacancy_key, candidate_key = self._ensure_context(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        self._ensure_offer_stage_active(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
            auth_context=auth_context,
            request=request,
        )
        entity = self._require_offer_or_404(vacancy_id=vacancy_key, candidate_id=candidate_key)
        conflict_reason = resolve_offer_action_conflict(
            status=entity.status,
            action=action,  # type: ignore[arg-type]
        )
        if conflict_reason is not None:
            self._audit_failure(
                auth_context=auth_context,
                request=request,
                vacancy_id=vacancy_key,
                candidate_id=candidate_key,
                reason=conflict_reason,
            )
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=conflict_reason)
        actor_sub, _ = actor_from_auth_context(auth_context)
        previous_status = entity.status
        entity = self._offer_dao.mark_decision(
            entity=entity,
            status=target_status,
            decision_note=payload.note,
            decision_recorded_by_staff_id=actor_sub,
        )
        self._evaluate_automation_offer_status_changed(
            vacancy_id=vacancy_key,
            candidate_id=candidate_key,
            previous_status=previous_status,
            entity=entity,
            auth_context=auth_context,
            correlation_id=get_request_id(request),
        )
        self._audit_success(
            action=f"offer:{target_status}",
            auth_context=auth_context,
            request=request,
            resource_id=entity.offer_id,
        )
        return _to_offer_response(entity)

    def _evaluate_automation_offer_status_changed(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        previous_status: str | None,
        entity: Offer,
        auth_context: AuthContext,
        correlation_id: str | None,
    ) -> None:
        """Evaluate automation rules for one persisted offer status transition (fail-closed)."""
        try:
            vacancy = self._vacancy_dao.get_by_id(vacancy_id)
            if vacancy is None:
                return
            actor_sub, actor_role = actor_from_auth_context(auth_context)
            if entity.decision_at is not None:
                event_time = entity.decision_at
            elif entity.sent_at is not None:
                event_time = entity.sent_at
            else:
                event_time = entity.updated_at

            candidate_uuid = UUID(candidate_id)
            event = OfferStatusChangedEvent(
                event_type="offer.status_changed",
                event_time=event_time,
                trigger_event_id=UUID(entity.offer_id),
                payload=OfferStatusChangedPayload(
                    offer_id=UUID(entity.offer_id),
                    vacancy_id=UUID(vacancy_id),
                    vacancy_title=vacancy.title,
                    candidate_id=candidate_uuid,
                    candidate_id_short=candidate_id_to_short(candidate_uuid),
                    previous_status=previous_status,
                    status=entity.status,
                    offer_status=entity.status,
                    hiring_manager_staff_id=(
                        None
                        if vacancy.hiring_manager_staff_id is None
                        else UUID(vacancy.hiring_manager_staff_id)
                    ),
                    changed_by_staff_id=actor_sub,
                    changed_by_role=actor_role,
                ),
            )
            self._automation_executor.handle_event(event=event, correlation_id=correlation_id)
        except Exception:
            return

    def _ensure_context(self, *, vacancy_id: UUID, candidate_id: UUID) -> tuple[str, str]:
        """Validate vacancy-candidate pair exists before reading or mutating offer data."""
        vacancy_key = str(vacancy_id)
        candidate_key = str(candidate_id)
        if self._vacancy_dao.get_by_id(vacancy_key) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")
        if self._candidate_profile_dao.get_by_id(candidate_key) is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
        return vacancy_key, candidate_key

    def _get_current_pipeline_stage(self, *, vacancy_id: str, candidate_id: str) -> str | None:
        """Read current pipeline stage from append-only transition history."""
        last_transition = self._transition_dao.get_last_transition(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        if last_transition is None:
            return None
        return last_transition.to_stage

    def _ensure_offer_stage_active(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> None:
        """Reject mutations when the pair is not currently inside pipeline stage `offer`."""
        current_stage = self._get_current_pipeline_stage(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        if current_stage == "offer":
            return
        self._audit_failure(
            auth_context=auth_context,
            request=request,
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            reason=OFFER_REASON_STAGE_NOT_ACTIVE,
        )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=OFFER_REASON_STAGE_NOT_ACTIVE,
        )

    def _require_offer_or_404(self, *, vacancy_id: str, candidate_id: str) -> Offer:
        """Load persisted offer row or raise a stable 404 code."""
        entity = self._offer_dao.get_by_pair(vacancy_id=vacancy_id, candidate_id=candidate_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=OFFER_REASON_NOT_FOUND,
            )
        return entity

    def _audit_success(
        self,
        *,
        action: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str,
    ) -> None:
        """Write success audit event for offer lifecycle action."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="offer",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
        )

    def _audit_failure(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        vacancy_id: str,
        candidate_id: str,
        reason: str,
    ) -> None:
        """Write failure audit event for rejected offer lifecycle action."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="offer:lifecycle",
            resource_type="offer",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=f"{vacancy_id}:{candidate_id}",
            reason=reason,
        )


def _to_offer_response(entity: Offer) -> OfferResponse:
    """Map persisted offer row to canonical API response shape."""
    return OfferResponse(
        offer_id=UUID(entity.offer_id),
        vacancy_id=UUID(entity.vacancy_id),
        candidate_id=UUID(entity.candidate_id),
        status=entity.status,  # type: ignore[arg-type]
        terms_summary=entity.terms_summary,
        proposed_start_date=entity.proposed_start_date,
        expires_at=entity.expires_at,
        note=entity.note,
        sent_at=entity.sent_at,
        sent_by_staff_id=UUID(entity.sent_by_staff_id) if entity.sent_by_staff_id else None,
        decision_at=entity.decision_at,
        decision_note=entity.decision_note,
        decision_recorded_by_staff_id=(
            UUID(entity.decision_recorded_by_staff_id)
            if entity.decision_recorded_by_staff_id
            else None
        ),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
