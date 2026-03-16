"""Versioned HTTP routes for automation rule CRUD (planning only in TASK-08-01)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.dependencies.automation import (
    get_automation_execution_log_service,
    get_automation_rule_service,
)
from hrm_backend.automation.schemas.executions import (
    AutomationActionExecutionListResponse,
    AutomationActionExecutionResponse,
    AutomationActionExecutionStatus,
    AutomationExecutionRunListResponse,
    AutomationExecutionRunResponse,
    AutomationExecutionRunStatus,
)
from hrm_backend.automation.schemas.rules import (
    AutomationRuleActivationRequest,
    AutomationRuleCreateRequest,
    AutomationRuleListResponse,
    AutomationRuleResponse,
    AutomationRuleUpdateRequest,
)
from hrm_backend.automation.services.automation_rule_service import AutomationRuleService
from hrm_backend.automation.services.execution_log_service import AutomationExecutionLogService
from hrm_backend.rbac import Role, require_permission

router = APIRouter(tags=["automation"])

AutomationRuleServiceDependency = Annotated[
    AutomationRuleService, Depends(get_automation_rule_service)
]
AutomationExecutionLogServiceDependency = Annotated[
    AutomationExecutionLogService,
    Depends(get_automation_execution_log_service),
]
CurrentAuthContext = Annotated[AuthContext, Depends(get_current_auth_context)]

AutomationRuleCreateRole = Annotated[
    Role,
    Depends(require_permission("automation_rule:create")),
]
AutomationRuleListRole = Annotated[
    Role,
    Depends(require_permission("automation_rule:list")),
]
AutomationRuleUpdateRole = Annotated[
    Role,
    Depends(require_permission("automation_rule:update")),
]
AutomationRuleActivateRole = Annotated[
    Role,
    Depends(require_permission("automation_rule:activate")),
]
AutomationExecutionListRole = Annotated[
    Role,
    Depends(require_permission("automation_execution:list")),
]
AutomationExecutionReadRole = Annotated[
    Role,
    Depends(require_permission("automation_execution:read")),
]


@router.post("/api/v1/automation/rules", response_model=AutomationRuleResponse)
def create_rule(
    request: Request,
    payload: AutomationRuleCreateRequest,
    _: AutomationRuleCreateRole,
    auth_context: CurrentAuthContext,
    service: AutomationRuleServiceDependency,
) -> AutomationRuleResponse:
    """Create a new inactive automation rule."""
    return service.create_rule(payload=payload, auth_context=auth_context, request=request)


@router.get("/api/v1/automation/rules", response_model=AutomationRuleListResponse)
def list_rules(
    request: Request,
    _: AutomationRuleListRole,
    auth_context: CurrentAuthContext,
    service: AutomationRuleServiceDependency,
    trigger: Annotated[str | None, Query(max_length=128)] = None,
    is_active: Annotated[bool | None, Query()] = None,
) -> AutomationRuleListResponse:
    """List automation rules."""
    return service.list_rules(
        trigger=trigger,
        is_active=is_active,
        auth_context=auth_context,
        request=request,
    )


@router.patch("/api/v1/automation/rules/{rule_id}", response_model=AutomationRuleResponse)
def patch_rule(
    rule_id: UUID,
    request: Request,
    payload: AutomationRuleUpdateRequest,
    _: AutomationRuleUpdateRole,
    auth_context: CurrentAuthContext,
    service: AutomationRuleServiceDependency,
) -> AutomationRuleResponse:
    """Patch one automation rule (excluding activation)."""
    return service.update_rule(
        rule_id=rule_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.post(
    "/api/v1/automation/rules/{rule_id}/activation",
    response_model=AutomationRuleResponse,
)
def set_rule_activation(
    rule_id: UUID,
    request: Request,
    payload: AutomationRuleActivationRequest,
    _: AutomationRuleActivateRole,
    auth_context: CurrentAuthContext,
    service: AutomationRuleServiceDependency,
) -> AutomationRuleResponse:
    """Activate or deactivate one automation rule."""
    return service.set_activation(
        rule_id=rule_id,
        payload=payload,
        auth_context=auth_context,
        request=request,
    )


@router.get("/api/v1/automation/executions", response_model=AutomationExecutionRunListResponse)
def list_execution_runs(
    request: Request,
    _: AutomationExecutionListRole,
    auth_context: CurrentAuthContext,
    service: AutomationExecutionLogServiceDependency,
    event_type: Annotated[str | None, Query(max_length=128)] = None,
    trigger_event_id: Annotated[UUID | None, Query()] = None,
    status: Annotated[AutomationExecutionRunStatus | None, Query()] = None,
    correlation_id: Annotated[str | None, Query(max_length=64)] = None,
    trace_id: Annotated[str | None, Query(max_length=64)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AutomationExecutionRunListResponse:
    """List automation execution runs (non-PII operator view)."""
    return service.list_runs(
        event_type=event_type,
        trigger_event_id=trigger_event_id,
        status_filter=status,
        correlation_id=correlation_id,
        trace_id=trace_id,
        limit=limit,
        offset=offset,
        auth_context=auth_context,
        request=request,
    )


@router.get(
    "/api/v1/automation/executions/{run_id}",
    response_model=AutomationExecutionRunResponse,
)
def get_execution_run(
    run_id: UUID,
    request: Request,
    _: AutomationExecutionReadRole,
    auth_context: CurrentAuthContext,
    service: AutomationExecutionLogServiceDependency,
) -> AutomationExecutionRunResponse:
    """Return one automation execution run by id (non-PII operator view)."""
    return service.get_run(run_id=run_id, auth_context=auth_context, request=request)


@router.get(
    "/api/v1/automation/executions/{run_id}/actions",
    response_model=AutomationActionExecutionListResponse,
)
def list_execution_actions(
    run_id: UUID,
    request: Request,
    _: AutomationExecutionReadRole,
    auth_context: CurrentAuthContext,
    service: AutomationExecutionLogServiceDependency,
    status: Annotated[AutomationActionExecutionStatus | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> AutomationActionExecutionListResponse:
    """List action executions for one run (non-PII operator view)."""
    return service.list_actions(
        run_id=run_id,
        status_filter=status,
        limit=limit,
        offset=offset,
        auth_context=auth_context,
        request=request,
    )


@router.get(
    "/api/v1/automation/action-executions/{action_execution_id}",
    response_model=AutomationActionExecutionResponse,
)
def get_action_execution(
    action_execution_id: UUID,
    request: Request,
    _: AutomationExecutionReadRole,
    auth_context: CurrentAuthContext,
    service: AutomationExecutionLogServiceDependency,
) -> AutomationActionExecutionResponse:
    """Return one action execution by id (non-PII operator view)."""
    return service.get_action(
        action_execution_id=action_execution_id,
        auth_context=auth_context,
        request=request,
    )
