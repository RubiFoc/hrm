"""Unit tests for interview invitation token generation and hashing."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from hrm_backend.interviews.utils.tokens import InterviewTokenManager


def test_issue_token_uses_earliest_expiration_boundary() -> None:
    """Verify token expiration is capped by schedule end plus twelve hours."""
    manager = InterviewTokenManager(secret="interview-secret")
    now = datetime(2026, 3, 9, 10, 0, 0, tzinfo=UTC)

    short_window = manager.issue_token(
        interview_id="interview-1",
        schedule_version=1,
        scheduled_end_at=now + timedelta(hours=2),
        now=now,
    )
    long_window = manager.issue_token(
        interview_id="interview-1",
        schedule_version=1,
        scheduled_end_at=now + timedelta(days=90),
        now=now,
    )

    assert short_window.expires_at == now + timedelta(hours=14)
    assert long_window.expires_at == now + timedelta(days=30)


def test_compose_and_hash_token_are_deterministic_per_schedule_version() -> None:
    """Verify stored hashes match reconstructed tokens and change after token rotation."""
    manager = InterviewTokenManager(secret="interview-secret")

    original = manager.issue_token(
        interview_id="interview-1",
        schedule_version=3,
        scheduled_end_at=datetime(2026, 3, 10, 10, 0, 0, tzinfo=UTC),
    )
    reconstructed = manager.compose_token(
        interview_id="interview-1",
        schedule_version=3,
        token_nonce=original.token_nonce,
    )
    rotated = manager.issue_token(
        interview_id="interview-1",
        schedule_version=4,
        scheduled_end_at=datetime(2026, 3, 10, 10, 0, 0, tzinfo=UTC),
    )

    assert reconstructed == original.token
    assert manager.hash_token(reconstructed) == original.token_hash
    assert rotated.token != original.token
    assert rotated.token_hash != original.token_hash


def test_issue_token_accepts_naive_utc_storage_timestamp() -> None:
    """Verify DB-loaded naive UTC datetimes do not break token expiry calculation."""
    manager = InterviewTokenManager(secret="interview-secret")
    now = datetime(2026, 3, 9, 10, 0, 0, tzinfo=UTC)

    issued = manager.issue_token(
        interview_id="interview-2",
        schedule_version=1,
        scheduled_end_at=datetime(2026, 3, 9, 12, 0, 0),
        now=now,
    )

    assert issued.expires_at == datetime(2026, 3, 10, 0, 0, 0, tzinfo=UTC)
