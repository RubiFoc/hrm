"""Versioned HTTP routes for recipient-scoped notifications and digests."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.notifications.dependencies.notifications import get_notification_service
from hrm_backend.notifications.schemas.notification import (
    NotificationDigestResponse,
    NotificationListResponse,
    NotificationResponse,
)
from hrm_backend.notifications.services.notification_service import NotificationService
from hrm_backend.notifications.utils.notifications import NotificationListStatus
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])
NotificationServiceDependency = Annotated[
    NotificationService,
    Depends(get_notification_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
NotificationReadRole = Annotated[Role, Depends(require_permission("notification:read"))]
NotificationUpdateRole = Annotated[Role, Depends(require_permission("notification:update"))]
NotificationStatusQuery = Annotated[NotificationListStatus, Query()]
NotificationLimitQuery = Annotated[int, Query(ge=1, le=100)]
NotificationOffsetQuery = Annotated[int, Query(ge=0)]


@router.get("", response_model=NotificationListResponse)
def list_notifications(
    request: Request,
    _: NotificationReadRole,
    auth_context: CurrentAuthContext,
    service: NotificationServiceDependency,
    status: NotificationStatusQuery = "unread",
    limit: NotificationLimitQuery = 20,
    offset: NotificationOffsetQuery = 0,
) -> NotificationListResponse:
    """List notifications that belong to the current authenticated recipient."""
    return service.list_notifications(
        auth_context=auth_context,
        request=request,
        list_status=status,
        limit=limit,
        offset=offset,
    )


@router.get("/digest", response_model=NotificationDigestResponse)
def get_notification_digest(
    request: Request,
    _: NotificationReadRole,
    auth_context: CurrentAuthContext,
    service: NotificationServiceDependency,
) -> NotificationDigestResponse:
    """Return the on-demand notification digest for the current authenticated recipient."""
    return service.get_digest(auth_context=auth_context, request=request)


@router.post("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_read(
    notification_id: UUID,
    request: Request,
    _: NotificationUpdateRole,
    auth_context: CurrentAuthContext,
    service: NotificationServiceDependency,
) -> NotificationResponse:
    """Mark one recipient-owned notification as read."""
    return service.mark_as_read(
        notification_id=notification_id,
        auth_context=auth_context,
        request=request,
    )
