"""Business service for vacancy CRUD and pipeline transitions."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.schemas.pipeline import (
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
from hrm_backend.vacancies.utils.pipeline import is_transition_allowed


class VacancyService:
    """Orchestrates vacancy and pipeline business workflows."""

    def __init__(
        self,
        *,
        vacancy_dao: VacancyDAO,
        transition_dao: PipelineTransitionDAO,
        candidate_profile_dao: CandidateProfileDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize vacancy service dependencies.

        Args:
            vacancy_dao: Vacancy DAO.
            transition_dao: Pipeline transition DAO.
            candidate_profile_dao: Candidate profile DAO.
            audit_service: Audit service.
        """
        self._vacancy_dao = vacancy_dao
        self._transition_dao = transition_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._audit_service = audit_service

    def create_vacancy(
        self,
        *,
        payload: VacancyCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> VacancyResponse:
        """Create vacancy row and emit audit event."""
        entity = self._vacancy_dao.create_vacancy(payload)
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
        return _to_vacancy_response(entity)

    def list_vacancies(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> VacancyListResponse:
        """List vacancies and emit read audit event."""
        items = [_to_vacancy_response(item) for item in self._vacancy_dao.list_vacancies()]
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
        return _to_vacancy_response(entity)

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
        return _to_vacancy_response(updated)

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
        transition = self._transition_dao.create_transition(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            from_stage=from_stage,
            to_stage=payload.to_stage,
            reason=payload.reason,
            changed_by_sub=actor_sub,
            changed_by_role=actor_role,
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


def _to_vacancy_response(entity) -> VacancyResponse:
    """Map vacancy persistence row to API response.

    Args:
        entity: Vacancy row.

    Returns:
        VacancyResponse: API payload.
    """
    return VacancyResponse(
        vacancy_id=UUID(entity.vacancy_id),
        title=entity.title,
        description=entity.description,
        department=entity.department,
        status=entity.status,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
