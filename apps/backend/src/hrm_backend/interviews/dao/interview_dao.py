"""Data-access helpers for interview lifecycle rows."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hrm_backend.interviews.models.interview import Interview


class InterviewDAO:
    """Persist and query interview lifecycle rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def create_interview(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        scheduled_start_at: datetime,
        scheduled_end_at: datetime,
        timezone: str,
        location_kind: str,
        location_details: str | None,
        interviewer_staff_ids: list[str],
        created_by_staff_id: str,
    ) -> Interview:
        """Insert one queued interview row."""
        entity = Interview(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            status="pending_sync",
            calendar_sync_status="queued",
            schedule_version=1,
            scheduled_start_at=scheduled_start_at,
            scheduled_end_at=scheduled_end_at,
            timezone=timezone,
            location_kind=location_kind,
            location_details=location_details,
            interviewer_staff_ids_json=interviewer_staff_ids,
            candidate_response_status="pending",
            created_by_staff_id=created_by_staff_id,
            updated_by_staff_id=created_by_staff_id,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_by_id(self, interview_id: str) -> Interview | None:
        """Fetch interview row by identifier."""
        return self._session.get(Interview, interview_id)

    def get_by_token_hash(self, token_hash: str) -> Interview | None:
        """Fetch current interview row by stored invitation token hash."""
        return (
            self._session.query(Interview)
            .filter(Interview.candidate_token_hash == token_hash)
            .first()
        )

    def find_active_for_pair(self, *, vacancy_id: str, candidate_id: str) -> Interview | None:
        """Load one non-terminal interview row for vacancy-candidate pair."""
        return (
            self._session.query(Interview)
            .filter(
                Interview.vacancy_id == vacancy_id,
                Interview.candidate_id == candidate_id,
                Interview.status != "cancelled",
            )
            .order_by(Interview.created_at.desc(), Interview.interview_id.desc())
            .first()
        )

    def list_for_vacancy(
        self,
        *,
        vacancy_id: str,
        candidate_id: str | None = None,
        status: str | None = None,
    ) -> list[Interview]:
        """List interview rows for one vacancy with optional filters."""
        query = self._session.query(Interview).filter(Interview.vacancy_id == vacancy_id)
        if candidate_id is not None:
            query = query.filter(Interview.candidate_id == candidate_id)
        if status is not None:
            query = query.filter(Interview.status == status)
        return list(query.order_by(Interview.created_at.desc(), Interview.interview_id.desc()).all())

    def save(self, entity: Interview) -> Interview:
        """Persist in-memory changes and refresh interview row."""
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def claim_by_id(self, interview_id: str) -> Interview | None:
        """Claim one queued/failed interview sync row and move it to running."""
        entity = (
            self._session.query(Interview)
            .filter(
                Interview.interview_id == interview_id,
                Interview.calendar_sync_status.in_(["queued", "failed"]),
            )
            .first()
        )
        if entity is None:
            return None

        entity.calendar_sync_status = "running"
        entity.calendar_sync_reason_code = None
        entity.calendar_sync_error_detail = None
        entity.updated_at = datetime.now(UTC)
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
