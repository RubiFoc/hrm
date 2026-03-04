"""DAO for candidate profile persistence operations."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.candidates.models.profile import CandidateProfile
from hrm_backend.candidates.schemas.profile import CandidateCreateRequest, CandidateUpdateRequest


class CandidateProfileDAO:
    """Data-access helper for candidate profile rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def create_profile(
        self,
        payload: CandidateCreateRequest,
        owner_subject_id: str,
    ) -> CandidateProfile:
        """Insert one candidate profile.

        Args:
            payload: Candidate profile input payload.
            owner_subject_id: Resolved owner subject identifier.

        Returns:
            CandidateProfile: Persisted profile entity.
        """
        entity = CandidateProfile(
            owner_subject_id=owner_subject_id,
            first_name=payload.first_name,
            last_name=payload.last_name,
            email=str(payload.email),
            phone=payload.phone,
            location=payload.location,
            current_title=payload.current_title,
            extra_data=payload.extra_data,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_by_email(self, email: str) -> CandidateProfile | None:
        """Fetch candidate profile by normalized e-mail."""
        normalized = email.strip().lower()
        return (
            self._session.query(CandidateProfile)
            .filter(CandidateProfile.email == normalized)
            .first()
        )

    def get_by_id(self, candidate_id: str) -> CandidateProfile | None:
        """Fetch candidate profile by identifier.

        Args:
            candidate_id: Candidate identifier.

        Returns:
            CandidateProfile | None: Matched profile or `None`.
        """
        return self._session.get(CandidateProfile, candidate_id)

    def list_profiles(self) -> list[CandidateProfile]:
        """Load all candidate profiles ordered by creation time.

        Returns:
            list[CandidateProfile]: Candidate profiles ordered ascending by timestamp.
        """
        return list(
            self._session.query(CandidateProfile)
            .order_by(CandidateProfile.created_at.asc(), CandidateProfile.candidate_id.asc())
            .all()
        )

    def update_profile(
        self,
        entity: CandidateProfile,
        payload: CandidateUpdateRequest,
    ) -> CandidateProfile:
        """Apply partial update to existing profile.

        Args:
            entity: Existing candidate profile.
            payload: Partial update request.

        Returns:
            CandidateProfile: Updated profile entity.
        """
        update_payload = payload.model_dump(exclude_none=True)
        for field_name, value in update_payload.items():
            if field_name == "email" and value is not None:
                setattr(entity, field_name, str(value))
            else:
                setattr(entity, field_name, value)

        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity
