"""DAO for append-only pipeline transition history."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.vacancies.models.pipeline_transition import PipelineTransition
from hrm_backend.vacancies.schemas.pipeline import PipelineStage


class PipelineTransitionDAO:
    """Data-access helper for pipeline transition events."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_transition(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
        from_stage: PipelineStage | None,
        to_stage: PipelineStage,
        reason: str | None,
        changed_by_sub: str,
        changed_by_role: str,
        commit: bool = True,
    ) -> PipelineTransition:
        """Insert append-only pipeline transition event.

        Args:
            vacancy_id: Vacancy identifier.
            candidate_id: Candidate identifier.
            from_stage: Previous stage.
            to_stage: New stage.
            reason: Optional reason.
            changed_by_sub: Actor subject id.
            changed_by_role: Actor role.
            commit: When `True`, commit immediately; otherwise flush into the current
                transaction so callers can bundle multiple writes atomically.

        Returns:
            PipelineTransition: Persisted transition event.
        """
        entity = PipelineTransition(
            vacancy_id=vacancy_id,
            candidate_id=candidate_id,
            from_stage=from_stage,
            to_stage=to_stage,
            reason=reason,
            changed_by_sub=changed_by_sub,
            changed_by_role=changed_by_role,
        )
        self._session.add(entity)
        if commit:
            self._session.commit()
            self._session.refresh(entity)
            return entity

        self._session.flush()
        return entity

    def get_last_transition(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
    ) -> PipelineTransition | None:
        """Load latest transition event for vacancy+candidate pair.

        Args:
            vacancy_id: Vacancy identifier.
            candidate_id: Candidate identifier.

        Returns:
            PipelineTransition | None: Latest event or `None`.
        """
        return (
            self._session.query(PipelineTransition)
            .filter(
                PipelineTransition.vacancy_id == vacancy_id,
                PipelineTransition.candidate_id == candidate_id,
            )
            .order_by(
                PipelineTransition.transitioned_at.desc(),
                PipelineTransition.transition_id.desc(),
            )
            .first()
        )

    def list_transitions(
        self,
        *,
        vacancy_id: str,
        candidate_id: str,
    ) -> list[PipelineTransition]:
        """Load ordered transition history for one vacancy+candidate pair.

        Args:
            vacancy_id: Vacancy identifier.
            candidate_id: Candidate identifier.

        Returns:
            list[PipelineTransition]: Ordered transition history.
        """
        return list(
            self._session.query(PipelineTransition)
            .filter(
                PipelineTransition.vacancy_id == vacancy_id,
                PipelineTransition.candidate_id == candidate_id,
            )
            .order_by(
                PipelineTransition.transitioned_at.asc(),
                PipelineTransition.transition_id.asc(),
            )
            .all()
        )

    def get_latest_transitions_by_vacancy(
        self,
        *,
        vacancy_id: str,
        candidate_ids: list[str],
    ) -> dict[str, PipelineTransition]:
        """Batch-load latest vacancy transitions for multiple candidates.

        Args:
            vacancy_id: Vacancy identifier that scopes the lookup.
            candidate_ids: Candidate identifiers resolved in one query.

        Returns:
            dict[str, PipelineTransition]: Mapping of `candidate_id -> latest transition`.
        """
        if not candidate_ids:
            return {}

        rows = (
            self._session.query(PipelineTransition)
            .filter(
                PipelineTransition.vacancy_id == vacancy_id,
                PipelineTransition.candidate_id.in_(candidate_ids),
            )
            .order_by(
                PipelineTransition.candidate_id.asc(),
                PipelineTransition.transitioned_at.desc(),
                PipelineTransition.transition_id.desc(),
            )
            .all()
        )
        transitions: dict[str, PipelineTransition] = {}
        for row in rows:
            transitions.setdefault(row.candidate_id, row)
        return transitions

    def get_latest_transitions_for_vacancy(
        self,
        *,
        vacancy_id: str,
    ) -> dict[str, PipelineTransition]:
        """Load latest transition rows for every candidate linked to one vacancy.

        Args:
            vacancy_id: Vacancy identifier that scopes the lookup.

        Returns:
            dict[str, PipelineTransition]: Mapping of `candidate_id -> latest transition`.
        """
        rows = (
            self._session.query(PipelineTransition)
            .filter(PipelineTransition.vacancy_id == vacancy_id)
            .order_by(
                PipelineTransition.candidate_id.asc(),
                PipelineTransition.transitioned_at.desc(),
                PipelineTransition.transition_id.desc(),
            )
            .all()
        )
        transitions: dict[str, PipelineTransition] = {}
        for row in rows:
            transitions.setdefault(row.candidate_id, row)
        return transitions

    def get_latest_transitions_for_vacancies(
        self,
        *,
        vacancy_ids: list[str],
    ) -> dict[tuple[str, str], PipelineTransition]:
        """Load latest transition rows for every candidate across multiple vacancies.

        Args:
            vacancy_ids: Vacancy identifiers resolved in one query.

        Returns:
            dict[tuple[str, str], PipelineTransition]: Mapping of `(vacancy_id, candidate_id)` to
                the latest transition row.
        """
        if not vacancy_ids:
            return {}

        rows = (
            self._session.query(PipelineTransition)
            .filter(PipelineTransition.vacancy_id.in_(vacancy_ids))
            .order_by(
                PipelineTransition.vacancy_id.asc(),
                PipelineTransition.candidate_id.asc(),
                PipelineTransition.transitioned_at.desc(),
                PipelineTransition.transition_id.desc(),
            )
            .all()
        )
        transitions: dict[tuple[str, str], PipelineTransition] = {}
        for row in rows:
            transitions.setdefault((row.vacancy_id, row.candidate_id), row)
        return transitions
