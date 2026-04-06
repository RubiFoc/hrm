"""Persistence model for vacancy salary-band history."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, Integer, Numeric, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class SalaryBand(Base):
    """Append-only salary band record for a vacancy.

    Attributes:
        band_id: Unique salary band identifier.
        vacancy_id: Vacancy identifier the band applies to.
        band_version: Monotonic version number per vacancy.
        min_amount: Minimum salary amount for the band.
        max_amount: Maximum salary amount for the band.
        currency: Currency code (fixed to BYN by policy).
        created_by_staff_id: HR staff identifier who created the band.
        created_at: Creation timestamp.
    """

    __tablename__ = "compensation_salary_bands"
    __table_args__ = (
        Index("ux_comp_salary_bands_vacancy_version", "vacancy_id", "band_version", unique=True),
        Index("ix_comp_salary_bands_vacancy_id", "vacancy_id"),
        Index("ix_comp_salary_bands_created_at", "created_at"),
    )

    band_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.vacancy_id", ondelete="CASCADE"),
        nullable=False,
    )
    band_version: Mapped[int] = mapped_column(Integer, nullable=False)
    min_amount: Mapped[float] = mapped_column(Numeric(12, 2, asdecimal=False), nullable=False)
    max_amount: Mapped[float] = mapped_column(Numeric(12, 2, asdecimal=False), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="BYN")
    created_by_staff_id: Mapped[str] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="RESTRICT"),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
