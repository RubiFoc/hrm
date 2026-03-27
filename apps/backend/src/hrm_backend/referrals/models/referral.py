"""Persistence model for employee-submitted referrals."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column

from hrm_backend.core.models.base import Base


class EmployeeReferral(Base):
    """Referral record linking an employee recommendation to a vacancy.

    Attributes:
        referral_id: Unique referral identifier.
        vacancy_id: Target vacancy identifier.
        candidate_id: Linked candidate profile identifier when resolved.
        referrer_employee_id: Employee profile identifier of the referrer.
        bonus_owner_employee_id: Employee profile identifier that owns the referral bonus.
        full_name: Candidate full name provided by the referrer.
        phone: Candidate phone number.
        email: Candidate e-mail address (normalized).
        cv_document_id: Linked candidate document identifier for the submitted CV.
        consent_confirmed_at: Timestamp when consent was confirmed for processing the referral.
        submitted_at: Referral submission timestamp.
        updated_at: Last update timestamp.
    """

    __tablename__ = "employee_referrals"
    __table_args__ = (
        Index(
            "ux_employee_referrals_vacancy_email",
            "vacancy_id",
            "email",
            unique=True,
        ),
        Index("ix_employee_referrals_vacancy_id", "vacancy_id"),
        Index("ix_employee_referrals_referrer_employee_id", "referrer_employee_id"),
        Index("ix_employee_referrals_candidate_id", "candidate_id"),
        Index("ix_employee_referrals_bonus_owner_employee_id", "bonus_owner_employee_id"),
        Index("ix_employee_referrals_submitted_at", "submitted_at"),
    )

    referral_id: Mapped[str] = mapped_column(
        String(36),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    vacancy_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("vacancies.vacancy_id", ondelete="CASCADE"),
        nullable=False,
    )
    candidate_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidate_profiles.candidate_id", ondelete="SET NULL"),
        nullable=True,
    )
    referrer_employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employee_profiles.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    bonus_owner_employee_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("employee_profiles.employee_id", ondelete="CASCADE"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    cv_document_id: Mapped[str | None] = mapped_column(
        String(36),
        ForeignKey("candidate_documents.document_id", ondelete="SET NULL"),
        nullable=True,
    )
    consent_confirmed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )
    submitted_at: Mapped[datetime] = mapped_column(
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
