"""Create automation rule storage table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316000022"
down_revision = "20260313000021"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create the automation_rules table and supporting indexes."""
    op.create_table(
        "automation_rules",
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("trigger", sa.String(length=128), nullable=False),
        sa.Column("conditions_json", sa.JSON(), nullable=True),
        sa.Column("actions_json", sa.JSON(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("updated_by_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("rule_id"),
    )
    op.create_index(
        "ix_automation_rules_trigger_active_priority",
        "automation_rules",
        ["trigger", "is_active", "priority"],
        unique=False,
    )
    op.create_index(
        "ix_automation_rules_updated_at",
        "automation_rules",
        ["updated_at"],
        unique=False,
    )


def downgrade() -> None:
    """Drop the automation_rules table and supporting indexes."""
    op.drop_index("ix_automation_rules_updated_at", table_name="automation_rules")
    op.drop_index(
        "ix_automation_rules_trigger_active_priority",
        table_name="automation_rules",
    )
    op.drop_table("automation_rules")

