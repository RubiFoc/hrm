"""Internal typed payloads for durable hire-conversion handoff records."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.employee.utils.conversions import HIRE_CONVERSION_STATUS_READY

HireConversionStatus = Literal["ready"]


class HireConversionCandidateSnapshot(BaseModel):
    """Frozen candidate fields required for later employee-profile bootstrap."""

    model_config = ConfigDict(extra="forbid")

    first_name: str
    last_name: str
    email: str
    phone: str | None = None
    location: str | None = None
    current_title: str | None = None
    extra_data: dict[str, object] = Field(default_factory=dict)


class HireConversionOfferSnapshot(BaseModel):
    """Frozen accepted-offer data required for later employee bootstrap."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["accepted"]
    terms_summary: str | None
    proposed_start_date: date | None = None
    expires_at: date | None = None
    note: str | None = None
    sent_at: datetime | None = None
    sent_by_staff_id: UUID | None = None
    decision_at: datetime | None = None
    decision_note: str | None = None
    decision_recorded_by_staff_id: UUID | None = None


class HireConversionCreate(BaseModel):
    """Internal service payload for one persisted hire-conversion handoff."""

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    candidate_id: UUID
    offer_id: UUID
    hired_transition_id: UUID
    status: HireConversionStatus = HIRE_CONVERSION_STATUS_READY
    candidate_snapshot: HireConversionCandidateSnapshot
    offer_snapshot: HireConversionOfferSnapshot
    converted_by_staff_id: UUID
