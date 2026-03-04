"""Data-access helpers for immutable audit event persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.audit.models.event import AuditEvent
from hrm_backend.audit.schemas.event import AuditEventCreate


class AuditEventDAO:
    """Append-only data-access object for audit events."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def insert_event(self, payload: AuditEventCreate) -> AuditEvent:
        """Insert and persist a new audit event.

        Args:
            payload: Audit event payload.

        Returns:
            AuditEvent: Persisted model instance.
        """
        entity = AuditEvent(**payload.model_dump())
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
