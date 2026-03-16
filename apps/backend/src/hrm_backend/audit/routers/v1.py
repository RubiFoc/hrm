"""Version 1 audit query APIs (admin-only)."""

from __future__ import annotations

from datetime import UTC, datetime
from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse

from hrm_backend.audit.dependencies.audit import get_audit_service
from hrm_backend.audit.dependencies.audit_read import get_audit_read_service
from hrm_backend.audit.schemas.export import AuditEventExportFormat
from hrm_backend.audit.schemas.event import AuditResult, AuditSource
from hrm_backend.audit.schemas.read import AuditEventListResponse
from hrm_backend.audit.services.audit_read_service import AuditReadService
from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.audit.utils.exports import render_audit_events_csv, render_audit_events_jsonl
from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/audit", tags=["audit"])

AuditReadServiceDependency = Annotated[AuditReadService, Depends(get_audit_read_service)]
AuditServiceDependency = Annotated[AuditService, Depends(get_audit_service)]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
AuditReadRole = Annotated[Role, Depends(require_permission("audit:read"))]


@router.get(
    "/events",
    response_model=AuditEventListResponse,
    responses={
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def list_audit_events(
    request: Request,
    _: AuditReadRole,
    auth_context: CurrentAuthContext,
    audit_read_service: AuditReadServiceDependency,
    audit_service: AuditServiceDependency,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    action: Annotated[str | None, Query()] = None,
    result: Annotated[AuditResult | None, Query()] = None,
    source: Annotated[AuditSource | None, Query()] = None,
    resource_type: Annotated[str | None, Query()] = None,
    correlation_id: Annotated[str | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
) -> AuditEventListResponse:
    """List audit events with deterministic filters and pagination."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        response = audit_read_service.list_events(
            limit=limit,
            offset=offset,
            action=action,
            result=result,
            source=source,
            resource_type=resource_type,
            correlation_id=correlation_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
    except HTTPException as exc:
        audit_service.record_api_event(
            action="audit.event:list",
            resource_type="audit_event",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=_extract_reason_code(exc),
        )
        raise

    audit_service.record_api_event(
        action="audit.event:list",
        resource_type="audit_event",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
    )
    return response


@router.get(
    "/events/export",
    responses={
        200: {
            "content": {
                "text/csv": {},
                "application/x-ndjson": {},
            }
        },
        status.HTTP_403_FORBIDDEN: {"description": "RBAC denied"},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Validation failure"},
    },
)
def export_audit_events(
    request: Request,
    _: AuditReadRole,
    auth_context: CurrentAuthContext,
    audit_read_service: AuditReadServiceDependency,
    audit_service: AuditServiceDependency,
    format: AuditEventExportFormat,
    limit: Annotated[int, Query(ge=1, le=10_000)] = 5000,
    offset: Annotated[int, Query(ge=0)] = 0,
    action: Annotated[str | None, Query()] = None,
    result: Annotated[AuditResult | None, Query()] = None,
    source: Annotated[AuditSource | None, Query()] = None,
    resource_type: Annotated[str | None, Query()] = None,
    correlation_id: Annotated[str | None, Query()] = None,
    occurred_from: Annotated[datetime | None, Query()] = None,
    occurred_to: Annotated[datetime | None, Query()] = None,
) -> StreamingResponse:
    """Download audit events as CSV or JSONL attachment."""
    actor_sub, actor_role = actor_from_auth_context(auth_context)
    try:
        items = audit_read_service.export_events(
            limit=limit,
            offset=offset,
            action=action,
            result=result,
            source=source,
            resource_type=resource_type,
            correlation_id=correlation_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        if format == "csv":
            content = render_audit_events_csv(items)
            media_type = "text/csv"
            filename = f"audit-events-{timestamp}.csv"
        else:
            content = render_audit_events_jsonl(items)
            media_type = "application/x-ndjson"
            filename = f"audit-events-{timestamp}.jsonl"
        response = StreamingResponse(BytesIO(content), media_type=media_type)
        response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    except HTTPException as exc:
        audit_service.record_api_event(
            action="audit.event:export",
            resource_type="audit_event",
            result="failure",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            reason=_extract_reason_code(exc),
        )
        raise

    audit_service.record_api_event(
        action="audit.event:export",
        resource_type="audit_event",
        result="success",
        request=request,
        actor_sub=actor_sub,
        actor_role=actor_role,
        reason=format,
    )
    return response


def _extract_reason_code(exc: HTTPException) -> str:
    """Normalize `HTTPException.detail` to audit-friendly reason code."""
    if isinstance(exc.detail, str) and exc.detail.strip():
        return exc.detail.strip()
    return "validation_failed"
