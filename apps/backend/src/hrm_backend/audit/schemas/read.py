"""Audit event read/query schemas used by the admin audit API."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from hrm_backend.audit.schemas.event import AuditResult, AuditSource


class AuditEventListItem(BaseModel):
    """Serialized audit event item returned from query API.

    This schema mirrors the persisted `audit_events` payload to keep the audit-read path
    a faithful, append-only evidence surface.
    """

    event_id: UUID
    occurred_at: datetime
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


class AuditEventListResponse(BaseModel):
    """Paginated audit event list response with stable contract."""

    items: list[AuditEventListItem]
    total: int = Field(ge=0)
    limit: int = Field(ge=1, le=100)
    offset: int = Field(ge=0)
