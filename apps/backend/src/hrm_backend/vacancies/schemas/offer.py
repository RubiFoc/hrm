"""Offer lifecycle request/response schemas."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

OfferStatus = Literal["draft", "sent", "accepted", "declined"]


class OfferUpsertRequest(BaseModel):
    """Input payload for creating or updating one draft offer."""

    model_config = ConfigDict(extra="forbid")

    terms_summary: str = Field(min_length=1, max_length=4000)
    proposed_start_date: date | None = None
    expires_at: date | None = None
    note: str | None = Field(default=None, max_length=4000)

    @field_validator("terms_summary")
    @classmethod
    def validate_terms_summary(cls, value: str) -> str:
        """Trim terms summary and reject whitespace-only values."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("offer terms summary must not be blank")
        return normalized

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        """Trim optional note field to keep API storage deterministic."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

class OfferDecisionRequest(BaseModel):
    """Optional note payload for recording accepted or declined offer status."""

    model_config = ConfigDict(extra="forbid")

    note: str | None = Field(default=None, max_length=4000)

    @field_validator("note")
    @classmethod
    def normalize_note(cls, value: str | None) -> str | None:
        """Trim optional decision note to stable storage form."""
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None


class OfferResponse(BaseModel):
    """Canonical staff-facing offer lifecycle payload."""

    offer_id: UUID
    vacancy_id: UUID
    candidate_id: UUID
    status: OfferStatus
    terms_summary: str | None
    proposed_start_date: date | None
    expires_at: date | None
    note: str | None
    sent_at: datetime | None
    sent_by_staff_id: UUID | None
    decision_at: datetime | None
    decision_note: str | None
    decision_recorded_by_staff_id: UUID | None
    created_at: datetime
    updated_at: datetime
