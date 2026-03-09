"""Data-access helpers for per-interviewer calendar event bindings."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.interviews.models.calendar_binding import InterviewCalendarBinding


class InterviewCalendarBindingDAO:
    """Persist and query external calendar event bindings."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session."""
        self._session = session

    def list_for_interview(self, interview_id: str) -> list[InterviewCalendarBinding]:
        """Load all calendar bindings for one interview."""
        return list(
            self._session.query(InterviewCalendarBinding)
            .filter(InterviewCalendarBinding.interview_id == interview_id)
            .order_by(
                InterviewCalendarBinding.interviewer_staff_id.asc(),
                InterviewCalendarBinding.binding_id.asc(),
            )
            .all()
        )

    def upsert_binding(
        self,
        *,
        interview_id: str,
        interviewer_staff_id: str,
        calendar_id: str,
        calendar_event_id: str,
        schedule_version: int,
    ) -> InterviewCalendarBinding:
        """Create or update one interviewer calendar binding."""
        entity = (
            self._session.query(InterviewCalendarBinding)
            .filter(
                InterviewCalendarBinding.interview_id == interview_id,
                InterviewCalendarBinding.interviewer_staff_id == interviewer_staff_id,
            )
            .first()
        )
        if entity is None:
            entity = InterviewCalendarBinding(
                interview_id=interview_id,
                interviewer_staff_id=interviewer_staff_id,
                calendar_id=calendar_id,
                calendar_event_id=calendar_event_id,
                schedule_version=schedule_version,
            )
        else:
            entity.calendar_id = calendar_id
            entity.calendar_event_id = calendar_event_id
            entity.schedule_version = schedule_version

        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def delete_all(self, interview_id: str) -> None:
        """Delete all bindings for one interview."""
        (
            self._session.query(InterviewCalendarBinding)
            .filter(InterviewCalendarBinding.interview_id == interview_id)
            .delete(synchronize_session=False)
        )
        self._session.commit()
