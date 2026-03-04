"""Validation and parsing helpers for candidate CV processing."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass

from fastapi import HTTPException, status


@dataclass(frozen=True)
class CVValidationResult:
    """Validated file envelope returned by CV validator.

    Attributes:
        content: Uploaded binary payload.
        mime_type: Validated MIME type.
        checksum_sha256: Calculated SHA-256 checksum.
        size_bytes: Uploaded payload size in bytes.
    """

    content: bytes
    mime_type: str
    checksum_sha256: str
    size_bytes: int


def validate_cv_payload(
    *,
    filename: str,
    mime_type: str,
    content: bytes,
    checksum_sha256: str,
    allowed_mime_types: tuple[str, ...],
    max_size_bytes: int,
) -> CVValidationResult:
    """Validate CV upload payload.

    Args:
        filename: Uploaded filename.
        mime_type: Uploaded MIME type.
        content: Uploaded binary content.
        checksum_sha256: Client-provided SHA-256 checksum.
        allowed_mime_types: Allowed MIME type whitelist.
        max_size_bytes: Maximum payload size.

    Returns:
        CVValidationResult: Normalized and validated CV payload.

    Raises:
        HTTPException: If validation fails.
    """
    normalized_filename = filename.strip()
    if not normalized_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename must be non-empty",
        )

    normalized_mime = mime_type.strip().lower()
    if normalized_mime not in {item.lower() for item in allowed_mime_types}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported CV MIME type: {normalized_mime}",
        )

    size_bytes = len(content)
    if size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="CV file is empty",
        )
    if size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail=f"CV exceeds max size ({max_size_bytes} bytes)",
        )

    expected_checksum = checksum_sha256.strip().lower()
    calculated_checksum = hashlib.sha256(content).hexdigest()
    if expected_checksum != calculated_checksum:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="CV checksum mismatch",
        )

    return CVValidationResult(
        content=content,
        mime_type=normalized_mime,
        checksum_sha256=calculated_checksum,
        size_bytes=size_bytes,
    )


def parse_cv_document(*, content: bytes, mime_type: str) -> dict[str, object]:
    """Produce deterministic parsed CV payload for worker pipeline.

    Args:
        content: CV binary payload.
        mime_type: Document MIME type.

    Returns:
        dict[str, object]: Minimal parsed metadata payload.

    Raises:
        ValueError: If parsing fails.
    """
    if content.startswith(b"FAIL_PARSE"):
        raise ValueError("CV parsing failed by deterministic test marker")

    text_excerpt = content[:80].decode("utf-8", errors="ignore").strip()
    return {
        "mime_type": mime_type,
        "size_bytes": len(content),
        "excerpt": text_excerpt,
    }
