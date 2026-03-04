"""PostgreSQL adapters for candidate domain."""

from hrm_backend.candidates.dao.candidate_document_dao import CandidateDocumentDAO
from hrm_backend.candidates.dao.candidate_profile_dao import CandidateProfileDAO
from hrm_backend.candidates.dao.cv_parsing_job_dao import CVParsingJobDAO

__all__ = ["CandidateProfileDAO", "CandidateDocumentDAO", "CVParsingJobDAO"]
