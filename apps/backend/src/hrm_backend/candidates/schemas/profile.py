"""Candidate profile request and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


class CandidateCreateRequest(BaseModel):
    """Input payload for candidate profile creation.

    Attributes:
        owner_subject_id: Optional explicit owner subject id (used by HR).
        first_name: Candidate first name.
        last_name: Candidate last name.
        email: Candidate e-mail.
        phone: Optional phone number.
        location: Optional location/city.
        current_title: Optional current title.
        extra_data: Extensible profile fields.
    """

    model_config = ConfigDict(extra="forbid")

    owner_subject_id: str | None = Field(default=None, min_length=1, max_length=128)
    first_name: str = Field(min_length=1, max_length=128)
    last_name: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=256)
    phone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=256)
    current_title: str | None = Field(default=None, max_length=256)
    extra_data: dict[str, Any] = Field(default_factory=dict)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        """Validate and normalize e-mail value."""
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Invalid email format")
        return normalized


class CandidateUpdateRequest(BaseModel):
    """Partial update payload for candidate profiles."""

    model_config = ConfigDict(extra="forbid")

    first_name: str | None = Field(default=None, min_length=1, max_length=128)
    last_name: str | None = Field(default=None, min_length=1, max_length=128)
    email: str | None = Field(default=None, min_length=3, max_length=256)
    phone: str | None = Field(default=None, max_length=64)
    location: str | None = Field(default=None, max_length=256)
    current_title: str | None = Field(default=None, max_length=256)
    extra_data: dict[str, Any] | None = None

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str | None) -> str | None:
        """Validate and normalize optional e-mail value."""
        if value is None:
            return None
        normalized = value.strip().lower()
        if "@" not in normalized or "." not in normalized.rsplit("@", 1)[-1]:
            raise ValueError("Invalid email format")
        return normalized


class CandidateResponse(BaseModel):
    """Candidate profile API representation."""

    candidate_id: UUID
    owner_subject_id: str
    first_name: str
    last_name: str
    email: str
    phone: str | None
    location: str | None
    current_title: str | None
    extra_data: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class CandidateListResponse(BaseModel):
    """Candidate profile list payload."""

    items: list[CandidateResponse]
