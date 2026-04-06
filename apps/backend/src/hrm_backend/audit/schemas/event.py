"""Audit event input schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

AuditSource = Literal["api", "job"]
AuditResult = Literal["allowed", "denied", "success", "failure"]


class AuditEventCreate(BaseModel):
    """Input payload for append-only audit event creation.

    Attributes:
        source: Event source (`api` or `job`).
        actor_sub: Subject identifier for actor, if available.
        actor_role: Role claim for actor, if available.
        action: Action identifier for sensitive operation.
        resource_type: Resource category touched by operation.
        resource_id: Optional concrete resource identifier.
        result: Outcome (`allowed`, `denied`, `success`, `failure`).
        reason: Optional explanation for deny/failure outcomes.
        before_snapshot: Optional structured snapshot captured before a write.
        after_snapshot: Optional structured snapshot captured after a write.
        correlation_id: Correlation ID from request/job context.
        ip: Caller IP for API-originated events.
        user_agent: Caller user-agent for API-originated events.
    """

    source: AuditSource
    actor_sub: str | None = Field(default=None, max_length=128)
    actor_role: str | None = Field(default=None, max_length=64)
    action: str = Field(min_length=1, max_length=128)
    resource_type: str = Field(min_length=1, max_length=128)
    resource_id: str | None = Field(default=None, max_length=128)
    result: AuditResult
    reason: str | None = Field(default=None, max_length=2048)
    before_snapshot: dict[str, object] | None = None
    after_snapshot: dict[str, object] | None = None
    correlation_id: str | None = Field(default=None, max_length=64)
    ip: str | None = Field(default=None, max_length=64)
    user_agent: str | None = Field(default=None, max_length=512)
