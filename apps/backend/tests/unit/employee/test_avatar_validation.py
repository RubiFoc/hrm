"""Unit tests for avatar upload validation."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from hrm_backend.employee.utils.avatar import validate_avatar_payload


def test_avatar_validation_rejects_empty_payload() -> None:
    """Ensure empty avatar payload fails with 422."""
    with pytest.raises(HTTPException) as exc_info:
        validate_avatar_payload(
            filename="avatar.png",
            mime_type="image/png",
            content=b"",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "avatar_empty"


def test_avatar_validation_rejects_unsupported_mime_type() -> None:
    """Ensure unsupported MIME types fail with 415."""
    with pytest.raises(HTTPException) as exc_info:
        validate_avatar_payload(
            filename="avatar.bmp",
            mime_type="image/bmp",
            content=b"binary",
        )

    assert exc_info.value.status_code == 415
    assert exc_info.value.detail == "avatar_mime_unsupported"


def test_avatar_validation_rejects_payload_too_large() -> None:
    """Ensure payloads exceeding the size limit fail with 413."""
    with pytest.raises(HTTPException) as exc_info:
        validate_avatar_payload(
            filename="avatar.png",
            mime_type="image/png",
            content=b"x" * (10 * 1024 * 1024 + 1),
        )

    assert exc_info.value.status_code == 413
    assert exc_info.value.detail == "avatar_too_large"


def test_avatar_validation_rejects_missing_filename() -> None:
    """Ensure empty filename fails with 422."""
    with pytest.raises(HTTPException) as exc_info:
        validate_avatar_payload(
            filename=" ",
            mime_type="image/png",
            content=b"payload",
        )

    assert exc_info.value.status_code == 422
    assert exc_info.value.detail == "avatar_filename_missing"
