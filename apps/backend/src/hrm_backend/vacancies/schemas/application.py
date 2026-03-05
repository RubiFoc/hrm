"""Schemas for public candidate applications to vacancies."""

from __future__ import annotations

from datetime import datetime
from typing import Final, Literal
from uuid import UUID

from pydantic import BaseModel

PublicApplyReasonCode = Literal[
    "rate_limited",
    "honeypot_triggered",
    "duplicate_submission",
    "cooldown_active",
    "validation_failed",
]
PUBLIC_APPLY_REASON_RATE_LIMITED: Final[PublicApplyReasonCode] = "rate_limited"
PUBLIC_APPLY_REASON_HONEYPOT_TRIGGERED: Final[PublicApplyReasonCode] = "honeypot_triggered"
PUBLIC_APPLY_REASON_DUPLICATE_SUBMISSION: Final[PublicApplyReasonCode] = "duplicate_submission"
PUBLIC_APPLY_REASON_COOLDOWN_ACTIVE: Final[PublicApplyReasonCode] = "cooldown_active"
PUBLIC_APPLY_REASON_VALIDATION_FAILED: Final[PublicApplyReasonCode] = "validation_failed"


class PublicVacancyApplicationResponse(BaseModel):
    """Response payload for successful public vacancy application."""

    vacancy_id: UUID
    candidate_id: UUID
    document_id: UUID
    parsing_job_id: UUID
    transition_id: UUID
    applied_at: datetime
