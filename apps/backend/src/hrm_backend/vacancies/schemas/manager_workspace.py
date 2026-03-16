"""Schemas for manager-safe hiring visibility on the existing vacancy route tree."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from hrm_backend.interviews.schemas.interview import InterviewStatus
from hrm_backend.vacancies.schemas.offer import OfferStatus
from hrm_backend.vacancies.schemas.pipeline import PipelineStage


class ManagerWorkspaceHiringSummaryResponse(BaseModel):
    """Aggregate hiring counters for the current manager workspace scope."""

    vacancy_count: int = Field(ge=0)
    open_vacancy_count: int = Field(ge=0)
    candidate_count: int = Field(ge=0)
    active_interview_count: int = Field(ge=0)
    upcoming_interview_count: int = Field(ge=0)


class ManagerWorkspaceVacancyListItemResponse(BaseModel):
    """One vacancy row visible in the manager hiring workspace."""

    vacancy_id: UUID
    title: str
    department: str
    status: str
    hiring_manager_staff_id: UUID | None
    hiring_manager_login: str | None
    candidate_count: int = Field(ge=0)
    active_interview_count: int = Field(ge=0)
    latest_activity_at: datetime | None
    created_at: datetime
    updated_at: datetime


class ManagerWorkspaceOverviewResponse(BaseModel):
    """Top-level manager workspace payload with aggregate hiring summary and visible vacancies."""

    summary: ManagerWorkspaceHiringSummaryResponse
    items: list[ManagerWorkspaceVacancyListItemResponse]


class ManagerWorkspaceStageSummaryResponse(BaseModel):
    """Stage counters for one manager-visible vacancy snapshot."""

    applied: int = Field(ge=0)
    screening: int = Field(ge=0)
    shortlist: int = Field(ge=0)
    interview: int = Field(ge=0)
    offer: int = Field(ge=0)
    hired: int = Field(ge=0)
    rejected: int = Field(ge=0)


class ManagerWorkspaceCandidateSnapshotSummaryResponse(BaseModel):
    """Aggregate counters for the selected vacancy inside manager workspace."""

    candidate_count: int = Field(ge=0)
    active_interview_count: int = Field(ge=0)
    upcoming_interview_count: int = Field(ge=0)
    stage_counts: ManagerWorkspaceStageSummaryResponse


class ManagerWorkspaceCandidateSnapshotItemResponse(BaseModel):
    """PII-redacted candidate row rendered inside the manager vacancy snapshot."""

    candidate_id: UUID
    stage: PipelineStage
    stage_updated_at: datetime
    interview_status: InterviewStatus | None
    interview_scheduled_start_at: datetime | None
    interview_scheduled_end_at: datetime | None
    interview_timezone: str | None
    offer_status: OfferStatus | None = None


class ManagerWorkspaceCandidateSnapshotResponse(BaseModel):
    """Vacancy-scoped candidate snapshot payload for the manager workspace."""

    vacancy: ManagerWorkspaceVacancyListItemResponse
    summary: ManagerWorkspaceCandidateSnapshotSummaryResponse
    items: list[ManagerWorkspaceCandidateSnapshotItemResponse]
