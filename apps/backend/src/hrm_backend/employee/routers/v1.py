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
    get_employee_avatar_service,
    get_employee_directory_service,
    get_employee_onboarding_portal_service,
    get_employee_profile_service,
    get_onboarding_dashboard_service,
    get_onboarding_task_service,
    get_onboarding_template_service,
)
from hrm_backend.employee.schemas.avatar import (
    EmployeeAvatarDeleteResponse,
    EmployeeAvatarUploadResponse,
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
    EmployeeDirectoryListResponse,
    EmployeeDirectoryProfileResponse,
    EmployeeProfileCreateRequest,
    EmployeeProfilePrivacySettingsResponse,
    EmployeeProfilePrivacyUpdateRequest,
    EmployeeProfileResponse,
)
from hrm_backend.employee.schemas.template import (
    OnboardingChecklistTemplateCreateRequest,
    OnboardingChecklistTemplateListResponse,
    OnboardingChecklistTemplateResponse,
    OnboardingChecklistTemplateUpdateRequest,
)
from hrm_backend.employee.services.employee_avatar_service import EmployeeAvatarService
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
EmployeeDirectoryServiceDependency = Annotated[
    EmployeeDirectoryService,
    Depends(get_employee_directory_service),
]
EmployeeAvatarServiceDependency = Annotated[
    EmployeeAvatarService,
    Depends(get_employee_avatar_service),
]
EmployeeOnboardingPortalServiceDependency = Annotated[
    EmployeeOnboardingPortalService,
    Depends(get_employee_onboarding_portal_service),
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
DirectoryLimitQuery = Annotated[int, Query(ge=1, le=100)]
DirectoryOffsetQuery = Annotated[int, Query(ge=0)]
EmployeeProfileCreateRole = Annotated[Role, Depends(require_permission("employee_profile:create"))]
EmployeeProfileReadRole = Annotated[Role, Depends(require_permission("employee_profile:read"))]
EmployeeProfilePrivacyRole = Annotated[
    Role,
    Depends(require_permission("employee_profile:privacy_update")),
]
EmployeeDirectoryReadRole = Annotated[Role, Depends(require_permission("employee_directory:read"))]
EmployeeAvatarReadRole = Annotated[Role, Depends(require_permission("employee_avatar:read"))]
EmployeeAvatarWriteRole = Annotated[Role, Depends(require_permission("employee_avatar:write"))]
EmployeeAvatarAdminRole = Annotated[Role, Depends(require_permission("employee_avatar:admin"))]
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


@employee_router.get(
    "/directory",
    response_model=EmployeeDirectoryListResponse,
)
def list_employee_directory(
    request: Request,
    _: EmployeeDirectoryReadRole,
    __: EmployeeAvatarReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
    limit: DirectoryLimitQuery = 20,
    offset: DirectoryOffsetQuery = 0,
) -> EmployeeDirectoryListResponse:
    """List employee directory cards visible to the current staff actor.

    Args:
        request: Active HTTP request.
        auth_context: Authenticated actor context.
        service: Employee directory service dependency.
        limit: Pagination limit for directory rows.
        offset: Pagination offset for directory rows.

    Returns:
        EmployeeDirectoryListResponse: Directory list payload.
    """
    return service.list_directory(
        auth_context=auth_context,
        request=request,
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
    _: EmployeeDirectoryReadRole,
    __: EmployeeAvatarReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
) -> EmployeeDirectoryProfileResponse:
    """Read one employee directory profile by identifier.

    Args:
        employee_id: Employee profile identifier.
        request: Active HTTP request.
        auth_context: Authenticated actor context.
        service: Employee directory service dependency.

    Returns:
        EmployeeDirectoryProfileResponse: Directory profile payload.
    """
    return service.get_profile(
        employee_id=str(employee_id),
        auth_context=auth_context,
        request=request,
    )


@employee_router.get(
    "/me/privacy",
    response_model=EmployeeProfilePrivacySettingsResponse,
)
def get_my_employee_privacy_settings(
    request: Request,
    _: EmployeeProfilePrivacyRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
) -> EmployeeProfilePrivacySettingsResponse:
    """Read privacy settings for the authenticated employee profile.

    Args:
        request: Active HTTP request.
        auth_context: Authenticated actor context.
        service: Employee directory service dependency.

    Returns:
        EmployeeProfilePrivacySettingsResponse: Current privacy configuration.
    """
    return service.get_privacy_settings(auth_context=auth_context, request=request)


@employee_router.patch(
    "/me/privacy",
    response_model=EmployeeProfilePrivacySettingsResponse,
)
def update_my_employee_privacy_settings(
    request: Request,
    payload: EmployeeProfilePrivacyUpdateRequest,
    _: EmployeeProfilePrivacyRole,
    auth_context: CurrentAuthContext,
    service: EmployeeDirectoryServiceDependency,
) -> EmployeeProfilePrivacySettingsResponse:
    """Update privacy settings for the authenticated employee profile.

    Args:
        request: Active HTTP request.
        payload: Privacy update payload.
        auth_context: Authenticated actor context.
        service: Employee directory service dependency.

    Returns:
        EmployeeProfilePrivacySettingsResponse: Updated privacy configuration.
    """
    return service.update_privacy_settings(
        payload=payload,
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
    _: EmployeeAvatarWriteRole,
    auth_context: CurrentAuthContext,
    service: EmployeeAvatarServiceDependency,
) -> EmployeeAvatarUploadResponse:
    """Upload avatar for the authenticated employee profile.

    Args:
        request: Active HTTP request.
        file: Multipart avatar file.
        auth_context: Authenticated actor context.
        service: Employee avatar service dependency.

    Returns:
        EmployeeAvatarUploadResponse: Uploaded avatar metadata.
    """
    return await service.upload_my_avatar(
        file=file,
        auth_context=auth_context,
        request=request,
    )


@employee_router.delete(
    "/me/avatar",
    response_model=EmployeeAvatarDeleteResponse,
)
def delete_my_employee_avatar(
    request: Request,
    _: EmployeeAvatarWriteRole,
    auth_context: CurrentAuthContext,
    service: EmployeeAvatarServiceDependency,
) -> EmployeeAvatarDeleteResponse:
    """Delete avatar for the authenticated employee profile.

    Args:
        request: Active HTTP request.
        auth_context: Authenticated actor context.
        service: Employee avatar service dependency.

    Returns:
        EmployeeAvatarDeleteResponse: Deletion metadata payload.
    """
    return service.delete_my_avatar(
        auth_context=auth_context,
        request=request,
    )


@employee_router.post(
    "/{employee_id}/avatar",
    response_model=EmployeeAvatarUploadResponse,
)
async def upload_employee_avatar_admin(
    employee_id: UUID,
    request: Request,
    file: Annotated[UploadFile, File(...)],
    _: EmployeeAvatarAdminRole,
    auth_context: CurrentAuthContext,
    service: EmployeeAvatarServiceDependency,
) -> EmployeeAvatarUploadResponse:
    """Upload avatar for a target employee profile (admin/HR override).

    Args:
        employee_id: Employee profile identifier.
        request: Active HTTP request.
        file: Multipart avatar file.
        auth_context: Authenticated actor context.
        service: Employee avatar service dependency.

    Returns:
        EmployeeAvatarUploadResponse: Uploaded avatar metadata.
    """
    return await service.upload_employee_avatar_admin(
        employee_id=str(employee_id),
        file=file,
        auth_context=auth_context,
        request=request,
    )


@employee_router.delete(
    "/{employee_id}/avatar",
    response_model=EmployeeAvatarDeleteResponse,
)
def delete_employee_avatar_admin(
    employee_id: UUID,
    request: Request,
    _: EmployeeAvatarAdminRole,
    auth_context: CurrentAuthContext,
    service: EmployeeAvatarServiceDependency,
) -> EmployeeAvatarDeleteResponse:
    """Delete avatar for a target employee profile (admin/HR override).

    Args:
        employee_id: Employee profile identifier.
        request: Active HTTP request.
        auth_context: Authenticated actor context.
        service: Employee avatar service dependency.

    Returns:
        EmployeeAvatarDeleteResponse: Deletion metadata payload.
    """
    return service.delete_employee_avatar_admin(
        employee_id=str(employee_id),
        auth_context=auth_context,
        request=request,
    )


@employee_router.get("/{employee_id}/avatar")
def read_employee_avatar(
    employee_id: UUID,
    request: Request,
    _: EmployeeAvatarReadRole,
    auth_context: CurrentAuthContext,
    service: EmployeeAvatarServiceDependency,
):
    """Download active employee avatar as an inline stream.

    Args:
        employee_id: Employee profile identifier.
        request: Active HTTP request.
        auth_context: Authenticated actor context.
        service: Employee avatar service dependency.

    Returns:
        StreamingResponse: Inline avatar stream response.
    """
    payload = service.read_avatar(
        employee_id=str(employee_id),
        auth_context=auth_context,
        request=request,
    )
    return StreamingResponse(BytesIO(payload.content), media_type=payload.mime_type)


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
