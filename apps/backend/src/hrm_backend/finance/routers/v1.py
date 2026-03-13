"""Versioned HTTP routes for accountant workspace reads and exports."""

from __future__ import annotations

from io import BytesIO
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.finance.dependencies.accounting import get_accounting_workspace_service
from hrm_backend.finance.schemas.workspace import (
    AccountingWorkspaceExportFormat,
    AccountingWorkspaceListResponse,
)
from hrm_backend.finance.services.accounting_workspace_service import (
    AccountingWorkspaceExportPayload,
    AccountingWorkspaceService,
)
from hrm_backend.rbac import Role, require_permission

router = APIRouter(prefix="/api/v1/accounting", tags=["accounting"])
AccountingWorkspaceServiceDependency = Annotated[
    AccountingWorkspaceService,
    Depends(get_accounting_workspace_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
AccountingReadRole = Annotated[Role, Depends(require_permission("accounting:read"))]
WorkspaceSearchQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
WorkspaceLimitQuery = Annotated[int, Query(ge=1, le=100)]
WorkspaceOffsetQuery = Annotated[int, Query(ge=0)]


@router.get("/workspace", response_model=AccountingWorkspaceListResponse)
def get_accounting_workspace(
    request: Request,
    _: AccountingReadRole,
    auth_context: CurrentAuthContext,
    service: AccountingWorkspaceServiceDependency,
    search: WorkspaceSearchQuery = None,
    limit: WorkspaceLimitQuery = 20,
    offset: WorkspaceOffsetQuery = 0,
) -> AccountingWorkspaceListResponse:
    """List accountant-visible onboarding rows for the current actor."""
    return service.list_workspace(
        auth_context=auth_context,
        request=request,
        search=search,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/workspace/export",
    responses={
        200: {
            "content": {
                "text/csv": {},
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {},
            }
        }
    },
)
def export_accounting_workspace(
    request: Request,
    _: AccountingReadRole,
    auth_context: CurrentAuthContext,
    service: AccountingWorkspaceServiceDependency,
    format: AccountingWorkspaceExportFormat,
    search: WorkspaceSearchQuery = None,
):
    """Download accountant-visible workspace rows as CSV or XLSX attachment."""
    payload = service.export_workspace(
        auth_context=auth_context,
        request=request,
        search=search,
        export_format=format,
    )
    return _to_streaming_response(payload)


def _to_streaming_response(payload: AccountingWorkspaceExportPayload) -> StreamingResponse:
    """Convert one export payload into an attachment streaming response."""
    response = StreamingResponse(BytesIO(payload.content), media_type=payload.media_type)
    response.headers["Content-Disposition"] = f'attachment; filename="{payload.filename}"'
    return response
