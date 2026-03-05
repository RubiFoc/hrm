"""Service for public candidate application flow to vacancies."""

from __future__ import annotations

from json import JSONDecodeError, loads
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, UploadFile, status
from redis.exceptions import RedisError

from hrm_backend.audit.services.audit_service import (
    AuditService,
    get_client_ip,
    get_request_id,
)
from hrm_backend.candidates.infra.celery.dispatch import enqueue_cv_parsing
from hrm_backend.candidates.infra.minio import CandidateStorage
from hrm_backend.candidates.infra.postgres import (
    CandidateDocumentDAO,
    CandidateProfileDAO,
    CVParsingJobDAO,
)
from hrm_backend.candidates.schemas.profile import CandidateCreateRequest, CandidateUpdateRequest
from hrm_backend.candidates.utils.cv import validate_cv_payload
from hrm_backend.core.errors.http import service_unavailable
from hrm_backend.settings import AppSettings
from hrm_backend.vacancies.dao.pipeline_transition_dao import PipelineTransitionDAO
from hrm_backend.vacancies.dao.vacancy_dao import VacancyDAO
from hrm_backend.vacancies.monitoring.public_apply import (
    record_public_apply_blocked,
    record_public_apply_success,
)
from hrm_backend.vacancies.schemas.application import (
    PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION,
    PUBLIC_APPLY_REASON_VALIDATION_FAILED,
    PublicVacancyApplicationResponse,
)
from hrm_backend.vacancies.services.public_apply_exceptions import PublicApplyRejectedError
from hrm_backend.vacancies.services.public_apply_policy import PublicApplyPolicyService
from hrm_backend.vacancies.services.public_apply_rate_limiter import PublicApplyRateLimiter
from hrm_backend.vacancies.utils.pipeline import is_transition_allowed


