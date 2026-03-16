"""Create durable automation execution log tables."""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "20260316000023"
down_revision = "20260316000022"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Create automation execution run/action tables and supporting indexes."""
    op.create_table(
        "automation_execution_runs",
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("trigger_event_id", sa.String(length=36), nullable=False),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("correlation_id", sa.String(length=64), nullable=True),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("planned_action_count", sa.Integer(), nullable=False),
        sa.Column("succeeded_action_count", sa.Integer(), nullable=False),
        sa.Column("deduped_action_count", sa.Integer(), nullable=False),
        sa.Column("failed_action_count", sa.Integer(), nullable=False),
        sa.Column("error_kind", sa.String(length=128), nullable=True),
        sa.Column("error_text", sa.String(length=1024), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("run_id"),
    )
    op.create_index(
        "ix_automation_execution_runs_event_trigger_time",
        "automation_execution_runs",
        ["event_type", "trigger_event_id", "event_time"],
        unique=False,
    )
    op.create_index(
        "ix_automation_execution_runs_status_started_at",
        "automation_execution_runs",
        ["status", "started_at"],
        unique=False,
    )
    op.create_index(
        "ix_automation_execution_runs_correlation_id",
        "automation_execution_runs",
        ["correlation_id"],
        unique=False,
    )
    op.create_index(
        "ix_automation_execution_runs_trace_id",
        "automation_execution_runs",
        ["trace_id"],
        unique=False,
    )

    op.create_table(
        "automation_action_executions",
        sa.Column("action_execution_id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=36), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("rule_id", sa.String(length=36), nullable=False),
        sa.Column("recipient_staff_id", sa.Uuid(as_uuid=False), nullable=False),
        sa.Column("recipient_role", sa.String(length=32), nullable=False),
        sa.Column("source_type", sa.String(length=64), nullable=False),
        sa.Column("source_id", sa.String(length=36), nullable=False),
        sa.Column("dedupe_key", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("trace_id", sa.String(length=64), nullable=False),
        sa.Column("result_notification_id", sa.String(length=36), nullable=True),
        sa.Column("error_kind", sa.String(length=128), nullable=True),
        sa.Column("error_text", sa.String(length=1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["automation_execution_runs.run_id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("action_execution_id"),
    )
    op.create_index(
        "ix_automation_action_executions_run_id",
        "automation_action_executions",
        ["run_id"],
        unique=False,
    )
    op.create_index(
        "ix_automation_action_executions_status_updated_at",
        "automation_action_executions",
        ["status", "updated_at"],
        unique=False,
    )
    op.create_index(
        "ix_automation_action_executions_dedupe_key",
        "automation_action_executions",
        ["dedupe_key"],
        unique=False,
    )


def downgrade() -> None:
    """Drop automation execution log tables and supporting indexes."""
    op.drop_index(
        "ix_automation_action_executions_dedupe_key",
        table_name="automation_action_executions",
    )
    op.drop_index(
        "ix_automation_action_executions_status_updated_at",
        table_name="automation_action_executions",
    )
    op.drop_index(
        "ix_automation_action_executions_run_id",
        table_name="automation_action_executions",
    )
    op.drop_table("automation_action_executions")

    op.drop_index(
        "ix_automation_execution_runs_trace_id",
        table_name="automation_execution_runs",
    )
    op.drop_index(
        "ix_automation_execution_runs_correlation_id",
        table_name="automation_execution_runs",
    )
    op.drop_index(
        "ix_automation_execution_runs_status_started_at",
        table_name="automation_execution_runs",
    )
    op.drop_index(
        "ix_automation_execution_runs_event_trigger_time",
        table_name="automation_execution_runs",
    )
    op.drop_table("automation_execution_runs")

