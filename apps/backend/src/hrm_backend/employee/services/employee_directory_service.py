"""Business service for employee directory visibility and avatar operations."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime
from uuid import UUID, uuid4

from fastapi import HTTPException, Request, UploadFile, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.infra.minio import EmployeeAvatarStorage
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.profile import (
    EmployeeAvatarDownloadPayload,
    EmployeeAvatarUploadResponse,
    EmployeeDirectoryListItemResponse,
    EmployeeDirectoryListResponse,
    EmployeeDirectoryProfileResponse,
)
from hrm_backend.settings import AppSettings

EMPLOYEE_PROFILE_NOT_FOUND = "employee_profile_not_found"
EMPLOYEE_PROFILE_IDENTITY_CONFLICT = "employee_profile_identity_conflict"
EMPLOYEE_AVATAR_NOT_FOUND = "employee_avatar_not_found"
EMPLOYEE_AVATAR_EMPTY = "employee_avatar_empty"
EMPLOYEE_AVATAR_INVALID_MIME_TYPE = "employee_avatar_invalid_mime_type"
EMPLOYEE_AVATAR_TOO_LARGE = "employee_avatar_too_large"

_ALLOWED_AVATAR_MIME_TYPES: frozenset[str] = frozenset(
    {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
)
_MAX_AVATAR_SIZE_BYTES = 5 * 1024 * 1024
_AVATAR_FILENAME_BY_MIME: dict[str, str] = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@dataclass(frozen=True)
class _ValidatedAvatarPayload:
    """Validated binary payload accepted for avatar persistence."""

    content: bytes
    mime_type: str
    extension: str


class EmployeeDirectoryService:
    """Expose employee directory reads and self-service avatar updates."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        profile_dao: EmployeeProfileDAO,
        staff_account_dao: StaffAccountDAO,
        avatar_storage: EmployeeAvatarStorage,
        audit_service: AuditService,
    ) -> None:
        """Initialize employee-directory service dependencies.

        Args:
            settings: Application settings for object-storage encryption policy.
            profile_dao: DAO for employee profile reads and updates.
            staff_account_dao: DAO for authenticated staff-account lookups.
            avatar_storage: Object storage adapter for avatar binaries.
            audit_service: Audit service for success/failure traces.
        """
        self._settings = settings
        self._profile_dao = profile_dao
        self._staff_account_dao = staff_account_dao
        self._avatar_storage = avatar_storage
        self._audit_service = audit_service

    def list_directory(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        search: str | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> EmployeeDirectoryListResponse:
        """List employee directory cards visible to authenticated employees.

        Args:
            auth_context: Authenticated actor context.
            request: Active HTTP request.
            search: Optional free-text search query.
            limit: Maximum number of returned rows.
            offset: Number of skipped rows.

        Returns:
            EmployeeDirectoryListResponse: Paginated employee directory payload.
        """
        entities = self._profile_dao.list_directory(
            search=search,
            limit=limit,
            offset=offset,
        )
        total = self._profile_dao.count_directory(search=search)
        self._audit_success(
            action="employee_directory:list",
            resource_type="employee_directory",
            auth_context=auth_context,
            request=request,
            resource_id=None,
        )
        return EmployeeDirectoryListResponse(
            items=[_to_directory_item(entity) for entity in entities],
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_directory_profile(
        self,
        *,
        employee_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeDirectoryProfileResponse:
        """Read detailed employee profile payload from directory scope.

        Args:
            employee_id: Employee profile identifier.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeDirectoryProfileResponse: Detailed profile payload.

        Raises:
            HTTPException: If employee profile does not exist.
        """
        entity = self._profile_dao.get_by_id(str(employee_id))
        if entity is None:
            self._audit_failure(
                action="employee_directory:read",
                resource_type="employee_directory",
                auth_context=auth_context,
                request=request,
                reason=EMPLOYEE_PROFILE_NOT_FOUND,
                resource_id=str(employee_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )

        self._audit_success(
            action="employee_directory:read",
            resource_type="employee_directory",
            auth_context=auth_context,
            request=request,
            resource_id=entity.employee_id,
        )
        item = _to_directory_item(entity)
        return EmployeeDirectoryProfileResponse(
            employee_id=item.employee_id,
            full_name=item.full_name,
            email=item.email,
            phone=item.phone,
            location=item.location,
            position_title=item.position_title,
            department=item.department,
            manager=item.manager,
            subordinates=item.subordinates,
            birthday_day_month=item.birthday_day_month,
            tenure_in_company_months=item.tenure_in_company_months,
            avatar_url=item.avatar_url,
            avatar_updated_at=item.avatar_updated_at,
            is_dismissed=item.is_dismissed,
        )

    async def upload_my_avatar(
        self,
        *,
        file: UploadFile,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarUploadResponse:
        """Upload or replace avatar binary for the authenticated employee profile.

        Args:
            file: Uploaded avatar multipart file.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarUploadResponse: Updated avatar metadata payload.

        Raises:
            HTTPException: If employee profile cannot be resolved or uploaded file is invalid.
        """
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_failure(
                action="employee_avatar:update",
                resource_type="employee_avatar",
                auth_context=auth_context,
                request=request,
                reason=str(exc.detail),
            )
            raise

        payload = await _validate_avatar_payload(file=file)
        object_key = f"employees/{profile.employee_id}/avatars/{uuid4().hex}{payload.extension}"
        self._avatar_storage.put_object(
            object_key=object_key,
            data=payload.content,
            mime_type=payload.mime_type,
            enable_sse=self._settings.object_storage_sse_enabled,
        )

        now = datetime.now(UTC)
        profile.avatar_object_key = object_key
        profile.avatar_mime_type = payload.mime_type
        profile.avatar_updated_at = now
        self._profile_dao.update_profile(entity=profile)

        self._audit_success(
            action="employee_avatar:update",
            resource_type="employee_avatar",
            auth_context=auth_context,
            request=request,
            resource_id=profile.employee_id,
        )
        return EmployeeAvatarUploadResponse(
            employee_id=profile.employee_id,
            avatar_url=_avatar_url(profile),
            avatar_updated_at=now,
        )

    def download_avatar(
        self,
        *,
        employee_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarDownloadPayload:
        """Download one employee avatar by employee identifier.

        Args:
            employee_id: Employee profile identifier.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarDownloadPayload: Binary avatar payload for streaming response.

        Raises:
            HTTPException: If profile or avatar does not exist.
        """
        profile = self._profile_dao.get_by_id(str(employee_id))
        if profile is None:
            self._audit_failure(
                action="employee_avatar:read",
                resource_type="employee_avatar",
                auth_context=auth_context,
                request=request,
                reason=EMPLOYEE_PROFILE_NOT_FOUND,
                resource_id=str(employee_id),
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )
        if not profile.avatar_object_key or not profile.avatar_mime_type:
            self._audit_failure(
                action="employee_avatar:read",
                resource_type="employee_avatar",
                auth_context=auth_context,
                request=request,
                reason=EMPLOYEE_AVATAR_NOT_FOUND,
                resource_id=profile.employee_id,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_AVATAR_NOT_FOUND,
            )

        content = self._avatar_storage.get_object(object_key=profile.avatar_object_key)
        extension = _AVATAR_FILENAME_BY_MIME.get(profile.avatar_mime_type, ".bin")
        filename = f"employee-avatar-{profile.employee_id}{extension}"
        self._audit_success(
            action="employee_avatar:read",
            resource_type="employee_avatar",
            auth_context=auth_context,
            request=request,
            resource_id=profile.employee_id,
        )
        return EmployeeAvatarDownloadPayload(
            filename=filename,
            mime_type=profile.avatar_mime_type,
            content=content,
        )

    def _resolve_profile(self, *, auth_context: AuthContext) -> EmployeeProfile:
        """Resolve employee profile for authenticated employee with durable identity linking.

        Args:
            auth_context: Authenticated actor context.

        Returns:
            EmployeeProfile: Resolved and persisted employee profile entity.

        Raises:
            HTTPException: If no unique employee profile can be resolved.
        """
        subject_id = str(auth_context.subject_id)
        linked = self._profile_dao.get_by_staff_account_id(subject_id)
        if linked is not None:
            return linked

        account = self._staff_account_dao.get_by_id(subject_id)
        if account is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )

        matches = self._profile_dao.list_by_email(account.email)
        if not matches:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )
        if len(matches) > 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMPLOYEE_PROFILE_IDENTITY_CONFLICT,
            )

        profile = matches[0]
        if profile.staff_account_id is not None and profile.staff_account_id != subject_id:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=EMPLOYEE_PROFILE_IDENTITY_CONFLICT,
            )

        profile.staff_account_id = subject_id
        return self._profile_dao.update_profile(entity=profile)

    def _audit_success(
        self,
        *,
        action: str,
        resource_type: str,
        auth_context: AuthContext,
        request: Request,
        resource_id: str | None,
    ) -> None:
        """Record one successful employee-directory or avatar audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type=resource_type,
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
        resource_type: str,
        auth_context: AuthContext,
        request: Request,
        reason: str,
        resource_id: str | None = None,
    ) -> None:
        """Record one failed employee-directory or avatar audit event."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        self._audit_service.record_api_event(
            action=action,
            resource_type=resource_type,
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=resource_id,
            reason=reason,
        )


async def _validate_avatar_payload(*, file: UploadFile) -> _ValidatedAvatarPayload:
    """Validate employee avatar upload payload against MIME and size constraints.

    Args:
        file: Uploaded avatar file.

    Returns:
        _ValidatedAvatarPayload: Validated binary payload.

    Raises:
        HTTPException: If file payload is empty, unsupported, or exceeds technical size limit.
    """
    mime_type = (file.content_type or "").strip().lower()
    if mime_type not in _ALLOWED_AVATAR_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=EMPLOYEE_AVATAR_INVALID_MIME_TYPE,
        )

    content = await file.read()
    if not content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=EMPLOYEE_AVATAR_EMPTY,
        )
    if len(content) > _MAX_AVATAR_SIZE_BYTES:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=EMPLOYEE_AVATAR_TOO_LARGE,
        )

    return _ValidatedAvatarPayload(
        content=content,
        mime_type=mime_type,
        extension=_AVATAR_FILENAME_BY_MIME[mime_type],
    )


