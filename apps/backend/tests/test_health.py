"""Integration tests for core service health behavior."""

from fastapi.testclient import TestClient

from hrm_backend.main import app


def test_health() -> None:
    """Verify that the health endpoint returns a successful status payload."""
    client = TestClient(app)
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
