"""Business service for candidate CRUD and CV operations."""

from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO
from hrm_backend.candidates.infra.celery.dispatch import enqueue_cv_parsing
from hrm_backend.candidates.infra.minio import CandidateStorage
from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.parsing_job import CVParsingJob
from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.candidates.schemas.cv import CandidateCVDownloadPayload, CandidateCVUploadResponse
from hrm_backend.candidates.schemas.parsing import CVParsingStatusResponse
from hrm_backend.candidates.schemas.profile import (
    CandidateCreateRequest,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdateRequest,
)
from hrm_backend.candidates.utils.cv import validate_cv_payload
from hrm_backend.settings import AppSettings


@dataclass(frozen=True)
class _CandidateAccess:
    """Access policy decision used inside candidate service methods."""

    allowed: bool
    reason: str | None = None


class CandidateService:
    """Orchestrates candidate profile and CV document workflows."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        profile_dao: CandidateProfileDAO,
        document_dao: CandidateDocumentDAO,
        parsing_job_dao: CVParsingJobDAO,
        storage: CandidateStorage,
        audit_service: AuditService,
    ) -> None:
        """Initialize candidate service dependencies.

        Args:
            settings: Application runtime settings.
            profile_dao: Candidate profile DAO.
            document_dao: Candidate document DAO.
            parsing_job_dao: CV parsing job DAO.
            storage: Object storage adapter.
            audit_service: Audit service for success/failure traces.
        """
        self._settings = settings
        self._profile_dao = profile_dao
        self._document_dao = document_dao
        self._parsing_job_dao = parsing_job_dao
        self._storage = storage
        self._audit_service = audit_service

    def create_profile(
        self,
        *,
        payload: CandidateCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> CandidateResponse:
        """Create candidate profile and emit audit event.

        Args:
            payload: Candidate profile payload.
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CandidateResponse: Created candidate profile payload.
        """
        owner_subject_id = self._resolve_owner(payload.owner_subject_id, auth_context)
        entity = self._profile_dao.create_profile(
            payload=payload,
            owner_subject_id=owner_subject_id,
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_profile:create",
            resource_type="candidate_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.candidate_id,
        )
        return _to_candidate_response(entity)

    def get_profile(
        self,
        *,
        candidate_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> CandidateResponse:
        """Load candidate profile with ownership enforcement.

        Args:
            candidate_id: Candidate identifier.
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CandidateResponse: Candidate profile payload.
        """
        entity = self._get_profile_or_404(candidate_id)
        self._ensure_access(
            profile=entity,
            auth_context=auth_context,
            request=request,
            action="candidate_profile:read",
        )
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_profile:read",
            resource_type="candidate_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.candidate_id,
        )
        return _to_candidate_response(entity)

    def list_profiles(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> CandidateListResponse:
        """List candidate profiles for authorized actors.

        Args:
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CandidateListResponse: Candidate list payload.
        """
        items = [_to_candidate_response(item) for item in self._profile_dao.list_profiles()]
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_profile:list",
            resource_type="candidate_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return CandidateListResponse(items=items)

    def update_profile(
        self,
        *,
        candidate_id: str,
        payload: CandidateUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> CandidateResponse:
        """Patch candidate profile with ownership checks.

        Args:
            candidate_id: Candidate identifier.
            payload: Candidate update payload.
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CandidateResponse: Updated candidate profile payload.
        """
        entity = self._get_profile_or_404(candidate_id)
        self._ensure_access(
            profile=entity,
            auth_context=auth_context,
            request=request,
            action="candidate_profile:update",
        )
        updated = self._profile_dao.update_profile(entity=entity, payload=payload)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_profile:update",
            resource_type="candidate_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=updated.candidate_id,
        )
        return _to_candidate_response(updated)

    async def upload_cv(
        self,
        *,
        candidate_id: str,
        file: UploadFile,
        checksum_sha256: str,
        auth_context: AuthContext,
        request: Request,
    ) -> CandidateCVUploadResponse:
        """Validate, store, and index candidate CV file.

        Args:
            candidate_id: Candidate identifier.
            file: Uploaded multipart file.
            checksum_sha256: Client provided SHA-256 digest.
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CandidateCVUploadResponse: Persisted document metadata.
        """
        entity = self._get_profile_or_404(candidate_id)
        self._ensure_access(
            profile=entity,
            auth_context=auth_context,
            request=request,
            action="candidate_cv:upload",
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

        object_key = f"candidates/{candidate_id}/cv/{uuid4().hex}-{(file.filename or 'cv').strip()}"
        self._storage.put_object(
            object_key=object_key,
            data=validated.content,
            mime_type=validated.mime_type,
            enable_sse=self._settings.object_storage_sse_enabled,
        )

        self._document_dao.deactivate_active_documents(candidate_id)
        doc = self._document_dao.create_document(
            candidate_id=candidate_id,
            object_key=object_key,
            filename=file.filename or "cv",
            mime_type=validated.mime_type,
            size_bytes=validated.size_bytes,
            checksum_sha256=validated.checksum_sha256,
            is_active=True,
        )
        parsing_job = self._parsing_job_dao.create_queued_job(
            candidate_id=candidate_id,
            document_id=doc.document_id,
        )
        enqueue_cv_parsing(job_id=parsing_job.job_id)

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_cv:upload",
            resource_type="candidate_document",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=doc.document_id,
        )

        return CandidateCVUploadResponse(
            document_id=doc.document_id,
            candidate_id=doc.candidate_id,
            filename=doc.filename,
            mime_type=doc.mime_type,
            size_bytes=doc.size_bytes,
            checksum_sha256=doc.checksum_sha256,
            uploaded_at=doc.created_at,
        )

    def download_cv(
        self,
        *,
        candidate_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> CandidateCVDownloadPayload:
        """Download active candidate CV as backend stream payload.

        Args:
            candidate_id: Candidate identifier.
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CandidateCVDownloadPayload: File payload for response streaming.
        """
        entity = self._get_profile_or_404(candidate_id)
        self._ensure_access(
            profile=entity,
            auth_context=auth_context,
            request=request,
            action="candidate_cv:read",
        )
        doc = self._get_active_document_or_404(candidate_id)
        content = self._storage.get_object(object_key=doc.object_key)

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_cv:read",
            resource_type="candidate_document",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=doc.document_id,
        )
        return CandidateCVDownloadPayload(
            filename=doc.filename,
            mime_type=doc.mime_type,
            content=content,
        )

    def get_parsing_status(
        self,
        *,
        candidate_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> CVParsingStatusResponse:
        """Return latest asynchronous CV parsing job status.

        Args:
            candidate_id: Candidate identifier.
            auth_context: Authenticated actor context.
            request: HTTP request context.

        Returns:
            CVParsingStatusResponse: Latest parsing status payload.
        """
        entity = self._get_profile_or_404(candidate_id)
        self._ensure_access(
            profile=entity,
            auth_context=auth_context,
            request=request,
            action="candidate_cv:parsing_status",
        )
        job = self._get_latest_job_or_404(candidate_id)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action="candidate_cv:parsing_status",
            resource_type="candidate_document",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=job.job_id,
        )
        return CVParsingStatusResponse(
            candidate_id=job.candidate_id,
            document_id=job.document_id,
            job_id=job.job_id,
            status=job.status,  # type: ignore[arg-type]
            attempt_count=job.attempt_count,
            last_error=job.last_error,
            queued_at=job.queued_at,
            started_at=job.started_at,
            finished_at=job.finished_at,
            updated_at=job.updated_at,
        )

    def _resolve_owner(self, requested_owner: str | None, auth_context: AuthContext) -> str:
        """Resolve final candidate owner identifier based on actor role.

        Args:
            requested_owner: Owner value from request body.
            auth_context: Authenticated actor context.

        Returns:
            str: Owner subject identifier.
        """
        if auth_context.role == "candidate":
            return str(auth_context.subject_id)
        if requested_owner is not None and requested_owner.strip():
            return requested_owner.strip()
        return str(auth_context.subject_id)

    def _get_profile_or_404(self, candidate_id: str) -> CandidateProfile:
        """Load profile or raise 404.

        Args:
            candidate_id: Candidate identifier.

        Returns:
            CandidateProfile: Loaded profile entity.
        """
        entity = self._profile_dao.get_by_id(candidate_id)
        if entity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Candidate not found")
        return entity

    def _get_active_document_or_404(self, candidate_id: str) -> CandidateDocument:
        """Load active candidate CV row or raise 404.

        Args:
            candidate_id: Candidate identifier.

        Returns:
            CandidateDocument: Active CV metadata row.
        """
        entity = self._document_dao.get_active_document(candidate_id)
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate CV not found",
            )
        return entity

    def _get_latest_job_or_404(self, candidate_id: str) -> CVParsingJob:
        """Load latest parsing job row or raise 404.

        Args:
            candidate_id: Candidate identifier.

        Returns:
            CVParsingJob: Latest parsing job entity.
        """
        job = self._parsing_job_dao.get_latest_by_candidate(candidate_id)
        if job is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV parsing job is not available",
            )
        return job

    def _ensure_access(
        self,
        *,
        profile: CandidateProfile,
        auth_context: AuthContext,
        request: Request,
        action: str,
    ) -> None:
        """Enforce ownership-based access policy for non-HR actors.

        Args:
            profile: Candidate profile entity.
            auth_context: Authenticated actor context.
            request: HTTP request context.
            action: Action identifier for audit event.

        Raises:
            HTTPException: If actor tries to access another candidate.
        """
        access = self._evaluate_access(profile=profile, auth_context=auth_context)
        if access.allowed:
            return

        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type="candidate_profile",
            result="denied",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=profile.candidate_id,
            reason=access.reason,
        )
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=access.reason)

    @staticmethod
    def _evaluate_access(
        *,
        profile: CandidateProfile,
        auth_context: AuthContext,
    ) -> _CandidateAccess:
        """Evaluate candidate ownership access policy.

        Args:
            profile: Candidate profile entity.
            auth_context: Authenticated actor context.

        Returns:
            _CandidateAccess: Allow/deny decision for profile access.
        """
        if auth_context.role in {"admin", "hr"}:
            return _CandidateAccess(allowed=True)
        if str(auth_context.subject_id) == profile.owner_subject_id:
            return _CandidateAccess(allowed=True)
        return _CandidateAccess(
            allowed=False,
            reason="Actor can access only own candidate profile",
        )


def _to_candidate_response(entity: CandidateProfile) -> CandidateResponse:
    """Map persistence model to API response schema.

    Args:
        entity: Candidate profile entity.

    Returns:
        CandidateResponse: API response payload.
    """
    return CandidateResponse(
        candidate_id=entity.candidate_id,
        owner_subject_id=entity.owner_subject_id,
        first_name=entity.first_name,
        last_name=entity.last_name,
        email=entity.email,
        phone=entity.phone,
        location=entity.location,
        current_title=entity.current_title,
        extra_data=entity.extra_data,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
