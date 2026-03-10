"""Data-access helpers for structured interview feedback rows."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.interviews.models.feedback import InterviewFeedback


class InterviewFeedbackDAO:
    """Persist and query structured interviewer feedback rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO with active SQLAlchemy session.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def list_for_interview(
        self,
        *,
        interview_id: str,
        schedule_version: int | None = None,
    ) -> list[InterviewFeedback]:
        """List feedback rows for one interview with optional schedule-version filter.

        Args:
            interview_id: Interview identifier.
            schedule_version: Optional interview schedule version.

        Returns:
            list[InterviewFeedback]: Ordered feedback rows.
        """
        query = self._session.query(InterviewFeedback).filter(
            InterviewFeedback.interview_id == interview_id
        )
        if schedule_version is not None:
            query = query.filter(InterviewFeedback.schedule_version == schedule_version)
        return list(
            query.order_by(
                InterviewFeedback.schedule_version.asc(),
                InterviewFeedback.interviewer_staff_id.asc(),
                InterviewFeedback.feedback_id.asc(),
            ).all()
        )

    def get_for_interviewer(
        self,
        *,
        interview_id: str,
        schedule_version: int,
        interviewer_staff_id: str,
    ) -> InterviewFeedback | None:
        """Fetch one feedback row for one interviewer and one schedule version.

        Args:
            interview_id: Interview identifier.
            schedule_version: Interview schedule version.
            interviewer_staff_id: Interviewer staff identifier.

        Returns:
            InterviewFeedback | None: Existing feedback row, if any.
        """
        return (
            self._session.query(InterviewFeedback)
            .filter(
                InterviewFeedback.interview_id == interview_id,
                InterviewFeedback.schedule_version == schedule_version,
                InterviewFeedback.interviewer_staff_id == interviewer_staff_id,
            )
            .first()
        )

    def upsert_feedback(
        self,
        *,
        interview_id: str,
        schedule_version: int,
        interviewer_staff_id: str,
        requirements_match_score: int,
        communication_score: int,
        problem_solving_score: int,
        collaboration_score: int,
        recommendation: str,
        strengths_note: str,
        concerns_note: str,
        evidence_note: str,
    ) -> InterviewFeedback:
        """Create or replace the current feedback row for one interviewer.

        Args:
            interview_id: Interview identifier.
            schedule_version: Interview schedule version.
            interviewer_staff_id: Interviewer staff identifier.
            requirements_match_score: Requirements-match rubric score.
            communication_score: Communication rubric score.
            problem_solving_score: Problem-solving rubric score.
            collaboration_score: Collaboration rubric score.
            recommendation: Structured recommendation enum value.
            strengths_note: Positive evidence note.
            concerns_note: Concerns note.
            evidence_note: Supporting free-text evidence note.

        Returns:
            InterviewFeedback: Persisted feedback row.
        """
        entity = self.get_for_interviewer(
            interview_id=interview_id,
            schedule_version=schedule_version,
            interviewer_staff_id=interviewer_staff_id,
        )
        if entity is None:
            entity = InterviewFeedback(
                interview_id=interview_id,
                schedule_version=schedule_version,
                interviewer_staff_id=interviewer_staff_id,
                requirements_match_score=requirements_match_score,
                communication_score=communication_score,
                problem_solving_score=problem_solving_score,
                collaboration_score=collaboration_score,
                recommendation=recommendation,
                strengths_note=strengths_note,
                concerns_note=concerns_note,
                evidence_note=evidence_note,
            )
        else:
            entity.requirements_match_score = requirements_match_score
            entity.communication_score = communication_score
            entity.problem_solving_score = problem_solving_score
            entity.collaboration_score = collaboration_score
            entity.recommendation = recommendation
            entity.strengths_note = strengths_note
            entity.concerns_note = concerns_note
            entity.evidence_note = evidence_note
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
