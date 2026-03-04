"""Unit tests for candidate CV validation helpers."""

from __future__ import annotations

import hashlib

import pytest
from fastapi import HTTPException

from hrm_backend.candidates.utils.cv import validate_cv_payload


def test_validate_cv_payload_accepts_valid_pdf() -> None:
    """Verify validator accepts valid MIME, size, and checksum."""
    content = b"valid-pdf-content"
    checksum = hashlib.sha256(content).hexdigest()

    result = validate_cv_payload(
        filename="cv.pdf",
        mime_type="application/pdf",
        content=content,
        checksum_sha256=checksum,
        allowed_mime_types=("application/pdf",),
        max_size_bytes=1024,
    )

    assert result.mime_type == "application/pdf"
    assert result.size_bytes == len(content)
    assert result.checksum_sha256 == checksum


def test_validate_cv_payload_rejects_unsupported_mime() -> None:
    """Verify validator rejects unsupported MIME type."""
    content = b"content"
    checksum = hashlib.sha256(content).hexdigest()

    with pytest.raises(HTTPException) as exc_info:
        validate_cv_payload(
            filename="cv.txt",
            mime_type="text/plain",
            content=content,
            checksum_sha256=checksum,
            allowed_mime_types=("application/pdf",),
            max_size_bytes=1024,
        )

    assert exc_info.value.status_code == 415


def test_validate_cv_payload_rejects_checksum_mismatch() -> None:
    """Verify validator rejects non-matching checksum."""
    content = b"content"

    with pytest.raises(HTTPException) as exc_info:
        validate_cv_payload(
            filename="cv.pdf",
            mime_type="application/pdf",
            content=content,
            checksum_sha256="0" * 64,
            allowed_mime_types=("application/pdf",),
            max_size_bytes=1024,
        )

    assert exc_info.value.status_code == 422


def test_validate_cv_payload_rejects_oversized_file() -> None:
    """Verify validator rejects file exceeding size limit."""
    content = b"x" * 11
    checksum = hashlib.sha256(content).hexdigest()

    with pytest.raises(HTTPException) as exc_info:
        validate_cv_payload(
            filename="cv.pdf",
            mime_type="application/pdf",
            content=content,
            checksum_sha256=checksum,
            allowed_mime_types=("application/pdf",),
            max_size_bytes=10,
        )

    assert exc_info.value.status_code == 413
