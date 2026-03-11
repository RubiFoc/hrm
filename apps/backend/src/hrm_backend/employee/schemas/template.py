"""Request, response, and internal schemas for onboarding checklist templates."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class OnboardingChecklistTemplateItemWrite(BaseModel):
    """Checklist item payload used for create and update operations."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None
    sort_order: int = Field(ge=0)
    is_required: bool = True


class OnboardingChecklistTemplateCreateRequest(BaseModel):
    """Staff-facing request payload for creating onboarding checklist templates."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    is_active: bool = False
    items: list[OnboardingChecklistTemplateItemWrite] = Field(min_length=1)


class OnboardingChecklistTemplateUpdateRequest(BaseModel):
    """Staff-facing request payload for replacing onboarding checklist templates."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    is_active: bool = False
    items: list[OnboardingChecklistTemplateItemWrite] = Field(min_length=1)


class OnboardingChecklistTemplateItemUpsert(BaseModel):
    """Internal normalized checklist item payload for persistence operations."""

    model_config = ConfigDict(extra="forbid")

    code: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    description: str | None = None
    sort_order: int = Field(ge=0)
    is_required: bool = True


class OnboardingChecklistTemplateUpsert(BaseModel):
    """Internal normalized template payload for create and update operations."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=128)
    description: str | None = None
    is_active: bool = False
    items: list[OnboardingChecklistTemplateItemUpsert] = Field(min_length=1)


class OnboardingChecklistTemplateItemResponse(BaseModel):
    """API representation of one onboarding checklist template item."""

    template_item_id: UUID
    code: str
    title: str
    description: str | None
    sort_order: int
    is_required: bool


class OnboardingChecklistTemplateResponse(BaseModel):
    """API representation of one onboarding checklist template."""

    template_id: UUID
    name: str
    description: str | None
    is_active: bool
    items: list[OnboardingChecklistTemplateItemResponse]
    created_by_staff_id: UUID
    created_at: datetime
    updated_at: datetime


class OnboardingChecklistTemplateListResponse(BaseModel):
    """List payload for onboarding checklist templates."""

    items: list[OnboardingChecklistTemplateResponse]
