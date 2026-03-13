"""KPI snapshot persistence model."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import Date, DateTime, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class KpiSnapshot(Base):
    """Monthly KPI snapshot row for a single metric.

    Attributes:
        snapshot_id: Unique snapshot row identifier.
        period_month: First day of the month that this snapshot represents.
        metric_key: Stable KPI metric identifier.
        metric_value: Aggregated metric value for the selected month.
        generated_at: Timestamp when the snapshot was generated.
    """

    __tablename__ = "kpi_snapshots"
    __table_args__ = (
        Index(
            "ux_kpi_snapshots_period_metric",
            "period_month",
            "metric_key",
            unique=True,
        ),
        Index("ix_kpi_snapshots_period_month", "period_month"),
    )

    snapshot_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    period_month: Mapped[date] = mapped_column(Date, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), nullable=False)
    metric_value: Mapped[int] = mapped_column(Integer, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
