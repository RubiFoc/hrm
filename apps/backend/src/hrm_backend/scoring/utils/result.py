"""Canonical scoring payload definitions shared across scoring components."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MatchScoreEvidenceItem(BaseModel):
    """One evidence snippet supporting a scoring decision."""

    model_config = ConfigDict(extra="forbid")

    requirement: str = Field(min_length=1, max_length=512)
    snippet: str = Field(min_length=1)
    source_field: str | None = Field(default=None, max_length=128)

    @field_validator("requirement", "snippet", "source_field")
    @classmethod
    def _strip_optional_text(cls, value: str | None) -> str | None:
        """Strip text fields and reject empty strings."""
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty when provided")
        return normalized


class MatchScoreResult(BaseModel):
    """Structured scoring payload persisted as the canonical score artifact."""

    model_config = ConfigDict(extra="forbid")

    score: float = Field(ge=0, le=100)
    confidence: float = Field(ge=0, le=1)
    summary: str = Field(min_length=1)
    matched_requirements: list[str] = Field(default_factory=list)
    missing_requirements: list[str] = Field(default_factory=list)
    evidence: list[MatchScoreEvidenceItem] = Field(default_factory=list)
    model_name: str = Field(min_length=1, max_length=128)
    model_version: str = Field(min_length=1, max_length=128)

    @field_validator("summary", "model_name", "model_version")
    @classmethod
    def _strip_text(cls, value: str) -> str:
        """Strip text fields and reject empty strings."""
        normalized = value.strip()
        if not normalized:
            raise ValueError("must be non-empty")
        return normalized

    @field_validator("matched_requirements", "missing_requirements", mode="before")
    @classmethod
    def _normalize_requirement_lists(cls, value: object) -> list[str]:
        """Normalize requirement lists into unique non-empty strings."""
        if value is None:
            return []
        if not isinstance(value, list):
            raise ValueError("must be a list")

        items: list[str] = []
        for raw_item in value:
            normalized = str(raw_item).strip()
            if normalized and normalized not in items:
                items.append(normalized)
        return items

