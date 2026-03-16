"""Versioned HTTP routes for automation rule CRUD (planning only in TASK-08-01)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from hrm_backend.auth.dependencies.auth import get_current_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.dependencies.automation import get_automation_rule_service
from hrm_backend.automation.schemas.rules import (
    AutomationRuleActivationRequest,
    AutomationRuleCreateRequest,
    AutomationRuleListResponse,
    AutomationRuleResponse,
    AutomationRuleUpdateRequest,
)
from hrm_backend.automation.services.automation_rule_service import AutomationRuleService
from hrm_backend.rbac import Role, require_permission

router = APIRouter(tags=["automation"])

AutomationRuleServiceDependency = Annotated[
    AutomationRuleService, Depends(get_automation_rule_service)
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
