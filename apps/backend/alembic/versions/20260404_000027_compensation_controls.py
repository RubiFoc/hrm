"""add compensation controls tables

Revision ID: 20260404000027
Revises: 20260327000026
Create Date: 2026-04-04 12:00:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260404000027"
down_revision = "20260327000026"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add compensation controls tables and audit snapshots."""
    op.add_column(
        "audit_events",
        sa.Column("before_snapshot_json", sa.JSON(), nullable=True),
    )
    op.add_column(
        "audit_events",
        sa.Column("after_snapshot_json", sa.JSON(), nullable=True),
    )

    op.create_table(
        "compensation_raise_requests",
        sa.Column("request_id", sa.String(length=36), nullable=False),
        sa.Column("employee_id", sa.String(length=36), nullable=False),
        sa.Column("requested_by_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("proposed_base_salary", sa.Numeric(12, 2, asdecimal=False), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("leader_decision_by_staff_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("leader_decision_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("leader_decision_note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee_profiles.employee_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["requested_by_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["leader_decision_by_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("request_id"),
    )
    op.create_index(
        "ix_comp_raise_requests_employee_id",
        "compensation_raise_requests",
        ["employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_comp_raise_requests_status",
        "compensation_raise_requests",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_comp_raise_requests_requested_at",
        "compensation_raise_requests",
        ["requested_at"],
        unique=False,
    )

    op.create_table(
        "compensation_raise_confirmations",
        sa.Column("confirmation_id", sa.String(length=36), nullable=False),
        sa.Column("raise_request_id", sa.String(length=36), nullable=False),
        sa.Column("manager_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["raise_request_id"],
            ["compensation_raise_requests.request_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["manager_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("confirmation_id"),
    )
    op.create_index(
        "ux_comp_raise_confirmations_request_manager",
        "compensation_raise_confirmations",
        ["raise_request_id", "manager_staff_id"],
        unique=True,
    )
    op.create_index(
        "ix_comp_raise_confirmations_request_id",
        "compensation_raise_confirmations",
        ["raise_request_id"],
        unique=False,
    )

    op.create_table(
        "compensation_salary_bands",
        sa.Column("band_id", sa.String(length=36), nullable=False),
        sa.Column("vacancy_id", sa.String(length=36), nullable=False),
        sa.Column("band_version", sa.Integer(), nullable=False),
        sa.Column("min_amount", sa.Numeric(12, 2, asdecimal=False), nullable=False),
        sa.Column("max_amount", sa.Numeric(12, 2, asdecimal=False), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("created_by_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["vacancy_id"],
            ["vacancies.vacancy_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("band_id"),
    )
    op.create_index(
        "ux_comp_salary_bands_vacancy_version",
        "compensation_salary_bands",
        ["vacancy_id", "band_version"],
        unique=True,
    )
    op.create_index(
        "ix_comp_salary_bands_vacancy_id",
        "compensation_salary_bands",
        ["vacancy_id"],
        unique=False,
    )
    op.create_index(
        "ix_comp_salary_bands_created_at",
        "compensation_salary_bands",
        ["created_at"],
        unique=False,
    )

    op.create_table(
        "compensation_bonus_entries",
        sa.Column("bonus_id", sa.String(length=36), nullable=False),
        sa.Column("employee_id", sa.String(length=36), nullable=False),
        sa.Column("period_month", sa.Date(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2, asdecimal=False), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_by_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("updated_by_staff_id", sa.Uuid(as_uuid=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee_profiles.employee_id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["created_by_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_staff_id"],
            ["staff_accounts.staff_id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("bonus_id"),
    )
    op.create_index(
        "ux_comp_bonus_entries_employee_month",
        "compensation_bonus_entries",
        ["employee_id", "period_month"],
        unique=True,
    )
    op.create_index(
        "ix_comp_bonus_entries_employee_id",
        "compensation_bonus_entries",
        ["employee_id"],
        unique=False,
    )
    op.create_index(
        "ix_comp_bonus_entries_period_month",
        "compensation_bonus_entries",
        ["period_month"],
        unique=False,
    )


def downgrade() -> None:
    """Drop compensation controls tables and audit snapshots."""
    op.drop_index(
        "ix_comp_bonus_entries_period_month",
        table_name="compensation_bonus_entries",
    )
    op.drop_index(
        "ix_comp_bonus_entries_employee_id",
        table_name="compensation_bonus_entries",
    )
    op.drop_index(
        "ux_comp_bonus_entries_employee_month",
        table_name="compensation_bonus_entries",
    )
    op.drop_table("compensation_bonus_entries")

    op.drop_index(
        "ix_comp_salary_bands_created_at",
        table_name="compensation_salary_bands",
    )
    op.drop_index(
        "ix_comp_salary_bands_vacancy_id",
        table_name="compensation_salary_bands",
    )
    op.drop_index(
        "ux_comp_salary_bands_vacancy_version",
        table_name="compensation_salary_bands",
    )
    op.drop_table("compensation_salary_bands")

    op.drop_index(
        "ix_comp_raise_confirmations_request_id",
        table_name="compensation_raise_confirmations",
    )
    op.drop_index(
        "ux_comp_raise_confirmations_request_manager",
        table_name="compensation_raise_confirmations",
    )
    op.drop_table("compensation_raise_confirmations")

    op.drop_index(
        "ix_comp_raise_requests_requested_at",
        table_name="compensation_raise_requests",
    )
    op.drop_index(
        "ix_comp_raise_requests_status",
        table_name="compensation_raise_requests",
    )
    op.drop_index(
        "ix_comp_raise_requests_employee_id",
        table_name="compensation_raise_requests",
    )
    op.drop_table("compensation_raise_requests")

    op.drop_column("audit_events", "after_snapshot_json")
    op.drop_column("audit_events", "before_snapshot_json")
