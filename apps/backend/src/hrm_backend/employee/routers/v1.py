"""Versioned HTTP routes for employee profile and onboarding staff workflows."""

from __future__ import annotations

from io import BytesIO
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Query, Request, UploadFile
from fastapi.responses import StreamingResponse

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.employee.dependencies.employee import (
    get_employee_directory_service,
    get_employee_onboarding_portal_service,
    get_employee_profile_service,
    get_onboarding_dashboard_service,
    get_onboarding_task_service,
    get_onboarding_template_service,
)
from hrm_backend.employee.schemas.onboarding import (
    EmployeeOnboardingPortalResponse,
    EmployeeOnboardingTaskResponse,
    EmployeeOnboardingTaskUpdateRequest,
    OnboardingDashboardDetailResponse,
    OnboardingDashboardListResponse,
    OnboardingTaskListResponse,
    OnboardingTaskResponse,
    OnboardingTaskStatus,
    OnboardingTaskUpdateRequest,
)
from hrm_backend.employee.schemas.profile import (
    EmployeeAvatarUploadResponse,
    EmployeeDirectoryListResponse,
    EmployeeDirectoryProfileResponse,
    EmployeeProfileCreateRequest,
    EmployeeProfileResponse,
)
from hrm_backend.employee.schemas.template import (
    OnboardingChecklistTemplateCreateRequest,
    OnboardingChecklistTemplateListResponse,
    OnboardingChecklistTemplateResponse,
    OnboardingChecklistTemplateUpdateRequest,
)
from hrm_backend.employee.services.employee_directory_service import EmployeeDirectoryService
from hrm_backend.employee.services.employee_onboarding_portal_service import (
    EmployeeOnboardingPortalService,
)
from hrm_backend.employee.services.employee_profile_service import EmployeeProfileService
from hrm_backend.employee.services.onboarding_dashboard_service import (
    OnboardingDashboardService,
)
from hrm_backend.employee.services.onboarding_task_service import OnboardingTaskService
from hrm_backend.employee.services.onboarding_template_service import OnboardingTemplateService
from hrm_backend.rbac import Role, require_permission

