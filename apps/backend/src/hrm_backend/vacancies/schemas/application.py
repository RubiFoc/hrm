"""Schemas for public candidate applications to vacancies."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class PublicVacancyApplicationResponse(BaseModel):
    """Response payload for successful public vacancy application."""

    vacancy_id: UUID
    candidate_id: UUID
    document_id: UUID
    parsing_job_id: UUID
    transition_id: UUID
    applied_at: datetime
