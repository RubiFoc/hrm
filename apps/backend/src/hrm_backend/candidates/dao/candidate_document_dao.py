"""DAO for candidate document metadata persistence."""

from __future__ import annotations

from sqlalchemy.orm import Session

from hrm_backend.candidates.models.document import CandidateDocument


class CandidateDocumentDAO:
    """Data-access helper for candidate CV metadata rows."""

    def __init__(self, session: Session) -> None:
        """Initialize DAO.

        Args:
            session: Active SQLAlchemy session.
        """
        self._session = session

    def deactivate_active_documents(self, candidate_id: str) -> None:
        """Mark current active CV rows as inactive for one candidate.

        Args:
            candidate_id: Candidate identifier.
        """
        self._session.query(CandidateDocument).filter(
            CandidateDocument.candidate_id == candidate_id,
            CandidateDocument.is_active.is_(True),
        ).update({"is_active": False}, synchronize_session=False)
        self._session.commit()

    def create_document(
        self,
        *,
        candidate_id: str,
        object_key: str,
        filename: str,
        mime_type: str,
        size_bytes: int,
        checksum_sha256: str,
        is_active: bool,
    ) -> CandidateDocument:
        """Insert new candidate document row.

        Args:
            candidate_id: Candidate profile identifier.
            object_key: Object storage key.
            filename: Original uploaded filename.
            mime_type: Validated MIME type.
            size_bytes: Uploaded bytes length.
            checksum_sha256: SHA-256 hex digest.
            is_active: Whether this row is active CV reference.

        Returns:
            CandidateDocument: Persisted document metadata entity.
        """
        entity = CandidateDocument(
            candidate_id=candidate_id,
            object_key=object_key,
            filename=filename,
            mime_type=mime_type,
            size_bytes=size_bytes,
            checksum_sha256=checksum_sha256,
            is_active=is_active,
        )
        self._session.add(entity)
        self._session.commit()
        self._session.refresh(entity)
        return entity

    def get_active_document(self, candidate_id: str) -> CandidateDocument | None:
        """Fetch active CV metadata for candidate.

        Args:
            candidate_id: Candidate profile identifier.

        Returns:
            CandidateDocument | None: Active metadata row or `None`.
        """
        return (
            self._session.query(CandidateDocument)
            .filter(
                CandidateDocument.candidate_id == candidate_id,
                CandidateDocument.is_active.is_(True),
            )
            .order_by(CandidateDocument.created_at.desc(), CandidateDocument.document_id.desc())
            .first()
        )

    def get_by_id(self, document_id: str) -> CandidateDocument | None:
        """Fetch candidate document by identifier.

        Args:
            document_id: Document identifier.

        Returns:
            CandidateDocument | None: Matched document row or `None`.
        """
        return self._session.get(CandidateDocument, document_id)
