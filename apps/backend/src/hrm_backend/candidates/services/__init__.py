"""Business services for candidate domain."""

from hrm_backend.candidates.services.candidate_service import CandidateService
from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService

__all__ = ["CandidateService", "CVParsingWorkerService"]
