"""Service layer for employee referral submissions and review flows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, UploadFile, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.schemas.events import (
    PipelineTransitionAppendedEvent,
    PipelineTransitionAppendedPayload,
)
from hrm_backend.automation.services.executor import AutomationActionExecutor
from hrm_backend.automation.utils.identifiers import candidate_id_to_short
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.infra.celery.dispatch import enqueue_cv_parsing
from hrm_backend.candidates.infra.minio.storage import CandidateStorage
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.candidates.schemas.profile import CandidateCreateRequest, CandidateUpdateRequest
from hrm_backend.candidates.utils.cv import validate_cv_payload
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.referrals.dao.referral_dao import EmployeeReferralDAO
from hrm_backend.referrals.models.referral import EmployeeReferral
from hrm_backend.referrals.schemas.referral import (
    ReferralCreate,
    ReferralListItemResponse,
    ReferralListResponse,
    ReferralReviewRequest,
    ReferralReviewResponse,
    ReferralSubmitResponse,
)
from hrm_backend.referrals.utils.referral_utils import (
    normalize_email,
    normalize_full_name,
    normalize_phone,
    split_full_name,
)
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.models.vacancy import Vacancy
from hrm_backend.vacancies.schemas.pipeline import PipelineTransitionResponse
from hrm_backend.vacancies.utils.pipeline import is_transition_allowed

REFERRAL_NOT_FOUND = "referral_not_found"
REFERRAL_DUPLICATE = "referral_duplicate"
REFERRAL_STAGE_NOT_ALLOWED = "referral_stage_not_allowed"
REFERRAL_INVALID_TRANSITION = "referral_invalid_transition"
REFERRAL_ALREADY_IN_STAGE = "referral_already_in_stage"
REFERRAL_CANDIDATE_MISSING = "referral_candidate_missing"
REFERRAL_FORBIDDEN = "referral_forbidden"
REFERRER_PROFILE_NOT_FOUND = "referrer_employee_profile_not_found"
VACANCY_NOT_FOUND = "vacancy_not_found"
VACANCY_NOT_OPEN = "vacancy_not_open"
ALLOWED_REVIEW_STAGES = {"screening", "shortlist"}


class ReferralService:
    """Handle employee referral submissions and review transitions."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        session: Session,
        referral_dao: EmployeeReferralDAO,
        vacancy_dao: VacancyDAO,
        candidate_profile_dao: CandidateProfileDAO,
        candidate_document_dao: CandidateDocumentDAO,
        cv_parsing_job_dao: CVParsingJobDAO,
        transition_dao: PipelineTransitionDAO,
        employee_profile_dao: EmployeeProfileDAO,
        storage: CandidateStorage,
        automation_executor: AutomationActionExecutor,
        audit_service: AuditService,
    ) -> None:
        """Initialize referral service dependencies.

        Args:
            settings: Application settings.
            session: Active SQLAlchemy session for rollback handling.
            referral_dao: Referral DAO.
            vacancy_dao: Vacancy DAO.
            candidate_profile_dao: Candidate profile DAO.
            candidate_document_dao: Candidate document DAO.
            cv_parsing_job_dao: CV parsing job DAO.
            transition_dao: Pipeline transition DAO.
            employee_profile_dao: Employee profile DAO.
            storage: Candidate storage adapter.
            automation_executor: Automation action executor.
            audit_service: Audit service dependency.
        """
        self._settings = settings
        self._session = session
        self._referral_dao = referral_dao
        self._vacancy_dao = vacancy_dao
        self._candidate_profile_dao = candidate_profile_dao
        self._candidate_document_dao = candidate_document_dao
        self._cv_parsing_job_dao = cv_parsing_job_dao
        self._transition_dao = transition_dao
        self._employee_profile_dao = employee_profile_dao
        self._storage = storage
        self._automation_executor = automation_executor
        self._audit_service = audit_service

    async def submit_referral(
        self,
        *,
        vacancy_id: UUID,
        full_name: str,
        phone: str,
        email: str,
        file: UploadFile,
        checksum_sha256: str,
        auth_context: AuthContext,
        request: Request,
    ) -> ReferralSubmitResponse:
        """Submit a new employee referral for a vacancy.

        Args:
            vacancy_id: Target vacancy identifier.
            full_name: Candidate full name.
            phone: Candidate phone number.
            email: Candidate email.
            file: Uploaded CV file.
            checksum_sha256: Client-provided SHA-256 checksum.
            auth_context: Authenticated actor context.
            request: Active API request.

        Returns:
            ReferralSubmitResponse: Referral submission payload.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        referrer = self._resolve_referrer_profile(actor_sub, actor_role, request)
        vacancy = self._resolve_open_vacancy(vacancy_id, actor_sub, actor_role, request)

        normalized_email = normalize_email(email)
        normalized_phone = normalize_phone(phone)
        normalized_full_name = normalize_full_name(full_name)

        existing = self._referral_dao.get_by_vacancy_and_email(
            vacancy_id=str(vacancy_id),
            email=normalized_email,
        )
        if existing is not None:
            response = self._build_submit_response(existing, is_duplicate=True)
            self._audit_service.record_api_event(
                action="referral:submit",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=existing.referral_id,
                reason=REFERRAL_DUPLICATE,
            )
            self._audit_service.record_api_event(
                action="referral:merge",
                resource_type="referral",
                result="success",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=existing.referral_id,
                reason=REFERRAL_DUPLICATE,
            )
            return response

        candidate = self._upsert_candidate_profile(
            full_name=normalized_full_name,
            email=normalized_email,
            phone=normalized_phone,
        )

        payload = await file.read()
        validated = validate_cv_payload(
            filename=file.filename or "cv",
            mime_type=file.content_type or "application/octet-stream",
            content=payload,
            checksum_sha256=checksum_sha256,
            allowed_mime_types=self._settings.cv_allowed_mime_types,
            max_size_bytes=self._settings.cv_max_size_bytes,
        )
        object_key = (
            f"candidates/{candidate.candidate_id}/cv/"
            f"{uuid4().hex}-{(file.filename or 'cv').strip()}"
        )
        self._storage.put_object(
            object_key=object_key,
            data=validated.content,
            mime_type=validated.mime_type,
            enable_sse=self._settings.object_storage_sse_enabled,
        )
        self._candidate_document_dao.deactivate_active_documents(candidate.candidate_id)
        document = self._candidate_document_dao.create_document(
            candidate_id=candidate.candidate_id,
            object_key=object_key,
            filename=file.filename or "cv",
            mime_type=validated.mime_type,
            size_bytes=validated.size_bytes,
            checksum_sha256=validated.checksum_sha256,
            is_active=True,
        )
        parsing_job = self._cv_parsing_job_dao.create_queued_job(
            candidate_id=candidate.candidate_id,
            document_id=document.document_id,
        )
        enqueue_cv_parsing(job_id=parsing_job.job_id)

        transition = self._ensure_applied_transition(
            vacancy=vacancy,
            candidate_id=candidate.candidate_id,
            actor_sub=actor_sub,
            actor_role=actor_role,
            request=request,
        )

        now = datetime.now(UTC)
        try:
            referral = self._referral_dao.create_referral(
                payload=ReferralCreate(
                    vacancy_id=vacancy_id,
                    candidate_id=UUID(candidate.candidate_id),
                    referrer_employee_id=UUID(referrer.employee_id),
                    bonus_owner_employee_id=UUID(referrer.employee_id),
                    full_name=normalized_full_name,
                    phone=normalized_phone,
                    email=normalized_email,
                    cv_document_id=UUID(document.document_id),
                    consent_confirmed_at=now,
                    submitted_at=now,
                )
            )
        except IntegrityError:
            self._session.rollback()
            existing = self._referral_dao.get_by_vacancy_and_email(
                vacancy_id=str(vacancy_id),
                email=normalized_email,
            )
            if existing is not None:
                response = self._build_submit_response(existing, is_duplicate=True)
                self._audit_service.record_api_event(
                    action="referral:submit",
                    resource_type="referral",
                    result="failure",
                    request=request,
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    resource_id=existing.referral_id,
                    reason=REFERRAL_DUPLICATE,
                )
                self._audit_service.record_api_event(
                    action="referral:merge",
                    resource_type="referral",
                    result="success",
                    request=request,
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    resource_id=existing.referral_id,
                    reason=REFERRAL_DUPLICATE,
                )
                return response
            raise

        self._audit_service.record_api_event(
            action="referral:submit",
            resource_type="referral",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=referral.referral_id,
        )
        return ReferralSubmitResponse(
            referral_id=UUID(referral.referral_id),
            vacancy_id=UUID(referral.vacancy_id),
            candidate_id=UUID(referral.candidate_id) if referral.candidate_id else None,
            bonus_owner_employee_id=UUID(referral.bonus_owner_employee_id),
            submitted_at=referral.submitted_at,
            current_stage=transition.to_stage if transition else None,  # type: ignore[arg-type]
            current_stage_at=transition.transitioned_at if transition else None,
            is_duplicate=False,
        )

    def list_referrals(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        vacancy_id: UUID | None,
        limit: int,
        offset: int,
    ) -> ReferralListResponse:
        """List referrals visible to the current actor."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        vacancy_ids = self._resolve_vacancy_scope(
            actor_role=actor_role,
            actor_sub=actor_sub,
            vacancy_id=vacancy_id,
            request=request,
        )
        total = self._referral_dao.count_referrals(vacancy_ids=vacancy_ids)
        items = self._referral_dao.list_referrals(
            vacancy_ids=vacancy_ids,
            limit=limit,
            offset=offset,
        )
        vacancy_map = self._load_vacancies(items)
        candidate_map = self._candidate_profile_dao.get_by_ids(
            [item.candidate_id for item in items if item.candidate_id]
        )
        referrer_map = {
            profile.employee_id: profile
            for profile in self._employee_profile_dao.list_by_ids(
                [item.referrer_employee_id for item in items]
            )
        }
        transitions = self._load_latest_transitions(items)

        response_items: list[ReferralListItemResponse] = []
        for item in items:
            vacancy = vacancy_map.get(item.vacancy_id)
            candidate = candidate_map.get(item.candidate_id) if item.candidate_id else None
            referrer = referrer_map.get(item.referrer_employee_id)
            transition = transitions.get((item.vacancy_id, item.candidate_id or ""))
            response_items.append(
                ReferralListItemResponse(
                    referral_id=UUID(item.referral_id),
                    vacancy_id=UUID(item.vacancy_id),
                    vacancy_title=vacancy.title if vacancy else "",
                    candidate_id=UUID(item.candidate_id) if item.candidate_id else None,
                    candidate_full_name=_resolve_candidate_full_name(item, candidate),
                    candidate_email=(candidate.email if candidate else item.email),
                    candidate_phone=(candidate.phone if candidate else item.phone),
                    referrer_employee_id=UUID(item.referrer_employee_id),
                    referrer_full_name=_resolve_employee_full_name(referrer),
                    bonus_owner_employee_id=UUID(item.bonus_owner_employee_id),
                    submitted_at=item.submitted_at,
                    current_stage=transition.to_stage if transition else None,  # type: ignore[arg-type]
                    current_stage_at=transition.transitioned_at if transition else None,
                )
            )

        self._audit_service.record_api_event(
            action="referral:read",
            resource_type="referral",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return ReferralListResponse(
            items=response_items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def review_referral(
        self,
        *,
        referral_id: UUID,
        payload: ReferralReviewRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> ReferralReviewResponse:
        """Append a review-stage pipeline transition for a referral."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        referral = self._referral_dao.get_by_id(str(referral_id))
        if referral is None:
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(referral_id),
                reason=REFERRAL_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=REFERRAL_NOT_FOUND,
            )

        vacancy = self._vacancy_dao.get_by_id(referral.vacancy_id)
        if vacancy is None:
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=referral.referral_id,
                reason=VACANCY_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=VACANCY_NOT_FOUND,
            )

        if actor_role == "manager" and vacancy.hiring_manager_staff_id != actor_sub:
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=referral.referral_id,
                reason=REFERRAL_FORBIDDEN,
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=REFERRAL_FORBIDDEN,
            )

        if referral.candidate_id is None:
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=referral.referral_id,
                reason=REFERRAL_CANDIDATE_MISSING,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=REFERRAL_CANDIDATE_MISSING,
            )

        if payload.to_stage not in ALLOWED_REVIEW_STAGES:
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=referral.referral_id,
                reason=REFERRAL_STAGE_NOT_ALLOWED,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=REFERRAL_STAGE_NOT_ALLOWED,
            )

        latest = self._transition_dao.get_last_transition(
            vacancy_id=referral.vacancy_id,
            candidate_id=referral.candidate_id,
        )
        current_stage = latest.to_stage if latest else None
        if current_stage == payload.to_stage:
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=referral.referral_id,
                reason=REFERRAL_ALREADY_IN_STAGE,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=REFERRAL_ALREADY_IN_STAGE,
            )

        if not is_transition_allowed(current_stage, payload.to_stage):
            self._audit_service.record_api_event(
                action="referral:review",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=referral.referral_id,
                reason=REFERRAL_INVALID_TRANSITION,
            )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=REFERRAL_INVALID_TRANSITION,
            )

        transition = self._transition_dao.create_transition(
            vacancy_id=referral.vacancy_id,
            candidate_id=referral.candidate_id,
            from_stage=current_stage,
            to_stage=payload.to_stage,
            reason=payload.reason or "referral_review",
            changed_by_sub=actor_sub,
            changed_by_role=actor_role,
        )
        candidate = self._candidate_profile_dao.get_by_id(referral.candidate_id)
        if candidate is not None:
            self._evaluate_automation_pipeline_transition(
                transition=transition,
                vacancy=vacancy,
                candidate=candidate,
                correlation_id=request.headers.get("x-request-id"),
            )

        self._audit_service.record_api_event(
            action="referral:review",
            resource_type="referral",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=referral.referral_id,
        )

        return ReferralReviewResponse(
            referral_id=UUID(referral.referral_id),
            transition=_to_transition_response(transition),
        )

    def _resolve_referrer_profile(
        self,
        actor_sub: str,
        actor_role: str,
        request: Request,
    ) -> EmployeeProfile:
        referrer = self._employee_profile_dao.get_by_staff_account_id(actor_sub)
        if referrer is None:
            self._audit_service.record_api_event(
                action="referral:submit",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=REFERRER_PROFILE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=REFERRER_PROFILE_NOT_FOUND,
            )
        return referrer

    def _resolve_open_vacancy(
        self,
        vacancy_id: UUID,
        actor_sub: str,
        actor_role: str,
        request: Request,
    ) -> Vacancy:
        vacancy = self._vacancy_dao.get_by_id(str(vacancy_id))
        if vacancy is None:
            self._audit_service.record_api_event(
                action="referral:submit",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=VACANCY_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=VACANCY_NOT_FOUND,
            )
        if vacancy.status.lower() != "open":
            self._audit_service.record_api_event(
                action="referral:submit",
                resource_type="referral",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=vacancy.vacancy_id,
                reason=VACANCY_NOT_OPEN,
            )
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail=VACANCY_NOT_OPEN,
            )
        return vacancy

    def _upsert_candidate_profile(
        self,
        *,
        full_name: str,
        email: str,
        phone: str,
    ):
        first_name, last_name = split_full_name(full_name)
        if not first_name or not last_name:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="full_name_invalid",
            )
        existing = self._candidate_profile_dao.get_by_email(email)
        if existing is None:
            return self._candidate_profile_dao.create_profile(
                payload=CandidateCreateRequest(
                    owner_subject_id="public",
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    location=None,
                    current_title=None,
                    extra_data={},
                ),
                owner_subject_id="public",
            )

        return self._candidate_profile_dao.update_profile(
            entity=existing,
            payload=CandidateUpdateRequest(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                location=existing.location,
                current_title=existing.current_title,
                extra_data=existing.extra_data,
            ),
        )

    def _ensure_applied_transition(
        self,
        *,
        vacancy: Vacancy,
        candidate_id: str,
        actor_sub: str,
        actor_role: str,
        request: Request,
    ) -> PipelineTransition | None:
        latest = self._transition_dao.get_last_transition(
            vacancy_id=vacancy.vacancy_id,
            candidate_id=candidate_id,
        )
        if latest is not None:
            return latest
        if not is_transition_allowed(from_stage=None, to_stage="applied"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="canonical_pipeline_transition_invalid",
            )
        transition = self._transition_dao.create_transition(
            vacancy_id=vacancy.vacancy_id,
            candidate_id=candidate_id,
            from_stage=None,
            to_stage="applied",
            reason="employee_referral",
            changed_by_sub=actor_sub,
            changed_by_role=actor_role,
        )
        candidate = self._candidate_profile_dao.get_by_id(candidate_id)
        if candidate is not None:
            self._evaluate_automation_pipeline_transition(
                transition=transition,
                vacancy=vacancy,
                candidate=candidate,
                correlation_id=request.headers.get("x-request-id"),
            )
        return transition

    def _evaluate_automation_pipeline_transition(
        self,
        *,
        transition: PipelineTransition,
        vacancy: Vacancy,
        candidate: CandidateProfile,
        correlation_id: str | None,
    ) -> None:
        """Evaluate automation rules for one persisted pipeline transition."""
        try:
            candidate_uuid = UUID(candidate.candidate_id)
            event = PipelineTransitionAppendedEvent(
                event_type="pipeline.transition_appended",
                event_time=transition.transitioned_at,
                trigger_event_id=UUID(transition.transition_id),
                payload=PipelineTransitionAppendedPayload(
                    transition_id=UUID(transition.transition_id),
                    vacancy_id=UUID(vacancy.vacancy_id),
                    vacancy_title=vacancy.title,
                    candidate_id=candidate_uuid,
                    candidate_id_short=candidate_id_to_short(candidate_uuid),
                    from_stage=transition.from_stage,
                    to_stage=transition.to_stage,
                    stage=transition.to_stage,
                    hiring_manager_staff_id=(
                        None
                        if vacancy.hiring_manager_staff_id is None
                        else UUID(vacancy.hiring_manager_staff_id)
                    ),
                    changed_by_staff_id=transition.changed_by_sub,
                    changed_by_role=transition.changed_by_role,
                ),
            )
            self._automation_executor.handle_event(event=event, correlation_id=correlation_id)
        except Exception:
            return

    def _resolve_vacancy_scope(
        self,
        *,
        actor_role: str,
        actor_sub: str,
        vacancy_id: UUID | None,
        request: Request,
    ) -> list[str] | None:
        if actor_role == "manager":
            vacancies = self._vacancy_dao.list_by_hiring_manager_staff_id(actor_sub)
            vacancy_ids = [vacancy.vacancy_id for vacancy in vacancies]
            if vacancy_id is None:
                return vacancy_ids
            if str(vacancy_id) not in vacancy_ids:
                self._audit_service.record_api_event(
                    action="referral:read",
                    resource_type="referral",
                    result="failure",
                    request=request,
                    actor_sub=actor_sub,
                    actor_role=actor_role,
                    reason=REFERRAL_FORBIDDEN,
                )
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=REFERRAL_FORBIDDEN,
                )
            return [str(vacancy_id)]

        if vacancy_id is None:
            return None
        return [str(vacancy_id)]

    def _load_vacancies(self, items: list[EmployeeReferral]) -> dict[str, Vacancy]:
        vacancy_ids = {item.vacancy_id for item in items}
        if not vacancy_ids:
            return {}
        return {
            vacancy.vacancy_id: vacancy
            for vacancy in self._vacancy_dao.get_by_ids(list(vacancy_ids))
        }

    def _load_latest_transitions(
        self, items: list[EmployeeReferral]
    ) -> dict[tuple[str, str], PipelineTransition]:
        if not items:
            return {}
        transitions: dict[tuple[str, str], PipelineTransition] = {}
        by_vacancy: dict[str, list[str]] = {}
        for item in items:
            if item.candidate_id is None:
                continue
            by_vacancy.setdefault(item.vacancy_id, []).append(item.candidate_id)
        for vacancy_id, candidate_ids in by_vacancy.items():
            latest_transitions = self._transition_dao.get_latest_transitions_by_vacancy(
                vacancy_id=vacancy_id,
                candidate_ids=candidate_ids,
            )
            transitions.update(
                {
                    (vacancy_id, candidate_id): transition
                    for candidate_id, transition in latest_transitions.items()
                }
            )
        return transitions

    def _build_submit_response(
        self,
        referral: EmployeeReferral,
        *,
        is_duplicate: bool,
    ) -> ReferralSubmitResponse:
        transition = None
        if referral.candidate_id:
            transition = self._transition_dao.get_last_transition(
                vacancy_id=referral.vacancy_id,
                candidate_id=referral.candidate_id,
            )
        return ReferralSubmitResponse(
            referral_id=UUID(referral.referral_id),
            vacancy_id=UUID(referral.vacancy_id),
            candidate_id=UUID(referral.candidate_id) if referral.candidate_id else None,
            bonus_owner_employee_id=UUID(referral.bonus_owner_employee_id),
            submitted_at=referral.submitted_at,
            current_stage=transition.to_stage if transition else None,  # type: ignore[arg-type]
            current_stage_at=transition.transitioned_at if transition else None,
            is_duplicate=is_duplicate,
        )


def _to_transition_response(transition: PipelineTransition) -> PipelineTransitionResponse:
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


def _resolve_candidate_full_name(
    referral: EmployeeReferral,
    candidate,
) -> str:
    if candidate is None:
        return referral.full_name
    return f"{candidate.first_name} {candidate.last_name}".strip()


def _resolve_employee_full_name(profile: EmployeeProfile | None) -> str | None:
    if profile is None:
        return None
    return f"{profile.first_name} {profile.last_name}".strip()
