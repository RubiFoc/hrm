"""Unit tests for audit export rendering helpers."""

from __future__ import annotations

import csv
import json
from datetime import UTC, datetime
from io import StringIO
from uuid import UUID

from hrm_backend.audit.schemas.read import AuditEventListItem
from hrm_backend.audit.utils.exports import (
    AUDIT_EVENT_EXPORT_COLUMNS,
    render_audit_events_csv,
    render_audit_events_jsonl,
)


def _build_item(*, event_id: str, occurred_at: datetime, action: str) -> AuditEventListItem:
    """Build one deterministic audit event list item for export rendering tests."""
    return AuditEventListItem(
        event_id=UUID(event_id),
        occurred_at=occurred_at,
        source="api",
        actor_sub="actor-1",
        actor_role="admin",
        action=action,
        resource_type="auth",
        resource_id=None,
        result="success",
        reason=None,
        correlation_id="corr-1",
        ip="127.0.0.1",
        user_agent="pytest",
    )


def test_render_audit_events_csv_has_stable_header_and_row_order() -> None:
    """Verify CSV export keeps deterministic column order and uses item order."""
    items = [
        _build_item(
            event_id="00000000-0000-0000-0000-000000000201",
            occurred_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
            action="auth.login",
        ),
        _build_item(
            event_id="00000000-0000-0000-0000-000000000202",
            occurred_at=datetime(2026, 3, 16, 11, 0, tzinfo=UTC),
            action="auth.logout",
        ),
    ]

    payload = render_audit_events_csv(items)
    reader = csv.reader(StringIO(payload.decode("utf-8")))
    rows = list(reader)

    assert tuple(rows[0]) == AUDIT_EVENT_EXPORT_COLUMNS
    assert rows[1][0] == "00000000-0000-0000-0000-000000000201"
    assert rows[2][0] == "00000000-0000-0000-0000-000000000202"


def test_render_audit_events_jsonl_is_parseable_and_newline_terminated() -> None:
    """Verify JSONL export is newline-separated and JSON-parsable."""
    items = [
        _build_item(
            event_id="00000000-0000-0000-0000-000000000211",
            occurred_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
            action="audit.event:list",
        )
    ]

    payload = render_audit_events_jsonl(items)
    assert payload.endswith(b"\n")
    lines = payload.decode("utf-8").splitlines()
    assert len(lines) == 1
    assert json.loads(lines[0]) == items[0].model_dump(mode="json")


def test_export_helpers_are_deterministic_for_same_input() -> None:
    """Verify both CSV and JSONL renderers return stable bytes for the same inputs."""
    items = [
        _build_item(
            event_id="00000000-0000-0000-0000-000000000301",
            occurred_at=datetime(2026, 3, 16, 10, 0, tzinfo=UTC),
            action="auth.me",
        )
    ]

    assert render_audit_events_csv(items) == render_audit_events_csv(items)
    assert render_audit_events_jsonl(items) == render_audit_events_jsonl(items)

