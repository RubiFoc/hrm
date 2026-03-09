"""DAO for explainable match score artifact persistence."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy.orm import Session

from hrm_backend.scoring.models.score_artifact import MatchScoreArtifact
from hrm_backend.scoring.utils.result import MatchScoreResult


class MatchScoreArtifactDAO:
    """Data-access helper for persisted scoring artifacts."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def get_by_job_id(self, job_id: str) -> MatchScoreArtifact | None:
        """Fetch score artifact by scoring job identifier."""
        return (
            self._session.query(MatchScoreArtifact)
            .filter(MatchScoreArtifact.job_id == job_id)
            .first()
        )

    def upsert_artifact(
        self,
        *,
        job_id: str,
        vacancy_id: str,
        candidate_id: str,
        document_id: str,
        payload: MatchScoreResult,
    ) -> MatchScoreArtifact:
        """Insert or replace persisted artifact for one scoring job."""
        entity = self.get_by_job_id(job_id)
        if entity is None:
            entity = MatchScoreArtifact(
                job_id=job_id,
                vacancy_id=vacancy_id,
                candidate_id=candidate_id,
                document_id=document_id,
            )

        entity.score = payload.score
        entity.confidence = payload.confidence
        entity.summary = payload.summary
        entity.matched_requirements_json = list(payload.matched_requirements)
        entity.missing_requirements_json = list(payload.missing_requirements)
        entity.evidence_json = [item.model_dump() for item in payload.evidence]
        entity.model_name = payload.model_name
        entity.model_version = payload.model_version
        entity.scored_at = datetime.now(UTC)

        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

