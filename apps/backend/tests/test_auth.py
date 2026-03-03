"""Authentication and session lifecycle unit tests."""

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from hrm_backend.auth import SessionStore, get_bearer_token


def _request_with_headers(headers: dict[str, str]) -> Request:
    """Build minimal Starlette request object with provided HTTP headers.

    Args:
        headers: Header map represented as plain string pairs.

    Returns:
        Request: Request object suitable for dependency function testing.
    """
    scope = {
        "type": "http",
        "method": "GET",
        "path": "/",
        "headers": [
            (key.lower().encode("latin-1"), value.encode("latin-1"))
            for key, value in headers.items()
        ],
    }
    return Request(scope)


def test_issue_session_returns_access_and_refresh_tokens() -> None:
    """Verify session issuance returns complete token bundle."""
    store = SessionStore()

    bundle = store.issue_session(subject_id="hr-user-1", role="hr")

    assert bundle.token_type == "bearer"
    assert bundle.access_token
    assert bundle.refresh_token
    assert bundle.session_id
    assert bundle.expires_in > 0


def test_validate_access_token_returns_identity_claims() -> None:
    """Verify access token validation resolves subject, role, and session claims."""
    store = SessionStore()
    bundle = store.issue_session(subject_id="candidate-42", role="candidate")

    context = store.validate_access_token(bundle.access_token)

    assert context.subject_id == "candidate-42"
    assert context.role == "candidate"
    assert context.session_id == bundle.session_id


def test_refresh_rotates_refresh_token_and_rejects_replay() -> None:
    """Verify refresh operation rotates token secret and blocks old refresh token reuse."""
    store = SessionStore()
    initial_bundle = store.issue_session(subject_id="hr-rot", role="hr")

    rotated_bundle = store.rotate_refresh_token(initial_bundle.refresh_token)

    assert rotated_bundle.refresh_token != initial_bundle.refresh_token
    assert rotated_bundle.access_token != initial_bundle.access_token

    with pytest.raises(HTTPException) as exc_info:
        store.rotate_refresh_token(initial_bundle.refresh_token)

    assert "Invalid refresh token" in str(exc_info.value)


def test_revoke_session_blocks_access_token_validation_and_refresh() -> None:
    """Verify revoked sessions can no longer be used by access or refresh tokens."""
    store = SessionStore()
    bundle = store.issue_session(subject_id="candidate-logout", role="candidate")

    store.revoke_session(bundle.session_id)

    with pytest.raises(HTTPException) as access_exc:
        store.validate_access_token(bundle.access_token)
    assert "Session revoked" in str(access_exc.value)

    with pytest.raises(HTTPException) as refresh_exc:
        store.rotate_refresh_token(bundle.refresh_token)
    assert "Session revoked" in str(refresh_exc.value)


def test_get_bearer_token_extracts_token_value() -> None:
    """Verify Bearer token dependency extracts token from authorization header."""
    request = _request_with_headers({"Authorization": "Bearer token-value-123"})

    assert get_bearer_token(request) == "token-value-123"


def test_get_bearer_token_rejects_missing_and_malformed_headers() -> None:
    """Verify bearer dependency rejects missing or malformed authorization headers."""
    missing_header_request = _request_with_headers({})
    malformed_header_request = _request_with_headers({"Authorization": "Basic abc123"})

    with pytest.raises(HTTPException) as missing_exc:
        get_bearer_token(missing_header_request)
    assert "Missing Authorization header" in str(missing_exc.value)

    with pytest.raises(HTTPException) as malformed_exc:
        get_bearer_token(malformed_header_request)
    assert "Malformed Authorization header" in str(malformed_exc.value)
