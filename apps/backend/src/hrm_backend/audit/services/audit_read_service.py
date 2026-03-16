"""Read-only service for querying persisted audit events through API boundary."""

from __future__ import annotations

from datetime import UTC, datetime

from fastapi import HTTPException, status
from sqlalchemy.exc import SQLAlchemyError

from hrm_backend.audit.dao.audit_event_read_dao import AuditEventReadDAO
from hrm_backend.audit.schemas.event import AuditResult, AuditSource
from hrm_backend.audit.schemas.read import AuditEventListItem, AuditEventListResponse
from hrm_backend.core.errors.http import service_unavailable


class AuditReadService:
    """Service that validates audit query filters and builds stable responses."""

    def __init__(self, dao: AuditEventReadDAO) -> None:
        """Initialize service with DAO dependency.

        Args:
            dao: Read-only audit event DAO.
        """
        self._dao = dao

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
    ) -> AuditEventListResponse:
        """Return filtered audit events with stable pagination metadata.

        Args:
            limit: Maximum number of rows to return (1..100).
            offset: Number of rows to skip from ordered result (>= 0).
            action: Optional exact action filter.
            result: Optional exact result filter.
            source: Optional exact source filter.
            resource_type: Optional exact resource-type filter.
            correlation_id: Optional exact correlation-id filter.
            occurred_from: Optional inclusive lower bound for `occurred_at`.
            occurred_to: Optional inclusive upper bound for `occurred_at`.

        Returns:
            AuditEventListResponse: Paginated list response with stable ordering.

        Raises:
            HTTPException: When time range filter is invalid.
            fastapi.HTTPException: When audit storage is unavailable.
        """
        normalized_from = _normalize_utc(occurred_from)
        normalized_to = _normalize_utc(occurred_to)
        if normalized_from is not None and normalized_to is not None:
            if normalized_from > normalized_to:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="invalid_time_range",
                )

        try:
            entities = self._dao.list_events(
                limit=limit,
                offset=offset,
                action=action,
                result=result,
                source=source,
                resource_type=resource_type,
                correlation_id=correlation_id,
                occurred_from=normalized_from,
                occurred_to=normalized_to,
            )
            total = self._dao.count_events(
                action=action,
                result=result,
                source=source,
                resource_type=resource_type,
                correlation_id=correlation_id,
                occurred_from=normalized_from,
                occurred_to=normalized_to,
            )
        except SQLAlchemyError as exc:
            raise service_unavailable("Audit storage temporarily unavailable") from exc

        items = [_to_list_item(entity) for entity in entities]
        return AuditEventListResponse(items=items, total=total, limit=limit, offset=offset)

    def export_events(
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
    ) -> list[AuditEventListItem]:
        """Return filtered audit events for attachment exports.

        This method reuses the same filter semantics as the list API but returns only the
        serialized rows needed for export rendering.

        Args:
            limit: Maximum number of rows to return.
            offset: Number of rows to skip from ordered result (>= 0).
            action: Optional exact action filter.
            result: Optional exact result filter.
            source: Optional exact source filter.
            resource_type: Optional exact resource-type filter.
            correlation_id: Optional exact correlation-id filter.
            occurred_from: Optional inclusive lower bound for `occurred_at`.
            occurred_to: Optional inclusive upper bound for `occurred_at`.

        Returns:
            list[AuditEventListItem]: Matching audit events ordered deterministically.

        Raises:
            HTTPException: When time range filter is invalid.
            fastapi.HTTPException: When audit storage is unavailable.
        """
        normalized_from = _normalize_utc(occurred_from)
        normalized_to = _normalize_utc(occurred_to)
        if normalized_from is not None and normalized_to is not None:
            if normalized_from > normalized_to:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    detail="invalid_time_range",
                )

        try:
            entities = self._dao.list_events(
                limit=limit,
                offset=offset,
                action=action,
                result=result,
                source=source,
                resource_type=resource_type,
                correlation_id=correlation_id,
                occurred_from=normalized_from,
                occurred_to=normalized_to,
            )
        except SQLAlchemyError as exc:
            raise service_unavailable("Audit storage temporarily unavailable") from exc

        return [_to_list_item(entity) for entity in entities]


def _normalize_utc(value: datetime | None) -> datetime | None:
    """Normalize potentially-naive datetime values into timezone-aware UTC datetimes."""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _to_list_item(entity) -> AuditEventListItem:  # noqa: ANN001
    """Map persisted audit event row into the stable API/export item schema."""
    return AuditEventListItem(
        event_id=entity.event_id,
        occurred_at=entity.occurred_at,
        source=entity.source,  # type: ignore[arg-type]
        actor_sub=entity.actor_sub,
        actor_role=entity.actor_role,
        action=entity.action,
        resource_type=entity.resource_type,
        resource_id=entity.resource_id,
        result=entity.result,  # type: ignore[arg-type]
        reason=entity.reason,
        correlation_id=entity.correlation_id,
        ip=entity.ip,
        user_agent=entity.user_agent,
    )
