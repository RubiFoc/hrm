"""Create employee referral table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260327000025"
down_revision = "20260319000024"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create employee referrals table and supporting indexes."""
    op.create_table(
        "employee_referrals",
        sa.Column("referral_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=True),
        sa.Column("referrer_employee_id", sa.String(length=36), nullable=False),
        sa.Column("bonus_owner_employee_id", sa.String(length=36), nullable=False),
        sa.Column("full_name", sa.String(length=256), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("cv_document_id", sa.String(length=36), nullable=True),
        sa.Column("consent_confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.vacancy_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["referrer_employee_id"],
            ["employee_profiles.employee_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["bonus_owner_employee_id"],
            ["employee_profiles.employee_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["cv_document_id"],
            ["candidate_documents.document_id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("referral_id"),
    )
    op.create_index(
        "ux_employee_referrals_vacancy_email",
        "employee_referrals",
        ["vacancy_id", "email"],
        unique=True,
    )
    op.create_index(
        "ix_employee_referrals_vacancy_id",
        "employee_referrals",
        ["vacancy_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_referrals_referrer_employee_id",
        "employee_referrals",
        ["referrer_employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_referrals_candidate_id",
        "employee_referrals",
        ["candidate_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_referrals_bonus_owner_employee_id",
        "employee_referrals",
        ["bonus_owner_employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_referrals_submitted_at",
        "employee_referrals",
        ["submitted_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop employee referral table and supporting indexes."""
    op.drop_index(
        "ix_employee_referrals_submitted_at",
        table_name="employee_referrals",
    )
    op.drop_index(
        "ix_employee_referrals_bonus_owner_employee_id",
        table_name="employee_referrals",
    )
    op.drop_index(
        "ix_employee_referrals_candidate_id",
        table_name="employee_referrals",
    )
    op.drop_index(
        "ix_employee_referrals_referrer_employee_id",
        table_name="employee_referrals",
    )
    op.drop_index(
        "ix_employee_referrals_vacancy_id",
        table_name="employee_referrals",
    )
    op.drop_index(
        "ux_employee_referrals_vacancy_email",
        table_name="employee_referrals",
    )
    op.drop_table("employee_referrals")
