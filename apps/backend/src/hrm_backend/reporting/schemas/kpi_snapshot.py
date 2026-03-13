"""Schemas for KPI snapshot read and rebuild APIs."""

from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hrm_backend.reporting.utils.dates import ensure_month_start

KPIMetricKey = Literal[
    "vacancies_created_count",
    "candidates_applied_count",
    "interviews_scheduled_count",
    "offers_sent_count",
    "offers_accepted_count",
    "hires_count",
    "onboarding_started_count",
    "onboarding_tasks_completed_count",
]


class KpiSnapshotRebuildRequest(BaseModel):
    """Payload for requesting a KPI snapshot rebuild for one month."""

    model_config = ConfigDict(extra="forbid")

    period_month: date

    @field_validator("period_month")
    @classmethod
    def validate_period_month(cls, value: date) -> date:
        """Ensure the period month is provided as the first day of month."""
        return ensure_month_start(value)


class KpiSnapshotQuery(BaseModel):
    """Query parameters for monthly KPI snapshot reads."""

    model_config = ConfigDict(extra="forbid")

    period_month: date

    @field_validator("period_month")
    @classmethod
    def validate_period_month(cls, value: date) -> date:
        """Ensure the period month is provided as the first day of month."""
        return ensure_month_start(value)


class KpiSnapshotMetric(BaseModel):
    """Metric payload for one KPI snapshot row."""

    model_config = ConfigDict(extra="forbid")

    metric_key: KPIMetricKey
    metric_value: int = Field(ge=0)
    generated_at: datetime | None = None


class KpiSnapshotReadResponse(BaseModel):
    """Monthly KPI snapshot response payload."""

    model_config = ConfigDict(extra="forbid")

    period_month: date
    metrics: list[KpiSnapshotMetric]
