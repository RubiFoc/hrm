"""Business service for immutable audit event recording."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError

from hrm_backend.audit.dao.audit_event_dao import AuditEventDAO
from hrm_backend.audit.schemas.event import AuditEventCreate, AuditResult
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.core.errors.http import service_unavailable


class AuditService:
    """Service for writing sensitive-operation audit traces."""

    def __init__(self, dao: AuditEventDAO) -> None:
        """Initialize service with DAO dependency.

        Args:
            dao: Audit event DAO.
        """
        self._dao = dao

    def record(self, payload: AuditEventCreate) -> None:
        """Persist one audit event in append-only storage.

        Args:
            payload: Audit payload.

        Raises:
            fastapi.HTTPException: If audit storage is unavailable.
        """
        try:
            self._dao.insert_event(payload)
        except SQLAlchemyError as exc:
            raise service_unavailable("Audit storage temporarily unavailable") from exc

    def record_api_event(
        self,
        *,
        action: str,
        resource_type: str,
        result: AuditResult,
        request: Request,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        resource_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Record API-originated audit event.

        Args:
            action: Sensitive action identifier.
            resource_type: Resource category.
            result: Operation outcome.
            request: Active FastAPI request.
            actor_sub: Actor subject ID if available.
            actor_role: Actor role claim if available.
            resource_id: Optional resource identifier.
            reason: Optional deny/failure reason.
        """
        self.record(
            AuditEventCreate(
                source="api",
                actor_sub=actor_sub,
                actor_role=actor_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=result,
                reason=reason,
                correlation_id=get_request_id(request),
                ip=get_client_ip(request),
                user_agent=request.headers.get("user-agent"),
            )
        )

    def record_background_event(
        self,
        *,
        action: str,
        resource_type: str,
        result: AuditResult,
        correlation_id: str | None,
        actor_sub: str | None = None,
        actor_role: str | None = None,
        resource_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Record background-job audit event.

        Args:
            action: Sensitive action identifier.
            resource_type: Resource category.
            result: Operation outcome.
            correlation_id: Background execution correlation ID.
            actor_sub: Actor subject ID if available.
            actor_role: Actor role claim if available.
            resource_id: Optional resource identifier.
            reason: Optional deny/failure reason.
        """
        self.record(
            AuditEventCreate(
                source="job",
                actor_sub=actor_sub,
                actor_role=actor_role,
                action=action,
                resource_type=resource_type,
                resource_id=resource_id,
                result=result,
                reason=reason,
                correlation_id=correlation_id,
            )
        )

    def record_permission_decision(
        self,
        *,
        permission: str,
        role: str | None,
        allowed: bool,
        request: Request | None = None,
        actor_sub: str | None = None,
        correlation_id: str | None = None,
        reason: str | None = None,
    ) -> None:
        """Record allow/deny decision for RBAC permission checks.

        Args:
            permission: Permission identifier being evaluated.
            role: Actor role claim.
            allowed: Decision outcome.
            request: Optional API request context.
            actor_sub: Optional subject ID.
            correlation_id: Optional correlation ID (used for background jobs).
            reason: Optional explicit deny reason override.
        """
        resource_type = permission.split(":", 1)[0]
        result: AuditResult = "allowed" if allowed else "denied"
        deny_reason = reason
        if deny_reason is None and not allowed:
            deny_reason = f"Role '{role}' has no permission '{permission}'"

        if request is not None:
            self.record_api_event(
                action=permission,
                resource_type=resource_type,
                result=result,
                request=request,
                actor_sub=actor_sub,
                actor_role=role,
                reason=deny_reason,
            )
            return

        self.record_background_event(
            action=permission,
            resource_type=resource_type,
            result=result,
            correlation_id=correlation_id,
            actor_sub=actor_sub,
            actor_role=role,
            reason=deny_reason,
        )


def get_client_ip(request: Request) -> str | None:
    """Extract caller IP address from request context.

    Args:
        request: FastAPI request.

    Returns:
        str | None: Caller IP address if available.
    """
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",", 1)[0].strip()
    if request.client is None:
        return None
    return request.client.host


def get_request_id(request: Request) -> str | None:
    """Read correlation ID from request state or header fallback.

    Args:
        request: FastAPI request.

    Returns:
        str | None: Correlation identifier if available.
    """
    request_id = getattr(request.state, "request_id", None)
    if request_id:
        return str(request_id)
    header_value = request.headers.get("x-request-id")
    return header_value.strip() if header_value else None


def actor_from_auth_context(auth_context: AuthContext) -> tuple[str, str]:
    """Extract audit actor tuple from auth context.

    Args:
        auth_context: Validated auth context.

    Returns:
        tuple[str, str]: Subject ID and role pair.
    """
    return auth_context.subject_id, auth_context.role
