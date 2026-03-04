"""SQLAlchemy models for candidate domain."""

from hrm_backend.candidates.models.document import CandidateDocument
from hrm_backend.candidates.models.parsing_job import CVParsingJob
from hrm_backend.candidates.models.profile import CandidateProfile

__all__ = ["CandidateProfile", "CandidateDocument", "CVParsingJob"]
