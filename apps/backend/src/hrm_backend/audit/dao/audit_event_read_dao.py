"""Read-only data-access helpers for querying immutable audit events."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import Query, Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.audit.schemas.event import AuditResult, AuditSource


class AuditEventReadDAO:
    """Query DAO for append-only audit events.

    The DAO exposes a shared query builder that is reused by both list and count paths
    to keep filtering semantics deterministic.
    """

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def _build_query(
        self,
        *,
        action: str | None,
        result: AuditResult | None,
        source: AuditSource | None,
        resource_type: str | None,
        correlation_id: str | None,
        occurred_from: datetime | None,
        occurred_to: datetime | None,
    ) -> Query[AuditEvent]:
        """Build base SQLAlchemy query for audit event filters.

        Args:
            action: Optional exact action filter.
            result: Optional exact result filter.
            source: Optional exact source filter.
            resource_type: Optional exact resource-type filter.
            correlation_id: Optional exact correlation-id filter.
            occurred_from: Optional inclusive lower bound for `occurred_at`.
            occurred_to: Optional inclusive upper bound for `occurred_at`.

        Returns:
            Query[AuditEvent]: SQLAlchemy query with all requested filters applied.
        """
        query = self._session.query(AuditEvent)
        if action is not None:
            query = query.filter(AuditEvent.action == action)
        if result is not None:
            query = query.filter(AuditEvent.result == result)
        if source is not None:
            query = query.filter(AuditEvent.source == source)
        if resource_type is not None:
            query = query.filter(AuditEvent.resource_type == resource_type)
        if correlation_id is not None:
            query = query.filter(AuditEvent.correlation_id == correlation_id)
        if occurred_from is not None:
            query = query.filter(AuditEvent.occurred_at >= occurred_from)
        if occurred_to is not None:
            query = query.filter(AuditEvent.occurred_at <= occurred_to)
        return query

    def list_events(
        self,
        *,
        limit: int,
        offset: int,
        action: str | None = None,
        result: AuditResult | None = None,
        source: AuditSource | None = None,
        resource_type: str | None = None,
        correlation_id: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> list[AuditEvent]:
        """List audit events ordered by occurrence time (descending).

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result.
            action: Optional exact action filter.
            result: Optional exact result filter.
            source: Optional exact source filter.
            resource_type: Optional exact resource-type filter.
            correlation_id: Optional exact correlation-id filter.
            occurred_from: Optional inclusive lower bound for `occurred_at`.
            occurred_to: Optional inclusive upper bound for `occurred_at`.

        Returns:
            list[AuditEvent]: Matching audit events ordered deterministically.
        """
        query = self._build_query(
            action=action,
            result=result,
            source=source,
            resource_type=resource_type,
            correlation_id=correlation_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        return list(
            query.order_by(AuditEvent.occurred_at.desc(), AuditEvent.event_id.desc())
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count_events(
        self,
        *,
        action: str | None = None,
        result: AuditResult | None = None,
        source: AuditSource | None = None,
        resource_type: str | None = None,
        correlation_id: str | None = None,
        occurred_from: datetime | None = None,
        occurred_to: datetime | None = None,
    ) -> int:
        """Count audit events matching the provided filters.

        Args:
            action: Optional exact action filter.
            result: Optional exact result filter.
            source: Optional exact source filter.
            resource_type: Optional exact resource-type filter.
            correlation_id: Optional exact correlation-id filter.
            occurred_from: Optional inclusive lower bound for `occurred_at`.
            occurred_to: Optional inclusive upper bound for `occurred_at`.

        Returns:
            int: Total number of matching rows.
        """
        query = self._build_query(
            action=action,
            result=result,
            source=source,
            resource_type=resource_type,
            correlation_id=correlation_id,
            occurred_from=occurred_from,
            occurred_to=occurred_to,
        )
        return _count(query.with_entities(func.count(AuditEvent.event_id)).scalar())


def _count(value: int | None) -> int:
    """Normalize nullable SQL count results into a stable integer."""
    return int(value or 0)

