"""Business service for employee avatar upload, read, and delete operations."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from fastapi import HTTPException, Request, UploadFile, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_avatar_dao import EmployeeAvatarDAO
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.infra.minio import EmployeeAvatarStorage
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.avatar import (
    EmployeeAvatarDeleteResponse,
    EmployeeAvatarDownloadPayload,
    EmployeeAvatarUploadResponse,
)
from hrm_backend.employee.utils.avatar import validate_avatar_payload
from hrm_backend.settings import AppSettings

EMPLOYEE_PROFILE_NOT_FOUND = "employee_profile_not_found"
EMPLOYEE_PROFILE_IDENTITY_CONFLICT = "employee_profile_identity_conflict"
EMPLOYEE_PROFILE_DISMISSED = "employee_profile_dismissed"
EMPLOYEE_AVATAR_NOT_FOUND = "employee_avatar_not_found"


class EmployeeAvatarService:
    """Handle employee avatar upload, read, and delete workflows."""

    def __init__(
        self,
        *,
        settings: AppSettings,
        profile_dao: EmployeeProfileDAO,
        avatar_dao: EmployeeAvatarDAO,
        staff_account_dao: StaffAccountDAO,
        storage: EmployeeAvatarStorage,
        audit_service: AuditService,
    ) -> None:
        """Initialize avatar service dependencies.

        Args:
            settings: Application runtime settings.
            profile_dao: DAO for employee profile reads.
            avatar_dao: DAO for avatar metadata.
            staff_account_dao: DAO for authenticated staff-account lookups.
            storage: Object storage adapter for avatar binaries.
            audit_service: Audit service for success/failure traces.
        """
        self._settings = settings
        self._profile_dao = profile_dao
        self._avatar_dao = avatar_dao
        self._staff_account_dao = staff_account_dao
        self._storage = storage
        self._audit_service = audit_service

    async def upload_my_avatar(
        self,
        *,
        file: UploadFile,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarUploadResponse:
        """Upload avatar for the authenticated employee profile.

        This stores the avatar binary in object storage, updates metadata,
        and records audit events for the operation.

        Args:
            file: Uploaded avatar file from the request body.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarUploadResponse: Uploaded avatar metadata.

        Raises:
            HTTPException: If the profile cannot be resolved or upload validation fails.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action="employee_avatar:upload",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=str(exc.detail),
            )
            raise

        return await self._upload_avatar(
            profile=profile,
            file=file,
            auth_context=auth_context,
            request=request,
            action="employee_avatar:upload",
        )

    async def upload_employee_avatar_admin(
        self,
        *,
        employee_id: str,
        file: UploadFile,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarUploadResponse:
        """Upload avatar for a target employee profile as admin/HR override.

        This stores the avatar binary in object storage, updates metadata,
        and records audit events for the operation.

        Args:
            employee_id: Target employee profile identifier.
            file: Uploaded avatar file from the request body.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarUploadResponse: Uploaded avatar metadata.

        Raises:
            HTTPException: If the target profile is not found or upload fails.
        """
        profile = self._profile_dao.get_by_id(employee_id)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        if profile is None:
            self._audit_service.record_api_event(
                action="employee_avatar:admin_upload",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=employee_id,
                reason=EMPLOYEE_PROFILE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )

        return await self._upload_avatar(
            profile=profile,
            file=file,
            auth_context=auth_context,
            request=request,
            action="employee_avatar:admin_upload",
        )

    def delete_my_avatar(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarDeleteResponse:
        """Delete avatar for the authenticated employee profile.

        This removes the avatar object from storage, updates metadata,
        and records audit events for the operation.

        Args:
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarDeleteResponse: Deletion metadata payload.

        Raises:
            HTTPException: If the profile cannot be resolved or deletion fails.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action="employee_avatar:delete",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=str(exc.detail),
            )
            raise

        return self._delete_avatar(
            profile=profile,
            auth_context=auth_context,
            request=request,
            action="employee_avatar:delete",
        )

    def delete_employee_avatar_admin(
        self,
        *,
        employee_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarDeleteResponse:
        """Delete avatar for target employee profile as admin/HR override.

        This removes the avatar object from storage, updates metadata,
        and records audit events for the operation.

        Args:
            employee_id: Target employee profile identifier.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarDeleteResponse: Deletion metadata payload.

        Raises:
            HTTPException: If the target profile is not found or deletion fails.
        """
        profile = self._profile_dao.get_by_id(employee_id)
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        if profile is None:
            self._audit_service.record_api_event(
                action="employee_avatar:admin_delete",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=employee_id,
                reason=EMPLOYEE_PROFILE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )

        return self._delete_avatar(
            profile=profile,
            auth_context=auth_context,
            request=request,
            action="employee_avatar:admin_delete",
        )

    def read_avatar(
        self,
        *,
        employee_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeAvatarDownloadPayload:
        """Read active avatar for a target employee profile.

        Args:
            employee_id: Target employee profile identifier.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeAvatarDownloadPayload: MIME type and binary avatar content.

        Raises:
            HTTPException: If the profile or avatar cannot be loaded.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        profile = self._profile_dao.get_by_id(employee_id)
        if profile is None:
            self._audit_service.record_api_event(
                action="employee_avatar:read",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=employee_id,
                reason=EMPLOYEE_PROFILE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_NOT_FOUND,
            )
        if profile.is_dismissed:
            self._audit_service.record_api_event(
                action="employee_avatar:read",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=employee_id,
                reason=EMPLOYEE_PROFILE_DISMISSED,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_PROFILE_DISMISSED,
            )

        avatar = self._avatar_dao.get_active_avatar(employee_id)
        if avatar is None:
            self._audit_service.record_api_event(
                action="employee_avatar:read",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=employee_id,
                reason=EMPLOYEE_AVATAR_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_AVATAR_NOT_FOUND,
            )

        try:
            content = self._storage.get_object(object_key=avatar.object_key)
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action="employee_avatar:read",
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=avatar.avatar_id,
                reason=str(exc.detail),
            )
            raise
        self._audit_service.record_api_event(
            action="employee_avatar:read",
            resource_type="employee_avatar",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=avatar.avatar_id,
        )
        return EmployeeAvatarDownloadPayload(
            mime_type=avatar.mime_type,
            content=content,
        )

    async def _upload_avatar(
        self,
        *,
        profile: EmployeeProfile,
        file: UploadFile,
        auth_context: AuthContext,
        request: Request,
        action: str,
    ) -> EmployeeAvatarUploadResponse:
        """Upload avatar binary and persist metadata.

        Args:
            profile: Target employee profile entity.
            file: Uploaded avatar file.
            auth_context: Authenticated actor context.
            request: Active HTTP request.
            action: Audit action label.

        Returns:
            EmployeeAvatarUploadResponse: Uploaded avatar metadata.

        Raises:
            HTTPException: If validation or storage operations fail.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        payload = await file.read()
        try:
            validated = validate_avatar_payload(
                filename=file.filename or "",
                mime_type=file.content_type or "application/octet-stream",
                content=payload,
            )
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action=action,
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=profile.employee_id,
                reason=str(exc.detail),
            )
            raise

        object_key = (
            f"employees/{profile.employee_id}/avatar/{uuid4().hex}-{validated.filename}"
        )
        try:
            self._storage.put_object(
                object_key=object_key,
                data=validated.content,
                mime_type=validated.mime_type,
                enable_sse=self._settings.object_storage_sse_enabled,
            )
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action=action,
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=profile.employee_id,
                reason=str(exc.detail),
            )
            raise

        self._avatar_dao.deactivate_active_avatars(profile.employee_id, commit=False)
        avatar = self._avatar_dao.create_avatar(
            employee_id=profile.employee_id,
            object_key=object_key,
            mime_type=validated.mime_type,
            size_bytes=validated.size_bytes,
            is_active=True,
            commit=False,
        )
        self._avatar_dao.update_avatar(entity=avatar)

        self._audit_service.record_api_event(
            action=action,
            resource_type="employee_avatar",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=avatar.avatar_id,
        )
        return EmployeeAvatarUploadResponse(
            avatar_id=avatar.avatar_id,  # type: ignore[arg-type]
            employee_id=profile.employee_id,  # type: ignore[arg-type]
            mime_type=avatar.mime_type,
            size_bytes=avatar.size_bytes,
            updated_at=avatar.updated_at,
        )

    def _delete_avatar(
        self,
        *,
        profile: EmployeeProfile,
        auth_context: AuthContext,
        request: Request,
        action: str,
    ) -> EmployeeAvatarDeleteResponse:
        """Delete active avatar metadata and object.

        Args:
            profile: Target employee profile entity.
            auth_context: Authenticated actor context.
            request: Active HTTP request.
            action: Audit action label.

        Returns:
            EmployeeAvatarDeleteResponse: Deletion metadata payload.

        Raises:
            HTTPException: If the avatar cannot be deleted.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        avatar = self._avatar_dao.get_active_avatar(profile.employee_id)
        if avatar is None:
            self._audit_service.record_api_event(
                action=action,
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=profile.employee_id,
                reason=EMPLOYEE_AVATAR_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=EMPLOYEE_AVATAR_NOT_FOUND,
            )

        try:
            self._storage.remove_object(object_key=avatar.object_key)
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action=action,
                resource_type="employee_avatar",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=avatar.avatar_id,
                reason=str(exc.detail),
            )
            raise
        avatar.is_active = False
        avatar.updated_at = datetime.now(UTC)
        self._avatar_dao.update_avatar(entity=avatar)

        self._audit_service.record_api_event(
            action=action,
            resource_type="employee_avatar",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=avatar.avatar_id,
        )
        return EmployeeAvatarDeleteResponse(
            employee_id=profile.employee_id,  # type: ignore[arg-type]
            deleted_at=avatar.updated_at,
        )

    def _resolve_profile(self, *, auth_context: AuthContext) -> EmployeeProfile:
        """Resolve employee profile for the authenticated staff subject.

        Args:
            auth_context: Authenticated staff context.

        Returns:
            EmployeeProfile: Resolved and linked employee profile.

        Raises:
            HTTPException: If the profile cannot be uniquely resolved.
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
