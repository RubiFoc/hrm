"""Persistence model for bootstrapped employee profiles."""

from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class EmployeeProfile(Base):
    """Initial employee profile created from a durable hire-conversion handoff.

    Attributes:
        employee_id: Unique employee profile identifier.
        hire_conversion_id: Source hire-conversion handoff identifier.
        vacancy_id: Source vacancy identifier for the accepted offer.
        candidate_id: Source candidate identifier that became an employee.
        first_name: Employee first name frozen from candidate snapshot.
        last_name: Employee last name frozen from candidate snapshot.
        email: Employee e-mail frozen from candidate snapshot.
        phone: Optional phone number frozen from candidate snapshot.
        location: Optional location frozen from candidate snapshot.
        current_title: Optional pre-hire title frozen from candidate snapshot.
        extra_data_json: Extensible profile data frozen from candidate snapshot.
        offer_terms_summary: Accepted-offer summary used for bootstrap visibility.
        start_date: Proposed employment start date from accepted offer.
        staff_account_id: Optional authenticated staff account linked to this employee profile
            for self-service portal access.
        created_by_staff_id: Staff subject that created the employee profile.
        created_at: Creation timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "employee_profiles"
    __table_args__ = (
        Index(
            "ux_employee_profiles_hire_conversion",
            "hire_conversion_id",
            unique=True,
        ),
        Index(
            "ux_employee_profiles_vacancy_candidate",
            "vacancy_id",
            "candidate_id",
            unique=True,
        ),
        Index(
            "ux_employee_profiles_staff_account",
            "staff_account_id",
            unique=True,
        ),
        Index("ix_employee_profiles_email", "email"),
    )

    employee_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    hire_conversion_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("hire_conversions.conversion_id", ondelete="CASCADE"),
        nullable=False,
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.vacancy_id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.candidate_id", ondelete="CASCADE"),
        nullable=False,
    )
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    location: Mapped[str | None] = mapped_column(String(256), nullable=True)
    current_title: Mapped[str | None] = mapped_column(String(256), nullable=True)
    extra_data_json: Mapped[dict[str, object]] = mapped_column(JSON, nullable=False, default=dict)
    offer_terms_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    staff_account_id: Mapped[str | None] = mapped_column(
        Uuid(as_uuid=False),
        ForeignKey("staff_accounts.staff_id", ondelete="SET NULL"),
        nullable=True,
    )
    created_by_staff_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
