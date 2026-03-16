"""Business service for automation rule CRUD endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.dao.automation_rule_dao import AutomationRuleDAO
from hrm_backend.automation.schemas.rules import (
    AutomationRuleActivationRequest,
    AutomationRuleCreateRequest,
    AutomationRuleListResponse,
    AutomationRuleResponse,
    AutomationRuleUpdateRequest,
)

AUTOMATION_RULE_NOT_FOUND = "automation_rule_not_found"


class AutomationRuleService:
    """Manage automation rules via staff-only APIs."""

    def __init__(
        self,
        *,
        rule_dao: AutomationRuleDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize service dependencies."""
        self._rule_dao = rule_dao
        self._audit_service = audit_service

    def create_rule(
        self,
        *,
        payload: AutomationRuleCreateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationRuleResponse:
        """Create a new inactive automation rule."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        conditions_json = (
            payload.conditions.model_dump(mode="json") if payload.conditions else None
        )
        entity = self._rule_dao.create_rule(
            name=payload.name,
            trigger=payload.trigger,
            conditions_json=conditions_json,
            actions_json=[action.model_dump(mode="json") for action in payload.actions],
            priority=payload.priority,
            created_by_staff_id=actor_sub,
        )
        self._audit_service.record_api_event(
            action="automation_rule:create",
            resource_type="automation_rule",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.rule_id,
        )
        return _to_rule_response(entity)

    def list_rules(
        self,
        *,
        trigger: str | None,
        is_active: bool | None,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationRuleListResponse:
        """List automation rules for operator/admin UX."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        rows = self._rule_dao.list_rules(trigger=trigger, is_active=is_active)
        items = [_to_rule_response(row) for row in rows]
        self._audit_service.record_api_event(
            action="automation_rule:list",
            resource_type="automation_rule",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return AutomationRuleListResponse(items=items)

    def update_rule(
        self,
        *,
        rule_id: UUID,
        payload: AutomationRuleUpdateRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationRuleResponse:
        """Patch rule fields (excluding activation)."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        entity = self._rule_dao.get_by_id(str(rule_id))
        if entity is None:
            self._audit_service.record_api_event(
                action="automation_rule:update",
                resource_type="automation_rule",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(rule_id),
                reason=AUTOMATION_RULE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AUTOMATION_RULE_NOT_FOUND,
            )

        set_conditions = "conditions" in payload.model_fields_set
        conditions_json = payload.conditions.model_dump(mode="json") if payload.conditions else None
        if "actions" in payload.model_fields_set and payload.actions is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="automation_rule_actions_required",
            )

        entity = self._rule_dao.update_rule(
            entity=entity,
            name=payload.name if "name" in payload.model_fields_set else None,
            set_conditions=set_conditions,
            conditions_json=conditions_json,
            actions_json=(
                [action.model_dump(mode="json") for action in payload.actions]
                if payload.actions is not None
                else None
            ),
            priority=payload.priority,
            updated_by_staff_id=actor_sub,
        )
        self._audit_service.record_api_event(
            action="automation_rule:update",
            resource_type="automation_rule",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.rule_id,
        )
        return _to_rule_response(entity)

    def set_activation(
        self,
        *,
        rule_id: UUID,
        payload: AutomationRuleActivationRequest,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationRuleResponse:
        """Activate or deactivate an automation rule."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        entity = self._rule_dao.get_by_id(str(rule_id))
        if entity is None:
            self._audit_service.record_api_event(
                action="automation_rule:activate",
                resource_type="automation_rule",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(rule_id),
                reason=AUTOMATION_RULE_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AUTOMATION_RULE_NOT_FOUND,
            )

        entity = self._rule_dao.set_active(
            entity=entity,
            is_active=payload.is_active,
            updated_by_staff_id=actor_sub,
        )
        self._audit_service.record_api_event(
            action="automation_rule:activate",
            resource_type="automation_rule",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=entity.rule_id,
        )
        return _to_rule_response(entity)


def _to_rule_response(entity) -> AutomationRuleResponse:
    """Map rule ORM entity to the public response schema."""
    return AutomationRuleResponse(
        rule_id=UUID(entity.rule_id),
        name=entity.name,
        trigger=entity.trigger,
        conditions=entity.conditions_json,
        actions=entity.actions_json,
        priority=entity.priority,
        is_active=entity.is_active,
        created_by_staff_id=UUID(entity.created_by_staff_id),
        updated_by_staff_id=UUID(entity.updated_by_staff_id),
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
