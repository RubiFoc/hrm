"""Schemas for employee referral submissions and review workflows."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from hrm_backend.vacancies.schemas.pipeline import PipelineStage, PipelineTransitionResponse


class ReferralCreate(BaseModel):
    """Typed payload for persisting a referral record.

    Attributes:
        vacancy_id: Target vacancy identifier.
        candidate_id: Linked candidate identifier when available.
        referrer_employee_id: Referrer employee profile identifier.
        bonus_owner_employee_id: Bonus owner employee identifier.
        full_name: Candidate full name.
        phone: Candidate phone number.
        email: Candidate email address.
        cv_document_id: Candidate document identifier for the submitted CV.
        consent_confirmed_at: Consent confirmation timestamp.
        submitted_at: Submission timestamp.
    """

    model_config = ConfigDict(extra="forbid")

    vacancy_id: UUID
    candidate_id: UUID | None
    referrer_employee_id: UUID
    bonus_owner_employee_id: UUID
    full_name: str = Field(min_length=1, max_length=256)
    phone: str = Field(min_length=3, max_length=64)
    email: str = Field(min_length=3, max_length=256)
    cv_document_id: UUID | None
    consent_confirmed_at: datetime
    submitted_at: datetime


class ReferralSubmitResponse(BaseModel):
    """Response payload for employee referral submissions."""

    referral_id: UUID
    vacancy_id: UUID
    candidate_id: UUID | None
    bonus_owner_employee_id: UUID
    submitted_at: datetime
    current_stage: PipelineStage | None
    current_stage_at: datetime | None
    is_duplicate: bool = False


class ReferralListItemResponse(BaseModel):
    """Referral list row enriched with vacancy, candidate, and referrer context."""

    referral_id: UUID
    vacancy_id: UUID
    vacancy_title: str
    candidate_id: UUID | None
    candidate_full_name: str
    candidate_email: str
    candidate_phone: str | None
    referrer_employee_id: UUID
    referrer_full_name: str | None
    bonus_owner_employee_id: UUID
    submitted_at: datetime
    current_stage: PipelineStage | None
    current_stage_at: datetime | None


class ReferralListResponse(BaseModel):
    """Paginated referral list response."""

    items: list[ReferralListItemResponse]
    total: int = Field(ge=0)
    limit: int = Field(ge=1)
    offset: int = Field(ge=0)


class ReferralReviewRequest(BaseModel):
    """Input payload for HR/manager referral review transitions."""

    model_config = ConfigDict(extra="forbid")

    to_stage: PipelineStage
    reason: str | None = Field(default=None, max_length=2048)


class ReferralReviewResponse(BaseModel):
    """Response payload for referral review transitions."""

    referral_id: UUID
    transition: PipelineTransitionResponse