def _to_directory_item(entity: EmployeeProfile) -> EmployeeDirectoryListItemResponse:
    """Map one employee profile row to directory-card response payload."""
    extra_data = entity.extra_data_json or {}
    return EmployeeDirectoryListItemResponse(
        employee_id=entity.employee_id,
        full_name=f"{entity.first_name} {entity.last_name}".strip(),
        email=entity.email,
        phone=entity.phone,
        location=entity.location,
        position_title=entity.current_title,
        department=_coerce_string(extra_data.get("department")),
        manager=_coerce_string(extra_data.get("manager")),
        subordinates=_coerce_int(extra_data.get("subordinates")),
        birthday_day_month=_coerce_string(extra_data.get("birthday_day_month")),
        tenure_in_company_months=_compute_tenure_months(entity.start_date),
        avatar_url=_avatar_url(entity),
        avatar_updated_at=entity.avatar_updated_at,
        is_dismissed=entity.is_dismissed,
    )


def _avatar_url(entity: EmployeeProfile) -> str | None:
    """Build canonical API route for employee-avatar reads."""
    if not entity.avatar_object_key:
        return None
    return f"/api/v1/employees/{entity.employee_id}/avatar"


def _coerce_string(value: object) -> str | None:
    """Convert value to a trimmed string or return None when blank/invalid."""
    if not isinstance(value, str):
        return None
    normalized = value.strip()
    if not normalized:
        return None
    return normalized


def _coerce_int(value: object) -> int | None:
    """Convert value to integer or return None when conversion is not safe."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        if normalized.isdigit():
            return int(normalized)
    return None


def _compute_tenure_months(start_date: date | None) -> int | None:
    """Compute non-negative tenure in months from start date to current UTC day."""
    if start_date is None:
        return None
    today = datetime.now(UTC).date()
    months = (today.year - start_date.year) * 12 + (today.month - start_date.month)
    if today.day < start_date.day:
        months -= 1
    return max(months, 0)