class VacancyApplicationService:
    """Handles anonymous candidate applications to open vacancies."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        vacancy_dao: VacancyDAO,
        profile_dao: CandidateProfileDAO,
        document_dao: CandidateDocumentDAO,
        parsing_job_dao: CVParsingJobDAO,
        transition_dao: PipelineTransitionDAO,
        storage: CandidateStorage,
        audit_service: AuditService,
        rate_limiter: PublicApplyRateLimiter,
        policy_service: PublicApplyPolicyService,
    ) -> None:
        """Initialize service dependencies."""
        self._settings = settings
        self._vacancy_dao = vacancy_dao
        self._profile_dao = profile_dao
        self._document_dao = document_dao
        self._parsing_job_dao = parsing_job_dao
        self._transition_dao = transition_dao
        self._storage = storage
        self._audit_service = audit_service
        self._rate_limiter = rate_limiter
        self._policy_service = policy_service

    async def apply_public(
        self,
        *,
        vacancy_id: UUID,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        location: str | None,
        current_title: str | None,
        extra_data_raw: str | None,
        file: UploadFile,
        checksum_sha256: str,
        website: str | None,
        request: Request,
    ) -> PublicVacancyApplicationResponse:
        """Create or update candidate profile and apply to vacancy with CV upload."""
        vacancy_id_str = str(vacancy_id)
        normalized_email = email.strip().lower()
        correlation_id = get_request_id(request)
        client_ip = get_client_ip(request)
        try:
            self._rate_limiter.enforce(
                ip=client_ip,
                vacancy_id=vacancy_id_str,
                email=normalized_email,
            )
            self._policy_service.enforce_honeypot(website=website)

            vacancy = self._vacancy_dao.get_by_id(vacancy_id_str)
            if vacancy is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Vacancy not found",
                )

            if vacancy.status.lower() != "open":
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="Vacancy is not open for applications",
                )

            extra_data = self._parse_extra_data(extra_data_raw)
            self._policy_service.enforce_email_cooldown(
                vacancy_id=vacancy_id_str,
                email=normalized_email,
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
            self._policy_service.enforce_checksum_dedup(
                vacancy_id=vacancy_id_str,
                checksum_sha256=validated.checksum_sha256,
            )

            candidate = self._upsert_candidate_profile(
                first_name=first_name,
                last_name=last_name,
                email=normalized_email,
                phone=phone,
                location=location,
                current_title=current_title,
                extra_data=extra_data,
            )
            previous_transition = self._transition_dao.get_last_transition(
                vacancy_id=vacancy_id_str,
                candidate_id=candidate.candidate_id,
            )
            if previous_transition is not None:
                raise PublicApplyRejectedError(
                    reason_code=PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION,
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Candidate already applied to this vacancy",
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

            self._document_dao.deactivate_active_documents(candidate.candidate_id)
            document = self._document_dao.create_document(
                candidate_id=candidate.candidate_id,
                object_key=object_key,
                filename=file.filename or "cv",
                mime_type=validated.mime_type,
                size_bytes=validated.size_bytes,
                checksum_sha256=validated.checksum_sha256,
                is_active=True,
            )
            parsing_job = self._parsing_job_dao.create_queued_job(
                candidate_id=candidate.candidate_id,
                document_id=document.document_id,
            )
            enqueue_cv_parsing(job_id=parsing_job.job_id)

            if not is_transition_allowed(from_stage=None, to_stage="applied"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Canonical transition configuration error",
                )

            transition = self._transition_dao.create_transition(
                vacancy_id=vacancy_id_str,
                candidate_id=candidate.candidate_id,
                from_stage=None,
                to_stage="applied",
                reason="public_application",
                changed_by_sub="public",
                changed_by_role="public",
            )

            self._audit_service.record_api_event(
                action="vacancy:apply_public",
                resource_type="vacancy_application",
                result="success",
                request=request,
                resource_id=transition.transition_id,
            )
            record_public_apply_success(
                correlation_id=correlation_id,
                vacancy_id=vacancy_id_str,
            )
            return PublicVacancyApplicationResponse(
                vacancy_id=vacancy_id,
                candidate_id=UUID(candidate.candidate_id),
                document_id=UUID(document.document_id),
                parsing_job_id=UUID(parsing_job.job_id),
                transition_id=UUID(transition.transition_id),
                applied_at=transition.transitioned_at,
            )
        except RedisError as exc:
            raise service_unavailable(
                "Public application protection is temporarily unavailable"
            ) from exc
        except PublicApplyRejectedError as exc:
            self._audit_service.record_api_event(
                action="vacancy:apply_public",
                resource_type="vacancy_application",
                result="failure",
                request=request,
                reason=exc.reason_code,
            )
            record_public_apply_blocked(
                correlation_id=correlation_id,
                vacancy_id=vacancy_id_str,
                reason_code=exc.reason_code,
                blocked_alert_threshold_per_minute=(
                    self._settings.public_apply_blocked_alert_threshold_per_minute
                ),
            )
            raise
        except HTTPException:
            self._audit_service.record_api_event(
                action="vacancy:apply_public",
                resource_type="vacancy_application",
                result="failure",
                request=request,
                reason=PUBLIC_APPLY_REASON_VALIDATION_FAILED,
            )
            record_public_apply_blocked(
                correlation_id=correlation_id,
                vacancy_id=vacancy_id_str,
                reason_code=PUBLIC_APPLY_REASON_VALIDATION_FAILED,
                blocked_alert_threshold_per_minute=(
                    self._settings.public_apply_blocked_alert_threshold_per_minute
                ),
            )
            raise

    def _upsert_candidate_profile(
        self,
        *,
        first_name: str,
        last_name: str,
        email: str,
        phone: str,
        location: str | None,
        current_title: str | None,
        extra_data: dict[str, object],
    ):
        """Create candidate profile if absent or refresh contact fields by email."""
        existing = self._profile_dao.get_by_email(email)
        if existing is None:
            return self._profile_dao.create_profile(
                payload=CandidateCreateRequest(
                    owner_subject_id="public",
                    first_name=first_name,
                    last_name=last_name,
                    email=email,
                    phone=phone,
                    location=location,
                    current_title=current_title,
                    extra_data=extra_data,
                ),
                owner_subject_id="public",
            )

        return self._profile_dao.update_profile(
            entity=existing,
            payload=CandidateUpdateRequest(
                first_name=first_name,
                last_name=last_name,
                email=email,
                phone=phone,
                location=location,
                current_title=current_title,
                extra_data=extra_data,
            ),
        )

    @staticmethod
    def _parse_extra_data(raw_value: str | None) -> dict[str, object]:
        """Parse optional JSON-formatted extra_data from multipart form field."""
        if raw_value is None or not raw_value.strip():
            return {}
        try:
            parsed = loads(raw_value)
        except JSONDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="extra_data must be a valid JSON object",
            ) from exc

        if not isinstance(parsed, dict):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="extra_data must be a JSON object",
            )
        return parsed
