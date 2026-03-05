"""Business service for admin staff governance and key issuance flows."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from fastapi import HTTPException, status

from hrm_backend.admin.dao.employee_registration_key_dao import AdminEmployeeRegistrationKeyDAO
from hrm_backend.admin.dao.staff_account_dao import AdminStaffAccountDAO
from hrm_backend.admin.schemas.responses import (
    AdminEmployeeKeyListItem,
    AdminEmployeeKeyListResponse,
    AdminStaffListItem,
    AdminStaffListResponse,
    EmployeeRegistrationKeyResponse,
    EmployeeRegistrationKeyStatus,
    StaffResponse,
)
from hrm_backend.admin.utils.roles import STAFF_ROLES
from hrm_backend.auth.infra.security.password_service import PasswordService


class AdminService:
    """Orchestrates admin-only staff management and employee-key operations."""

    def __init__(
        self,
        *,
        staff_account_dao: AdminStaffAccountDAO,
        employee_registration_key_dao: AdminEmployeeRegistrationKeyDAO,
        password_service: PasswordService,
    ) -> None:
        """Initialize admin service dependencies.

        Args:
            staff_account_dao: Staff account DAO for admin flows.
            employee_registration_key_dao: Employee key DAO for admin flows.
            password_service: Password hashing adapter.
        """
        self._staff_account_dao = staff_account_dao
        self._employee_registration_key_dao = employee_registration_key_dao
        self._password_service = password_service

    def create_staff_account(
        self,
        *,
        login: str,
        email: str,
        password: str,
        role: str,
        is_active: bool,
    ) -> StaffResponse:
        """Create staff account directly through admin API.

        Args:
            login: Target staff login.
            email: Target staff email.
            password: Target staff raw password.
            role: Target staff role claim.
            is_active: Target active-state flag.

        Returns:
            StaffResponse: Created staff account payload.

        Raises:
            HTTPException: For unsupported role or uniqueness conflicts.
        """
        if role not in STAFF_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Unsupported staff role",
            )

        if self._staff_account_dao.get_by_login(login) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Login already exists")
        if self._staff_account_dao.get_by_email(email) is not None:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already exists")

        password_hash = self._password_service.hash_password(password)
        account = self._staff_account_dao.create_account(
            login=login,
            email=email,
            password_hash=password_hash,
            role=role,
            is_active=is_active,
        )
        return self._to_staff_response(account)

    def list_staff_accounts(
        self,
        *,
        limit: int,
        offset: int,
        search: str | None = None,
        role: str | None = None,
        is_active: bool | None = None,
    ) -> AdminStaffListResponse:
        """List staff accounts with pagination and optional filters.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result.
            search: Optional case-insensitive search term for login/e-mail.
            role: Optional role filter.
            is_active: Optional active-state filter.

        Returns:
            AdminStaffListResponse: Paginated staff list payload.

        Raises:
            HTTPException: If role filter value is unsupported.
        """
        if role is not None and role not in STAFF_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unsupported_role",
            )

        entities = self._staff_account_dao.list_accounts(
            limit=limit,
            offset=offset,
            search=search,
            role=role,
            is_active=is_active,
        )
        total = self._staff_account_dao.count_accounts(
            search=search,
            role=role,
            is_active=is_active,
        )
        items = [
            AdminStaffListItem(
                staff_id=UUID(entity.staff_id),
                login=entity.login,
                email=entity.email,
                role=entity.role,
                is_active=entity.is_active,
                created_at=entity.created_at,
                updated_at=entity.updated_at,
            )
            for entity in entities
        ]
        return AdminStaffListResponse(items=items, total=total, limit=limit, offset=offset)

    def update_staff_account(
        self,
        *,
        staff_id: UUID,
        role: str | None,
        is_active: bool | None,
        actor_subject_id: UUID,
    ) -> StaffResponse:
        """Update role and/or active-state for staff account with strict safety guard.

        Args:
            staff_id: Target staff account identifier.
            role: Optional replacement role.
            is_active: Optional replacement active-state.
            actor_subject_id: Authenticated actor identifier.

        Returns:
            StaffResponse: Updated staff account payload.

        Raises:
            HTTPException: For missing account, unsupported role, empty patch payload,
                forbidden self-modification, or last-admin protection.
        """
        if role is None and is_active is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="empty_patch",
            )
        if role is not None and role not in STAFF_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unsupported_role",
            )

        entity = self._staff_account_dao.get_by_id(str(staff_id))
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="staff_not_found",
            )

        resolved_role = role if role is not None else entity.role
        resolved_is_active = is_active if is_active is not None else entity.is_active
        actor_id = str(actor_subject_id)
        if entity.staff_id == actor_id:
            if entity.role == "admin" and resolved_role != "admin":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="self_modification_forbidden",
                )
            if resolved_is_active is False:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="self_modification_forbidden",
                )

        if entity.role == "admin" and entity.is_active:
            losing_admin_privilege = resolved_role != "admin" or resolved_is_active is False
            if losing_admin_privilege and self._staff_account_dao.count_active_admins() <= 1:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="last_admin_protection",
                )

        updated = self._staff_account_dao.update_account_fields(
            entity=entity,
            role=role,
            is_active=is_active,
        )
        return self._to_staff_response(updated)

    def create_employee_key(
        self,
        *,
        target_role: str,
        created_by_staff_id: UUID,
        ttl_seconds: int,
    ) -> EmployeeRegistrationKeyResponse:
        """Issue one-time employee registration key.

        Args:
            target_role: Role claim that can consume the key.
            created_by_staff_id: Issuer staff identifier.
            ttl_seconds: Key lifetime in seconds.

        Returns:
            EmployeeRegistrationKeyResponse: Issued key payload.

        Raises:
            HTTPException: If target role is unsupported for key issuance.
        """
        if target_role not in STAFF_ROLES or target_role == "admin":
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="Target role is not allowed for employee key",
            )

        key_row = self._employee_registration_key_dao.create_key(
            target_role=target_role,
            created_by_staff_id=str(created_by_staff_id),
            ttl_seconds=ttl_seconds,
        )
        return EmployeeRegistrationKeyResponse(
            key_id=UUID(key_row.key_id),
            employee_key=UUID(key_row.employee_key),
            target_role=key_row.target_role,
            expires_at=key_row.expires_at,
            used_at=key_row.used_at,
            created_by_staff_id=UUID(key_row.created_by_staff_id),
            created_at=key_row.created_at,
        )

    def list_employee_keys(
        self,
        *,
        limit: int,
        offset: int,
        target_role: str | None = None,
        key_status: str | None = None,
        created_by_staff_id: UUID | None = None,
        search: str | None = None,
    ) -> AdminEmployeeKeyListResponse:
        """List employee registration keys with pagination and filters.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result.
            target_role: Optional target-role filter.
            key_status: Optional lifecycle status filter.
            created_by_staff_id: Optional issuer identifier filter.
            search: Optional case-insensitive search for key identifiers.

        Returns:
            AdminEmployeeKeyListResponse: Paginated employee-key list payload.

        Raises:
            HTTPException: If target-role filter is unsupported.
        """
        if target_role is not None and target_role not in STAFF_ROLES:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="unsupported_role",
            )

        entities = self._employee_registration_key_dao.list_keys(
            limit=limit,
            offset=offset,
            target_role=target_role,
            status=key_status,
            created_by_staff_id=str(created_by_staff_id) if created_by_staff_id else None,
            search=search,
        )
        total = self._employee_registration_key_dao.count_keys(
            target_role=target_role,
            status=key_status,
            created_by_staff_id=str(created_by_staff_id) if created_by_staff_id else None,
            search=search,
        )
        items = [self._to_employee_key_list_item(entity) for entity in entities]
        return AdminEmployeeKeyListResponse(items=items, total=total, limit=limit, offset=offset)

    def revoke_employee_key(
        self,
        *,
        key_id: UUID,
        revoked_by_staff_id: UUID,
    ) -> AdminEmployeeKeyListItem:
        """Revoke active employee registration key.

        Args:
            key_id: Target key identifier.
            revoked_by_staff_id: Authenticated actor identifier.

        Returns:
            AdminEmployeeKeyListItem: Revoked key payload.

        Raises:
            HTTPException: For missing key, or when key is already used/expired/revoked.
        """
        now = datetime.now(UTC)
        entity = self._employee_registration_key_dao.get_by_id(str(key_id))
        if entity is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="key_not_found",
            )
        if entity.revoked_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="key_already_revoked",
            )
        if entity.used_at is not None:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="key_already_used",
            )
        if self._is_employee_key_expired(entity.expires_at, now):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="key_already_expired",
            )

        revoked = self._employee_registration_key_dao.revoke_key(
            entity=entity,
            revoked_at=now,
            revoked_by_staff_id=str(revoked_by_staff_id),
        )
        return self._to_employee_key_list_item(revoked)

    @staticmethod
    def _to_staff_response(account) -> StaffResponse:
        """Map staff account entity to API response payload.

        Args:
            account: Persistent staff account row/entity.

        Returns:
            StaffResponse: Serialized staff account payload.
        """
        return StaffResponse(
            staff_id=UUID(account.staff_id),
            login=account.login,
            email=account.email,
            role=account.role,
            is_active=account.is_active,
            created_at=account.created_at,
            updated_at=account.updated_at,
        )

    @staticmethod
    def _to_employee_key_list_item(entity) -> AdminEmployeeKeyListItem:
        """Map employee registration key entity to admin list payload item.

        Args:
            entity: Persistent employee registration key row/entity.

        Returns:
            AdminEmployeeKeyListItem: Serialized key payload with computed status.
        """
        return AdminEmployeeKeyListItem(
            key_id=UUID(entity.key_id),
            employee_key=UUID(entity.employee_key),
            target_role=entity.target_role,
            status=AdminService._resolve_employee_key_status(entity),
            expires_at=entity.expires_at,
            used_at=entity.used_at,
            revoked_at=entity.revoked_at,
            revoked_by_staff_id=UUID(entity.revoked_by_staff_id)
            if entity.revoked_by_staff_id
            else None,
            created_by_staff_id=UUID(entity.created_by_staff_id),
            created_at=entity.created_at,
        )

    @staticmethod
    def _resolve_employee_key_status(entity) -> EmployeeRegistrationKeyStatus:
        """Resolve employee registration key lifecycle status from timestamps.

        Args:
            entity: Persistent employee registration key row/entity.

        Returns:
            EmployeeRegistrationKeyStatus: Computed status string.
        """
        if entity.revoked_at is not None:
            return "revoked"
        if entity.used_at is not None:
            return "used"
        if AdminService._is_employee_key_expired(entity.expires_at):
            return "expired"
        return "active"

    @staticmethod
    def _is_employee_key_expired(expires_at: datetime, now: datetime | None = None) -> bool:
        """Check whether key expiration timestamp is in the past.

        Args:
            expires_at: Key expiration timestamp from storage.
            now: Optional current timestamp override for deterministic checks.

        Returns:
            bool: True when key is expired.
        """
        now_value = now or datetime.now(UTC)
        if expires_at.tzinfo is None:
            now_value = now_value.replace(tzinfo=None)
        return expires_at <= now_value
