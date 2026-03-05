"""Schemas for CV parsing status API."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

CVParsingStatus = Literal["queued", "running", "succeeded", "failed"]


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
