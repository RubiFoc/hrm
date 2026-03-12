"""Business service for vacancy CRUD and pipeline transitions."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.employee.services.hire_conversion_service import HireConversionService
from hrm_backend.interviews.dao.feedback_dao import InterviewFeedbackDAO
from hrm_backend.interviews.dao.interview_dao import InterviewDAO
from hrm_backend.interviews.utils.feedback import (
    GATE_REASON_MISSING,
    build_feedback_panel_summary,
)
from hrm_backend.vacancies.dao.offer_dao import OfferDAO
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.offer import Offer
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.schemas.pipeline import (
    PipelineStage,
    PipelineTransitionCreateRequest,
    PipelineTransitionListResponse,
    PipelineTransitionResponse,
)
from hrm_backend.vacancies.schemas.vacancy import (
    VacancyCreateRequest,
    VacancyListResponse,
    VacancyResponse,
    VacancyUpdateRequest,
)
from hrm_backend.vacancies.utils.offers import resolve_offer_pipeline_gate
from hrm_backend.vacancies.utils.pipeline import is_transition_allowed


class VacancyService:
    """Orchestrates vacancy and pipeline business workflows."""

    def __init__(
        self,
        *,
        session: Session,
        vacancy_dao: VacancyDAO,
        transition_dao: PipelineTransitionDAO,
        offer_dao: OfferDAO,
        candidate_profile_dao: CandidateProfileDAO,
        interview_dao: InterviewDAO,
        interview_feedback_dao: InterviewFeedbackDAO,
        hire_conversion_service: HireConversionService,
        staff_account_dao: StaffAccountDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize vacancy service dependencies.

        Args:
            session: SQLAlchemy session used to bundle atomic pipeline side effects.
            vacancy_dao: Vacancy DAO.
            transition_dao: Pipeline transition DAO.
            offer_dao: Offer DAO.
            candidate_profile_dao: Candidate profile DAO.
            interview_dao: Interview DAO.
            interview_feedback_dao: Interview feedback DAO.
            hire_conversion_service: Durable employee-domain handoff service.
            staff_account_dao: Staff-account DAO used to resolve assigned-manager labels.
            audit_service: Audit service.
        """
        self._session = session
        self._vacancy_dao = vacancy_dao
        self._transition_dao = transition_dao
        self._offer_dao = offer_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._interview_dao = interview_dao
        self._interview_feedback_dao = interview_feedback_dao
        self._hire_conversion_service = hire_conversion_service
        self._staff_account_dao = staff_account_dao
        self._audit_service = audit_service

    def create_vacancy(
        self,
        *,
        payload: VacancyCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> VacancyResponse:
        """Create vacancy row and emit audit event."""
        entity = self._vacancy_dao.create_vacancy(
            payload,
            hiring_manager_staff_id=self._resolve_hiring_manager_staff_id(
                payload.hiring_manager_login
            ),
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="vacancy:create",
            resource_type="vacancy",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.vacancy_id,
        )
        return self._to_vacancy_response(entity)

    def list_vacancies(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> VacancyListResponse:
        """List vacancies and emit read audit event."""
        items = self._to_vacancy_list_response_items(self._vacancy_dao.list_vacancies())
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="vacancy:read",
            resource_type="vacancy",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return VacancyListResponse(items=items)

    def get_vacancy(
        self,
        *,
        vacancy_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> VacancyResponse:
        """Load one vacancy or raise 404."""
        entity = self._vacancy_dao.get_by_id(str(vacancy_id))
        if entity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="vacancy:read",
            resource_type="vacancy",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.vacancy_id,
        )
        return self._to_vacancy_response(entity)

    def update_vacancy(
        self,
        *,
        vacancy_id: UUID,
        payload: VacancyUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> VacancyResponse:
        """Patch vacancy row and emit audit event."""
        entity = self._vacancy_dao.get_by_id(str(vacancy_id))
        if entity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")
        if "hiring_manager_login" in payload.model_fields_set:
            entity.hiring_manager_staff_id = self._resolve_hiring_manager_staff_id(
                payload.hiring_manager_login
            )
        updated = self._vacancy_dao.update_vacancy(entity=entity, payload=payload)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="vacancy:update",
            resource_type="vacancy",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=updated.vacancy_id,
        )
        return self._to_vacancy_response(updated)

    def _resolve_hiring_manager_staff_id(self, hiring_manager_login: str | None) -> str | None:
        """Resolve optional hiring-manager login to a durable staff-account identifier.

        Args:
            hiring_manager_login: Optional login value submitted on vacancy create/update.

        Returns:
            str | None: Resolved manager staff-account identifier, or `None` when the assignment
                should stay empty.

        Raises:
            HTTPException: If the login does not map to an active manager account.
        """
        if hiring_manager_login is None:
            return None

        normalized_login = hiring_manager_login.strip().lower()
        account = self._staff_account_dao.get_by_login(normalized_login)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="hiring_manager_not_found",
            )
        if account.role != "manager":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="hiring_manager_role_invalid",
            )
        if not account.is_active:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="hiring_manager_inactive",
            )
        return account.staff_id

    def _to_vacancy_list_response_items(self, vacancies: list[Vacancy]) -> list[VacancyResponse]:
        """Map vacancy entities to API responses with resolved manager-login labels."""
        staff_ids = [
            vacancy.hiring_manager_staff_id
            for vacancy in vacancies
            if vacancy.hiring_manager_staff_id is not None
        ]
        accounts = self._staff_account_dao.get_by_ids(staff_ids)
        return [
            _to_vacancy_response(
                vacancy,
                hiring_manager_login=accounts.get(vacancy.hiring_manager_staff_id).login
                if vacancy.hiring_manager_staff_id in accounts
                else None,
            )
            for vacancy in vacancies
        ]

    def _to_vacancy_response(self, vacancy: Vacancy) -> VacancyResponse:
        """Map one vacancy entity to the public response with manager metadata."""
        if vacancy.hiring_manager_staff_id is None:
            return _to_vacancy_response(vacancy, hiring_manager_login=None)

        account = self._staff_account_dao.get_by_id(vacancy.hiring_manager_staff_id)
        return _to_vacancy_response(
            vacancy,
            hiring_manager_login=None if account is None else account.login,
        )

    def transition_pipeline(
        self,
        *,
        payload: PipelineTransitionCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> PipelineTransitionResponse:
        """Append candidate pipeline transition if allowed by canonical matrix."""
        vacancy_id = str(payload.vacancy_id)
        candidate_id = str(payload.candidate_id)

        vacancy = self._vacancy_dao.get_by_id(vacancy_id)
        if vacancy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")

        candidate = self._candidate_profile_dao.get_by_id(candidate_id)
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

        previous = self._transition_dao.get_last_transition(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        from_stage = None if previous is None else previous.to_stage
        if not is_transition_allowed(from_stage=from_stage, to_stage=payload.to_stage):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=(
                    f"Transition from '{from_stage}' to '{payload.to_stage}' is not allowed"
                ),
            )

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        if from_stage == "interview" and payload.to_stage == "offer":
            gate_reason = self._evaluate_offer_feedback_gate(
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
            )
            if gate_reason is not None:
                self._audit_transition_failure(
                    request=request,
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    reason=gate_reason,
                )
                raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=gate_reason)
        if from_stage == "offer" and payload.to_stage in {"hired", "rejected"}:
            offer_gate_reason = self._evaluate_offer_resolution_gate(
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
                to_stage=payload.to_stage,
            )
            if offer_gate_reason is not None:
                self._audit_transition_failure(
                    request=request,
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    vacancy_id=vacancy_id,
                    candidate_id=candidate_id,
                    reason=offer_gate_reason,
                )
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=offer_gate_reason,
                )
        transition = self._persist_transition_bundle(
            vacancy_id=vacancy_id,
            candidate=candidate,
        from_stage=from_stage,
        to_stage=payload.to_stage,
        reason=payload.reason,
        actor_sub=actor_sub,
        actor_role=actor_role,
    )
        self._audit_service.record_api_event(
            action="pipeline:transition",
            resource_type="pipeline",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=transition.transition_id,
        )

        return PipelineTransitionResponse(
            transition_id=UUID(transition.transition_id),
            vacancy_id=UUID(transition.vacancy_id),
            candidate_id=UUID(transition.candidate_id),
            from_stage=transition.from_stage,  # type: ignore[arg-type]
            to_stage=transition.to_stage,  # type: ignore[arg-type]
            reason=transition.reason,
            changed_by_sub=transition.changed_by_sub,
            changed_by_role=transition.changed_by_role,
            transitioned_at=transition.transitioned_at,
        )

    def list_pipeline_transitions(
        self,
        *,
        vacancy_id: UUID,
        candidate_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> PipelineTransitionListResponse:
        """Return ordered pipeline transition history for one candidate on one vacancy."""
        vacancy = self._vacancy_dao.get_by_id(str(vacancy_id))
        if vacancy is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vacancy not found")

        candidate = self._candidate_profile_dao.get_by_id(str(candidate_id))
        if candidate is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")

        items = [
            PipelineTransitionResponse(
                transition_id=UUID(item.transition_id),
                vacancy_id=UUID(item.vacancy_id),
                candidate_id=UUID(item.candidate_id),
                from_stage=item.from_stage,  # type: ignore[arg-type]
                to_stage=item.to_stage,  # type: ignore[arg-type]
                reason=item.reason,
                changed_by_sub=item.changed_by_sub,
                changed_by_role=item.changed_by_role,
                transitioned_at=item.transitioned_at,
            )
            for item in self._transition_dao.list_transitions(
                vacancy_id=str(vacancy_id),
                candidate_id=str(candidate_id),
            )
        ]

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="pipeline:read",
            resource_type="pipeline",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=f"{vacancy_id}:{candidate_id}",
        )
        return PipelineTransitionListResponse(items=items)

    def _evaluate_offer_feedback_gate(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
    ) -> str | None:
        """Return the first fairness-gate blocker for `interview -> offer`, if any."""
        interview = self._interview_dao.find_active_for_pair(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        if interview is None:
            return GATE_REASON_MISSING
        summary = build_feedback_panel_summary(
            interview=interview,
            feedback_history=self._interview_feedback_dao.list_for_interview(
                interview_id=interview.interview_id
            ),
        )
        if summary.gate_status == "passed":
            return None
        return summary.gate_reason_codes[0]

    def _evaluate_offer_resolution_gate(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        to_stage: str,
    ) -> str | None:
        """Return blocker for `offer -> hired/rejected` when lifecycle status is incomplete."""
        offer = self._offer_dao.get_by_pair(vacancy_id=vacancy_id, candidate_id=candidate_id)
        return resolve_offer_pipeline_gate(
            status=None if offer is None else offer.status,
            to_stage=to_stage,
        )

    def _persist_transition_bundle(
        self,
        *,
        vacancy_id: str,
        candidate: CandidateProfile,
        from_stage: PipelineStage | None,
        to_stage: PipelineStage,
        reason: str | None,
        actor_sub: str,
        actor_role: str,
    ) -> PipelineTransition:
        """Persist one pipeline transition with required same-transaction side effects."""
        accepted_offer: Offer | None = None
        if to_stage == "hired":
            accepted_offer = self._offer_dao.get_by_pair(
                vacancy_id=vacancy_id,
                candidate_id=candidate.candidate_id,
            )
            if accepted_offer is None:
                raise RuntimeError("Expected accepted offer before persisting hire conversion")

        try:
            transition = self._transition_dao.create_transition(
                vacancy_id=vacancy_id,
                candidate_id=candidate.candidate_id,
                from_stage=from_stage,
                to_stage=to_stage,  # type: ignore[arg-type]
                reason=reason,
                changed_by_sub=actor_sub,
                changed_by_role=actor_role,
                commit=False,
            )
            if to_stage == "offer":
                self._ensure_offer_exists(
                    vacancy_id=vacancy_id,
                    candidate_id=candidate.candidate_id,
                    commit=False,
                )
            if to_stage == "hired":
                if accepted_offer is None:
                    raise RuntimeError("Expected accepted offer before persisting hire conversion")
                self._hire_conversion_service.create_ready_handoff(
                    candidate=candidate,
                    offer=accepted_offer,
                    hired_transition=transition,
                    converted_by_staff_id=actor_sub,
                    commit=False,
                )
            self._session.commit()
            self._session.refresh(transition)
            return transition
        except Exception:
            self._session.rollback()
            raise

    def _ensure_offer_exists(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        commit: bool = True,
    ) -> None:
        """Create blank draft offer for pairs that have just entered stage `offer`."""
        existing_offer = self._offer_dao.get_by_pair(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
        )
        if existing_offer is not None:
            return
        self._offer_dao.create_offer(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            commit=commit,
        )

    def _audit_transition_failure(
        self,
        *,
        request: Request,
        actor_sub: str,
        actor_role: str,
        vacancy_id: str,
        candidate_id: str,
        reason: str,
    ) -> None:
        """Write stable audit event for blocked pipeline transition attempts."""
        self._audit_service.record_api_event(
            action="pipeline:transition",
            resource_type="pipeline",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=f"{vacancy_id}:{candidate_id}",
            reason=reason,
        )


def _to_vacancy_response(entity: Vacancy, *, hiring_manager_login: str | None) -> VacancyResponse:
    """Map vacancy persistence row to API response.

    Args:
        entity: Vacancy row.
        hiring_manager_login: Optional resolved manager login label.

    Returns:
        VacancyResponse: API payload.
    """
    return VacancyResponse(
        vacancy_id=UUID(entity.vacancy_id),
        title=entity.title,
        description=entity.description,
        department=entity.department,
        status=entity.status,
        hiring_manager_staff_id=(
            None
            if entity.hiring_manager_staff_id is None
            else UUID(entity.hiring_manager_staff_id)
        ),
        hiring_manager_login=hiring_manager_login,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