router = APIRouter()
employee_router = APIRouter(prefix="/api/v1/employees", tags=["employees"])
onboarding_task_router = APIRouter(prefix="/api/v1/onboarding/runs", tags=["onboarding"])
onboarding_template_router = APIRouter(
    prefix="/api/v1/onboarding/templates",
    tags=["onboarding"],
)
EmployeeProfileServiceDependency = Annotated[
    EmployeeProfileService,
    Depends(get_employee_profile_service),
]
EmployeeOnboardingPortalServiceDependency = Annotated[
    EmployeeOnboardingPortalService,
    Depends(get_employee_onboarding_portal_service),
]
EmployeeDirectoryServiceDependency = Annotated[
    EmployeeDirectoryService,
    Depends(get_employee_directory_service),
]
OnboardingDashboardServiceDependency = Annotated[
    OnboardingDashboardService,
    Depends(get_onboarding_dashboard_service),
]
OnboardingTemplateServiceDependency = Annotated[
    OnboardingTemplateService,
    Depends(get_onboarding_template_service),
]
OnboardingTaskServiceDependency = Annotated[
    OnboardingTaskService,
    Depends(get_onboarding_task_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]
DashboardSearchQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
DashboardTaskStatusQuery = Annotated[OnboardingTaskStatus | None, Query()]
DashboardAssignedRoleQuery = Annotated[Role | None, Query()]
DashboardAssignedStaffQuery = Annotated[UUID | None, Query()]
DashboardOverdueOnlyQuery = Annotated[bool, Query()]
DashboardLimitQuery = Annotated[int, Query(ge=1, le=100)]
DashboardOffsetQuery = Annotated[int, Query(ge=0)]
DirectorySearchQuery = Annotated[str | None, Query(min_length=1, max_length=256)]
DirectoryLimitQuery = Annotated[int, Query(ge=1, le=100)]
DirectoryOffsetQuery = Annotated[int, Query(ge=0)]
EmployeeProfileCreateRole = Annotated[Role, Depends(require_permission("employee_profile:create"))]
EmployeeProfileReadRole = Annotated[Role, Depends(require_permission("employee_profile:read"))]
EmployeePortalReadRole = Annotated[
    Role,
    Depends(require_permission("employee_portal:read")),
]
EmployeePortalUpdateRole = Annotated[
    Role,
    Depends(require_permission("employee_portal:update")),
]
OnboardingDashboardReadRole = Annotated[
    Role,
    Depends(require_permission("onboarding_dashboard:read")),
]
OnboardingTaskListRole = Annotated[
    Role,
    Depends(require_permission("onboarding_task:list")),
]
OnboardingTaskUpdateRole = Annotated[
    Role,
    Depends(require_permission("onboarding_task:update")),
]
OnboardingTaskBackfillRole = Annotated[
    Role,
    Depends(require_permission("onboarding_task:backfill")),
]
OnboardingTemplateCreateRole = Annotated[
    Role,
    Depends(require_permission("onboarding_template:create")),
]
OnboardingTemplateListRole = Annotated[
    Role,
    Depends(require_permission("onboarding_template:list")),
]
OnboardingTemplateReadRole = Annotated[
    Role,
    Depends(require_permission("onboarding_template:read")),
]
OnboardingTemplateUpdateRole = Annotated[
    Role,
    Depends(require_permission("onboarding_template:update")),
]


@employee_router.post("", response_model=EmployeeProfileResponse)
def create_employee_profile(
    request: Request,
    payload: EmployeeProfileCreateRequest,
    _: EmployeeProfileCreateRole,
    auth_context: CurrentAuthContext,
    service: EmployeeProfileServiceDependency,
) -> EmployeeProfileResponse:
    """Create one employee profile from a persisted hire conversion."""
    return service.create_profile(payload=payload, auth_context=auth_context, request=request)


@employee_router.get("/directory", response_model=EmployeeDirectoryListResponse)
def list_employee_directory(
    request: Request,
    _: EmployeePortalReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
    search: DirectorySearchQuery = None,
    limit: DirectoryLimitQuery = 20,
    offset: DirectoryOffsetQuery = 0,
) -> EmployeeDirectoryListResponse:
    """List cross-employee profile cards for authenticated employee actors."""
    return service.list_directory(
        auth_context=auth_context,
        request=request,
        search=search,
        limit=limit,
        offset=offset,
    )


@employee_router.get(
    "/directory/{employee_id}",
    response_model=EmployeeDirectoryProfileResponse,
)
def get_employee_directory_profile(
    employee_id: UUID,
    request: Request,
    _: EmployeePortalReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
) -> EmployeeDirectoryProfileResponse:
    """Read one detailed employee profile from directory scope."""
    return service.get_directory_profile(
        employee_id=employee_id,
        auth_context=auth_context,
        request=request,
    )


@employee_router.post(
    "/me/avatar",
    response_model=EmployeeAvatarUploadResponse,
)
async def upload_my_employee_avatar(
    request: Request,
    file: Annotated[UploadFile, File(...)],
    _: EmployeePortalUpdateRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
) -> EmployeeAvatarUploadResponse:
    """Upload or replace avatar binary for authenticated employee profile."""
    return await service.upload_my_avatar(
        file=file,
        auth_context=auth_context,
        request=request,
    )


@employee_router.get("/{employee_id}/avatar")
def download_employee_avatar(
    employee_id: UUID,
    request: Request,
    _: EmployeePortalReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
):
    """Download one employee avatar as attachment stream."""
    payload = service.download_avatar(
        employee_id=employee_id,
        auth_context=auth_context,
        request=request,
    )
    response = StreamingResponse(BytesIO(payload.content), media_type=payload.mime_type)
    response.headers["Content-Disposition"] = f'attachment; filename="{payload.filename}"'
    return response


@employee_router.get(
    "/me/onboarding",
    response_model=EmployeeOnboardingPortalResponse,
)
def get_my_onboarding_portal(
    request: Request,
    _: EmployeePortalReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeOnboardingPortalServiceDependency,
) -> EmployeeOnboardingPortalResponse:
    """Read onboarding portal payload for the authenticated employee."""
    return service.get_portal(
        auth_context=auth_context,
        request=request,
    )


@employee_router.patch(
    "/me/onboarding/tasks/{task_id}",
    response_model=EmployeeOnboardingTaskResponse,
)
def update_my_onboarding_task(
    task_id: UUID,
    request: Request,
    payload: EmployeeOnboardingTaskUpdateRequest,
    _: EmployeePortalUpdateRole,
    auth_context: CurrentAuthContext,
    service: EmployeeOnboardingPortalServiceDependency,
) -> EmployeeOnboardingTaskResponse:
    """Update one employee-actionable onboarding task for the authenticated employee."""
    return service.update_task(
        task_id=task_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@employee_router.get("/{employee_id}", response_model=EmployeeProfileResponse)
def get_employee_profile(
    employee_id: UUID,
    request: Request,
    _: EmployeeProfileReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeProfileServiceDependency,
) -> EmployeeProfileResponse:
    """Read one employee profile by identifier."""
    return service.get_profile(
        employee_id=employee_id,
        auth_context=auth_context,
        request=request,
    )


@onboarding_task_router.get(
    "",
    response_model=OnboardingDashboardListResponse,
)
def list_onboarding_dashboard_runs(
    request: Request,
    _: OnboardingDashboardReadRole,
    auth_context: CurrentAuthContext,
    service: OnboardingDashboardServiceDependency,
    search: DashboardSearchQuery = None,
    task_status: DashboardTaskStatusQuery = None,
    assigned_role: DashboardAssignedRoleQuery = None,
    assigned_staff_id: DashboardAssignedStaffQuery = None,
    overdue_only: DashboardOverdueOnlyQuery = False,
    limit: DashboardLimitQuery = 20,
    offset: DashboardOffsetQuery = 0,
) -> OnboardingDashboardListResponse:
    """List onboarding progress rows visible to the current HR or manager actor."""
    return service.list_runs(
        auth_context=auth_context,
        request=request,
        search=search,
        task_status=task_status,
        assigned_role=assigned_role,
        assigned_staff_id=assigned_staff_id,
        overdue_only=overdue_only,
        limit=limit,
        offset=offset,
    )


@onboarding_task_router.get(
    "/{onboarding_id}",
    response_model=OnboardingDashboardDetailResponse,
)
def get_onboarding_dashboard_run(
    onboarding_id: UUID,
    request: Request,
    _: OnboardingDashboardReadRole,
    auth_context: CurrentAuthContext,
    service: OnboardingDashboardServiceDependency,
) -> OnboardingDashboardDetailResponse:
    """Read one onboarding dashboard detail payload with employee summary and tasks."""
    return service.get_run(
        onboarding_id=onboarding_id,
        auth_context=auth_context,
        request=request,
    )


@onboarding_task_router.get(
    "/{onboarding_id}/tasks",
    response_model=OnboardingTaskListResponse,
)
def list_onboarding_tasks(
    onboarding_id: UUID,
    request: Request,
    _: OnboardingTaskListRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTaskServiceDependency,
) -> OnboardingTaskListResponse:
    """List onboarding tasks for one onboarding run."""
    return service.list_tasks(
        onboarding_id=onboarding_id,
        auth_context=auth_context,
        request=request,
    )


@onboarding_task_router.patch(
    "/{onboarding_id}/tasks/{task_id}",
    response_model=OnboardingTaskResponse,
)
def update_onboarding_task(
    onboarding_id: UUID,
    task_id: UUID,
    request: Request,
    payload: OnboardingTaskUpdateRequest,
    _: OnboardingTaskUpdateRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTaskServiceDependency,
) -> OnboardingTaskResponse:
    """Update staff-managed workflow fields for one onboarding task."""
    return service.update_task(
        onboarding_id=onboarding_id,
        task_id=task_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@onboarding_task_router.post(
    "/{onboarding_id}/tasks/backfill",
    response_model=OnboardingTaskListResponse,
)
def backfill_onboarding_tasks(
    onboarding_id: UUID,
    request: Request,
    _: OnboardingTaskBackfillRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTaskServiceDependency,
) -> OnboardingTaskListResponse:
    """Backfill onboarding tasks for one legacy onboarding run that has none yet."""
    return service.backfill_tasks(
        onboarding_id=onboarding_id,
        auth_context=auth_context,
        request=request,
    )


@onboarding_template_router.post("", response_model=OnboardingChecklistTemplateResponse)
def create_onboarding_template(
    request: Request,
    payload: OnboardingChecklistTemplateCreateRequest,
    _: OnboardingTemplateCreateRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTemplateServiceDependency,
) -> OnboardingChecklistTemplateResponse:
    """Create one onboarding checklist template."""
    return service.create_template(payload=payload, auth_context=auth_context, request=request)


@onboarding_template_router.get("", response_model=OnboardingChecklistTemplateListResponse)
def list_onboarding_templates(
    request: Request,
    _: OnboardingTemplateListRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTemplateServiceDependency,
    active_only: bool = Query(default=False),
) -> OnboardingChecklistTemplateListResponse:
    """List onboarding checklist templates."""
    return service.list_templates(
        active_only=active_only,
        auth_context=auth_context,
        request=request,
    )


@onboarding_template_router.get(
    "/{template_id}",
    response_model=OnboardingChecklistTemplateResponse,
)
def get_onboarding_template(
    template_id: UUID,
    request: Request,
    _: OnboardingTemplateReadRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTemplateServiceDependency,
) -> OnboardingChecklistTemplateResponse:
    """Read one onboarding checklist template by identifier."""
    return service.get_template(
        template_id=template_id,
        auth_context=auth_context,
        request=request,
    )


@onboarding_template_router.put(
    "/{template_id}",
    response_model=OnboardingChecklistTemplateResponse,
)
def update_onboarding_template(
    template_id: UUID,
    request: Request,
    payload: OnboardingChecklistTemplateUpdateRequest,
    _: OnboardingTemplateUpdateRole,
    auth_context: CurrentAuthContext,
    service: OnboardingTemplateServiceDependency,
) -> OnboardingChecklistTemplateResponse:
    """Replace one onboarding checklist template by identifier."""
    return service.update_template(
        template_id=template_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


router.include_router(employee_router)
router.include_router(onboarding_task_router)
router.include_router(onboarding_template_router)
