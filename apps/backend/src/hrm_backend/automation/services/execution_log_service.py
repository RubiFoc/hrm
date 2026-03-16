"""Business service for automation execution log read APIs (TASK-08-03)."""

from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, Request, status

from hrm_backend.audit.services.audit_service import AuditService, actor_from_auth_context
from hrm_backend.auth.schemas.token_claims import AuthContext
from hrm_backend.automation.dao.execution_log_dao import AutomationExecutionLogDAO
from hrm_backend.automation.schemas.executions import (
    AutomationActionExecutionListItem,
    AutomationActionExecutionListResponse,
    AutomationActionExecutionResponse,
    AutomationExecutionRunListItem,
    AutomationExecutionRunListResponse,
    AutomationExecutionRunResponse,
)

AUTOMATION_EXECUTION_RUN_NOT_FOUND = "automation_execution_run_not_found"
AUTOMATION_ACTION_EXECUTION_NOT_FOUND = "automation_action_execution_not_found"


class AutomationExecutionLogService:
    """Expose non-PII automation execution logs for operator inspection."""

    def __init__(
        self,
        *,
        dao: AutomationExecutionLogDAO,
        audit_service: AuditService,
    ) -> None:
        """Initialize service dependencies.

        Args:
            dao: Execution log DAO.
            audit_service: Audit service for operator access traces.
        """
        self._dao = dao
        self._audit_service = audit_service

    def list_runs(
        self,
        *,
        event_type: str | None,
        trigger_event_id: UUID | None,
        status_filter: str | None,
        correlation_id: str | None,
        trace_id: str | None,
        limit: int,
        offset: int,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationExecutionRunListResponse:
        """List execution runs with pagination and optional filters."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        items = [
            _to_run_list_item(row)
            for row in self._dao.list_runs(
                event_type=event_type,
                trigger_event_id=None if trigger_event_id is None else str(trigger_event_id),
                status=status_filter,
                correlation_id=correlation_id,
                trace_id=trace_id,
                limit=limit,
                offset=offset,
            )
        ]
        total = self._dao.count_runs(
            event_type=event_type,
            trigger_event_id=None if trigger_event_id is None else str(trigger_event_id),
            status=status_filter,
            correlation_id=correlation_id,
            trace_id=trace_id,
        )
        self._audit_service.record_api_event(
            action="automation_execution:list",
            resource_type="automation_execution",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
        )
        return AutomationExecutionRunListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_run(
        self,
        *,
        run_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationExecutionRunResponse:
        """Return one execution run by id."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        entity = self._dao.get_run_by_id(run_id=str(run_id))
        if entity is None:
            self._audit_service.record_api_event(
                action="automation_execution:read",
                resource_type="automation_execution",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(run_id),
                reason=AUTOMATION_EXECUTION_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AUTOMATION_EXECUTION_RUN_NOT_FOUND,
            )

        self._audit_service.record_api_event(
            action="automation_execution:read",
            resource_type="automation_execution",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(run_id),
        )
        return _to_run_response(entity)

    def list_actions(
        self,
        *,
        run_id: UUID,
        status_filter: str | None,
        limit: int,
        offset: int,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationActionExecutionListResponse:
        """List action executions for one run."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        if self._dao.get_run_by_id(run_id=str(run_id)) is None:
            self._audit_service.record_api_event(
                action="automation_execution:read",
                resource_type="automation_execution",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(run_id),
                reason=AUTOMATION_EXECUTION_RUN_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AUTOMATION_EXECUTION_RUN_NOT_FOUND,
            )

        items = [
            _to_action_list_item(row)
            for row in self._dao.list_actions_by_run_id(
                run_id=str(run_id),
                status=status_filter,
                limit=limit,
                offset=offset,
            )
        ]
        total = self._dao.count_actions_by_run_id(run_id=str(run_id), status=status_filter)
        self._audit_service.record_api_event(
            action="automation_execution:read",
            resource_type="automation_execution",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(run_id),
        )
        return AutomationActionExecutionListResponse(
            items=items,
            total=total,
            limit=limit,
            offset=offset,
        )

    def get_action(
        self,
        *,
        action_execution_id: UUID,
        auth_context: AuthContext,
        request: Request,
    ) -> AutomationActionExecutionResponse:
        """Return one action execution row by id."""
        actor_sub, actor_role = actor_from_auth_context(auth_context)
        entity = self._dao.get_action_by_id(action_execution_id=str(action_execution_id))
        if entity is None:
            self._audit_service.record_api_event(
                action="automation_execution:read",
                resource_type="automation_execution",
                result="failure",
                request=request,
                actor_sub=actor_sub,
                actor_role=actor_role,
                resource_id=str(action_execution_id),
                reason=AUTOMATION_ACTION_EXECUTION_NOT_FOUND,
            )
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=AUTOMATION_ACTION_EXECUTION_NOT_FOUND,
            )

        self._audit_service.record_api_event(
            action="automation_execution:read",
            resource_type="automation_execution",
            result="success",
            request=request,
            actor_sub=actor_sub,
            actor_role=actor_role,
            resource_id=str(action_execution_id),
        )
        return _to_action_response(entity)


def _to_run_list_item(entity) -> AutomationExecutionRunListItem:
    """Map ORM run entity to a list payload."""
    return AutomationExecutionRunListItem(
        run_id=UUID(entity.run_id),
        event_type=entity.event_type,
        trigger_event_id=UUID(entity.trigger_event_id),
        event_time=entity.event_time,
        correlation_id=entity.correlation_id,
        trace_id=entity.trace_id,
        status=entity.status,  # type: ignore[arg-type]
        planned_action_count=entity.planned_action_count,
        succeeded_action_count=entity.succeeded_action_count,
        deduped_action_count=entity.deduped_action_count,
        failed_action_count=entity.failed_action_count,
        started_at=entity.started_at,
        finished_at=entity.finished_at,
    )


def _to_run_response(entity) -> AutomationExecutionRunResponse:
    """Map ORM run entity to the full response payload."""
    base = _to_run_list_item(entity)
    return AutomationExecutionRunResponse(
        **base.model_dump(),
        error_kind=entity.error_kind,
        error_text=entity.error_text,
        updated_at=entity.updated_at,
    )


def _to_action_list_item(entity) -> AutomationActionExecutionListItem:
    """Map ORM action entity to a list payload."""
    return AutomationActionExecutionListItem(
        action_execution_id=UUID(entity.action_execution_id),
        run_id=UUID(entity.run_id),
        action=entity.action,
        rule_id=UUID(entity.rule_id),
        recipient_staff_id=UUID(entity.recipient_staff_id),
        recipient_role=entity.recipient_role,
        source_type=entity.source_type,
        source_id=UUID(entity.source_id),
        dedupe_key=entity.dedupe_key,
        status=entity.status,  # type: ignore[arg-type]
        attempt_count=entity.attempt_count,
        trace_id=entity.trace_id,
        result_notification_id=(
            None if entity.result_notification_id is None else UUID(entity.result_notification_id)
        ),
        error_kind=entity.error_kind,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )


def _to_action_response(entity) -> AutomationActionExecutionResponse:
    """Map ORM action entity to the full response payload."""
    base = _to_action_list_item(entity)
    return AutomationActionExecutionResponse(
        **base.model_dump(),
        error_text=entity.error_text,
    )
