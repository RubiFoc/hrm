"""add employee profiles table

Revision ID: 20260310000014
Revises: 20260310000013
Create Date: 2026-03-11 00:45:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260310000014"
down_revision = "20260310000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create bootstrapped employee profile table."""
    op.create_table(
        "employee_profiles",
        sa.Column("employee_id", sa.String(length=36), nullable=False),
        sa.Column("hire_conversion_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("candidate_id", sa.String(length=36), nullable=False),
        sa.Column("first_name", sa.String(length=128), nullable=False),
        sa.Column("last_name", sa.String(length=128), nullable=False),
        sa.Column("email", sa.String(length=256), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("location", sa.String(length=256), nullable=True),
        sa.Column("current_title", sa.String(length=256), nullable=True),
        sa.Column("extra_data_json", sa.JSON(), nullable=False),
        sa.Column("offer_terms_summary", sa.Text(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=True),
        sa.Column("created_by_staff_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["hire_conversion_id"],
            ["hire_conversions.conversion_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.vacancy_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["candidate_id"],
            ["candidate_profiles.candidate_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("employee_id"),
    )
    op.create_index(
        "ux_employee_profiles_hire_conversion",
        "employee_profiles",
        ["hire_conversion_id"],
        unique=True,
    )
    op.create_index(
        "ux_employee_profiles_vacancy_candidate",
        "employee_profiles",
        ["vacancy_id", "candidate_id"],
        unique=True,
    )
    op.create_index(
        "ix_employee_profiles_email",
        "employee_profiles",
        ["email"],
        unique=False,
    )


def downgrade() -> None:
    """Drop bootstrapped employee profile table."""
    op.drop_index("ix_employee_profiles_email", table_name="employee_profiles")
    op.drop_index("ux_employee_profiles_vacancy_candidate", table_name="employee_profiles")
    op.drop_index("ux_employee_profiles_hire_conversion", table_name="employee_profiles")
    op.drop_table("employee_profiles")
