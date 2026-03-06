"""Schemas for CV parsing status API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel

CVParsingStatus = Literal["queued", "running", "succeeded", "failed"]
DetectedCVLanguage = Literal["ru", "en", "mixed", "unknown"]


class CVAnalysisEvidenceItem(BaseModel):
    """Evidence link from one extracted field to CV source snippet."""

    field: str
    snippet: str
    start_offset: int
    end_offset: int
    page: int | None = None


class CVAnalysisResponse(BaseModel):
    """Canonical CV analysis payload for latest active candidate document."""

    candidate_id: UUID
    document_id: UUID
    detected_language: DetectedCVLanguage
    parsed_at: datetime
    parsed_profile: dict[str, Any]
    evidence: list[CVAnalysisEvidenceItem]


class CVParsingStatusResponse(BaseModel):
    """Current parsing job status for candidate CV."""

    candidate_id: UUID
    document_id: UUID
    job_id: UUID
    status: CVParsingStatus
    attempt_count: int
    last_error: str | None
    queued_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    updated_at: datetime
    analysis_ready: bool
    detected_language: DetectedCVLanguage
