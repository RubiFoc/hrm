"""add employee key revocation columns

Revision ID: 20260305000007
Revises: 20260304000006
Create Date: 2026-03-05 18:30:00
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20260305000007"
down_revision = "20260304000006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add employee registration key revocation metadata columns."""
    op.add_column(
        "employee_registration_keys",
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "employee_registration_keys",
        sa.Column("revoked_by_staff_id", sa.Uuid(as_uuid=False), nullable=True),
    )
    op.create_foreign_key(
        "fk_emp_reg_keys_revoked_by_staff",
        "employee_registration_keys",
        "staff_accounts",
        ["revoked_by_staff_id"],
        ["staff_id"],
        ondelete="SET NULL",
    )
    op.create_index(
        "ix_employee_registration_keys_revoked_at",
        "employee_registration_keys",
        ["revoked_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop employee registration key revocation metadata columns."""
    op.drop_index(
        "ix_employee_registration_keys_revoked_at",
        table_name="employee_registration_keys",
    )
    op.drop_constraint(
        "fk_emp_reg_keys_revoked_by_staff",
        "employee_registration_keys",
        type_="foreignkey",
    )
    op.drop_column("employee_registration_keys", "revoked_by_staff_id")
    op.drop_column("employee_registration_keys", "revoked_at")
