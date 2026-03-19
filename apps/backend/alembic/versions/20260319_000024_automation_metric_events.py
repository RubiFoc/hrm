"""Create durable automation KPI metric event table."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260319000024"
down_revision = "20260316000023"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create automation metric event table and supporting indexes."""
    op.create_table(
        "automation_metric_events",
        sa.Column("metric_event_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("trigger_event_id", sa.String(length=36), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("outcome", sa.String(length=32), nullable=False),
        sa.Column("total_hr_operations_count", sa.Integer(), nullable=False),
        sa.Column("automated_hr_operations_count", sa.Integer(), nullable=False),
        sa.Column("planned_action_count", sa.Integer(), nullable=False),
        sa.Column("succeeded_action_count", sa.Integer(), nullable=False),
        sa.Column("deduped_action_count", sa.Integer(), nullable=False),
        sa.Column("failed_action_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("metric_event_id"),
    )
    op.create_index(
        "ux_automation_metric_events_event_trigger",
        "automation_metric_events",
        ["event_type", "trigger_event_id"],
        unique=True,
    )
    op.create_index(
        "ix_automation_metric_events_event_time",
        "automation_metric_events",
        ["event_time"],
        unique=False,
    )
    op.create_index(
        "ix_automation_metric_events_outcome",
        "automation_metric_events",
        ["outcome"],
        unique=False,
    )


def downgrade() -> None:
    """Drop automation metric event table and supporting indexes."""
    op.drop_index(
        "ix_automation_metric_events_outcome",
        table_name="automation_metric_events",
    )
    op.drop_index(
        "ix_automation_metric_events_event_time",
        table_name="automation_metric_events",
    )
    op.drop_index(
        "ux_automation_metric_events_event_trigger",
        table_name="automation_metric_events",
    )
    op.drop_table("automation_metric_events")
