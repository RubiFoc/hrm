"""DAO helpers for compensation raise requests."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from hrm_backend.finance.models.compensation_raise_request import CompensationRaiseRequest


class CompensationRaiseRequestDAO:
    """Data-access helper for compensation raise requests."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def get_by_id(self, request_id: str) -> CompensationRaiseRequest | None:
        """Fetch raise request by identifier."""
        return self._session.get(CompensationRaiseRequest, request_id)

    def create(
        self,
        *,
        entity: CompensationRaiseRequest,
        commit: bool = True,
    ) -> CompensationRaiseRequest:
        """Persist a new raise request entity."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity
        self._session.flush()
        return entity

    def update(
        self,
        *,
        entity: CompensationRaiseRequest,
        commit: bool = True,
    ) -> CompensationRaiseRequest:
        """Persist in-memory changes to one raise request."""
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity
        self._session.flush()
        return entity

    def list_by_employee_ids(
        self,
        *,
        employee_ids: list[str],
    ) -> list[CompensationRaiseRequest]:
        """List raise requests for the provided employee identifiers."""
        if not employee_ids:
            return []
        return list(
            self._session.query(CompensationRaiseRequest)
            .filter(CompensationRaiseRequest.employee_id.in_(employee_ids))
            .order_by(
                CompensationRaiseRequest.requested_at.desc(),
                CompensationRaiseRequest.request_id.asc(),
            )
            .all()
        )

    def list_requests(
        self,
        *,
        employee_ids: list[str] | None,
        status: str | None,
        limit: int,
        offset: int,
    ) -> list[CompensationRaiseRequest]:
        """List raise requests with optional employee and status filters."""
        query = self._session.query(CompensationRaiseRequest)
        if employee_ids is not None:
            if not employee_ids:
                return []
            query = query.filter(CompensationRaiseRequest.employee_id.in_(employee_ids))
        if status:
            query = query.filter(CompensationRaiseRequest.status == status)
        return list(
            query.order_by(
                CompensationRaiseRequest.requested_at.desc(),
                CompensationRaiseRequest.request_id.asc(),
            )
            .limit(limit)
            .offset(offset)
            .all()
        )

    def count_requests(
        self,
        *,
        employee_ids: list[str] | None,
        status: str | None,
    ) -> int:
        """Count raise requests for optional filters."""
        query = self._session.query(func.count(CompensationRaiseRequest.request_id))
        if employee_ids is not None:
            if not employee_ids:
                return 0
            query = query.filter(CompensationRaiseRequest.employee_id.in_(employee_ids))
        if status:
            query = query.filter(CompensationRaiseRequest.status == status)
        return int(query.scalar() or 0)
