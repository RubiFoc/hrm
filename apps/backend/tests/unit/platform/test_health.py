"""Unit tests for core service health behavior."""

from hrm_backend.main import health


def test_health() -> None:
    """Verify that the health endpoint function returns expected payload."""
    assert health() == {"status": "ok"}
