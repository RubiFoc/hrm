"""Business service for employee directory reads and privacy updates."""

from __future__ import annotations

from datetime import date

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.infra.postgres.staff_account_dao import StaffAccountDAO
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dao.employee_avatar_dao import EmployeeAvatarDAO
from hrm_backend.employee.dao.employee_profile_dao import EmployeeProfileDAO
from hrm_backend.employee.models.avatar import EmployeeProfileAvatar
from hrm_backend.employee.models.profile import EmployeeProfile
from hrm_backend.employee.schemas.profile import (
    EmployeeDirectoryAvatarResponse,
    EmployeeDirectoryListItemResponse,
    EmployeeDirectoryListResponse,
    EmployeeDirectoryProfileResponse,
    EmployeeProfilePrivacySettingsResponse,
    EmployeeProfilePrivacyUpdateRequest,
)

EMPLOYEE_PROFILE_NOT_FOUND = "employee_profile_not_found"
EMPLOYEE_PROFILE_IDENTITY_CONFLICT = "employee_profile_identity_conflict"
EMPLOYEE_PROFILE_DISMISSED = "employee_profile_dismissed"


class EmployeeDirectoryService:
    """Serve employee directory reads and privacy flag updates."""

    def __init__(
        self,
        *,
        profile_dao: EmployeeProfileDAO,
        avatar_dao: EmployeeAvatarDAO,
        staff_account_dao: StaffAccountDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize employee directory service dependencies.

        Args:
            profile_dao: DAO for employee profile reads and updates.
            avatar_dao: DAO for active avatar metadata.
            staff_account_dao: DAO for authenticated staff-account lookups.
            audit_service: Audit service for success/failure traces.
        """
        self._profile_dao = profile_dao
        self._avatar_dao = avatar_dao
        self._staff_account_dao = staff_account_dao
        self._audit_service = audit_service

    def list_directory(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
        limit: int = 20,
        offset: int = 0,
    ) -> EmployeeDirectoryListResponse:
        """List employee directory cards visible to the authenticated actor.

        Args:
            auth_context: Authenticated actor context.
            request: Active HTTP request.
            limit: Maximum number of rows.
            offset: Number of skipped rows after ordering.

        Returns:
            EmployeeDirectoryListResponse: Directory payload with pagination metadata.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        profiles = self._profile_dao.list_directory(limit=limit, offset=offset)
        total = self._profile_dao.count_directory()
        avatars = self._avatar_dao.get_active_avatars_by_employee_ids(
            [profile.employee_id for profile in profiles]
        )
        items = [
            _to_directory_item(
                profile=profile,
                avatar=avatars.get(profile.employee_id),
                actor_subject_id=actor_sub,
            )
            for profile in profiles
        ]
        self._audit_service.record_api_event(
            action="employee_directory:read",
            resource_type="employee_directory",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return EmployeeDirectoryListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_profile(
        self,
        *,
        employee_id: str,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeDirectoryProfileResponse:
        """Load employee directory profile by identifier.

        Args:
            employee_id: Employee profile identifier.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeDirectoryProfileResponse: Directory profile payload.

        Raises:
            HTTPException: If the profile does not exist or is not visible.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        profile = self._profile_dao.get_by_id(employee_id)
        if profile is None:
            self._audit_service.record_api_event(
                action="employee_directory:profile_read",
                resource_type="employee_profile",
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
                action="employee_directory:profile_read",
                resource_type="employee_profile",
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

        avatar = self._avatar_dao.get_active_avatar(profile.employee_id)
        response = _to_directory_item(
            profile=profile,
            avatar=avatar,
            actor_subject_id=actor_sub,
        )
        self._audit_service.record_api_event(
            action="employee_directory:profile_read",
            resource_type="employee_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=employee_id,
        )
        return EmployeeDirectoryProfileResponse(**response.model_dump())

    def get_privacy_settings(
        self,
        *,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeProfilePrivacySettingsResponse:
        """Return current privacy settings for the authenticated employee.

        Args:
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeProfilePrivacySettingsResponse: Current privacy configuration.

        Raises:
            HTTPException: If the employee profile cannot be resolved.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action="employee_profile:privacy_read",
                resource_type="employee_profile",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=str(exc.detail),
            )
            raise

        response = EmployeeProfilePrivacySettingsResponse(
            is_phone_visible=profile.is_phone_visible,
            is_email_visible=profile.is_email_visible,
            is_birthday_visible=profile.is_birthday_visible,
        )
        self._audit_service.record_api_event(
            action="employee_profile:privacy_read",
            resource_type="employee_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=profile.employee_id,
        )
        return response

    def update_privacy_settings(
        self,
        *,
        payload: EmployeeProfilePrivacyUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> EmployeeProfilePrivacySettingsResponse:
        """Update privacy flags for the authenticated employee.

        Args:
            payload: Privacy update payload.
            auth_context: Authenticated actor context.
            request: Active HTTP request.

        Returns:
            EmployeeProfilePrivacySettingsResponse: Updated privacy settings.
        """
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        try:
            profile = self._resolve_profile(auth_context=auth_context)
        except HTTPException as exc:
            self._audit_service.record_api_event(
                action="employee_profile:privacy_update",
                resource_type="employee_profile",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                reason=str(exc.detail),
            )
            raise

        if "is_phone_visible" in payload.model_fields_set:
            profile.is_phone_visible = bool(payload.is_phone_visible)
        if "is_email_visible" in payload.model_fields_set:
            profile.is_email_visible = bool(payload.is_email_visible)
        if "is_birthday_visible" in payload.model_fields_set:
            profile.is_birthday_visible = bool(payload.is_birthday_visible)

        updated = self._profile_dao.update_profile(entity=profile)
        self._audit_service.record_api_event(
            action="employee_profile:privacy_update",
            resource_type="employee_profile",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=updated.employee_id,
        )
        return EmployeeProfilePrivacySettingsResponse(
            is_phone_visible=updated.is_phone_visible,
            is_email_visible=updated.is_email_visible,
            is_birthday_visible=updated.is_birthday_visible,
        )

    def _resolve_profile(self, *, auth_context: AuthContext) -> EmployeeProfile:
        """Resolve employee profile for the authenticated staff subject.

        Args:
            auth_context: Authenticated staff context.

        Returns:
            EmployeeProfile: Resolved and linked employee profile.

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


def _to_directory_item(
    *,
    profile: EmployeeProfile,
    avatar: EmployeeProfileAvatar | None,
    actor_subject_id: str,
) -> EmployeeDirectoryListItemResponse:
    """Map employee profile entity to directory list payload."""
    is_self = profile.staff_account_id == actor_subject_id
    phone_value = profile.phone if is_self or profile.is_phone_visible else None
    email_value = profile.email if is_self or profile.is_email_visible else None
    birthday_value = (
        profile.birthday_day_month if is_self or profile.is_birthday_visible else None
    )
    return EmployeeDirectoryListItemResponse(
        employee_id=profile.employee_id,  # type: ignore[arg-type]
        full_name=f"{profile.first_name} {profile.last_name}".strip(),
        department=profile.department,
        position_title=profile.position_title or profile.current_title,
        manager=profile.manager,
        location=profile.location,
        tenure_in_company=_calculate_tenure_months(profile.start_date),
        subordinates=_resolve_subordinates(profile),
        phone=phone_value,
        email=email_value,
        birthday_day_month=birthday_value,
        avatar=_to_directory_avatar(avatar),
    )


def _to_directory_avatar(
    avatar: EmployeeProfileAvatar | None,
) -> EmployeeDirectoryAvatarResponse | None:
    """Map avatar metadata to directory response."""
    if avatar is None:
        return None
    return EmployeeDirectoryAvatarResponse(
        avatar_id=avatar.avatar_id,  # type: ignore[arg-type]
        mime_type=avatar.mime_type,
        size_bytes=avatar.size_bytes,
        updated_at=avatar.updated_at,
    )


def _calculate_tenure_months(start_date: date | None) -> int | None:
    """Compute tenure in company in full months."""
    if start_date is None:
        return None
    today = date.today()
    months = (today.year - start_date.year) * 12 + (today.month - start_date.month)
    if today.day < start_date.day:
        months -= 1
    return max(months, 0)


def _resolve_subordinates(profile: EmployeeProfile) -> int | None:
    """Extract subordinate count from extensible profile payload when available."""
    raw = profile.extra_data_json.get("subordinates") if profile.extra_data_json else None
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str) and raw.strip().isdigit():
        return int(raw.strip())
    return None
