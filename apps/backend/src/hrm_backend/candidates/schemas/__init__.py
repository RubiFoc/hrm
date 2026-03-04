"""Pydantic schemas for candidate APIs and worker payloads."""

from hrm_backend.candidates.schemas.cv import (
    CandidateCVDownloadPayload,
    CandidateCVUploadResponse,
)
from hrm_backend.candidates.schemas.parsing import CVParsingStatusResponse
from hrm_backend.candidates.schemas.profile import (
    CandidateCreateRequest,
    CandidateListResponse,
    CandidateResponse,
    CandidateUpdateRequest,
)

__all__ = [
    "CandidateCreateRequest",
    "CandidateUpdateRequest",
    "CandidateResponse",
    "CandidateListResponse",
    "CandidateCVUploadResponse",
    "CandidateCVDownloadPayload",
    "CVParsingStatusResponse",
]
