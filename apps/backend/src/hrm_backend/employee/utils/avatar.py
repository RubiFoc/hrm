"""Validation helpers for employee avatar uploads."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status

ALLOWED_AVATAR_MIME_TYPES = ("image/jpeg", "image/png", "image/webp")
MAX_AVATAR_SIZE_BYTES = 10 * 1024 * 1024


@dataclass(frozen=True)
class AvatarValidationResult:
    """Validated avatar upload payload.

    Attributes:
        content: Uploaded binary payload.
        mime_type: Validated MIME type.
        size_bytes: Uploaded payload size in bytes.
        filename: Normalized filename.
    """

    content: bytes
    mime_type: str
    size_bytes: int
    filename: str


def validate_avatar_payload(
    *,
    filename: str,
    mime_type: str,
    content: bytes,
    allowed_mime_types: tuple[str, ...] = ALLOWED_AVATAR_MIME_TYPES,
    max_size_bytes: int = MAX_AVATAR_SIZE_BYTES,
) -> AvatarValidationResult:
    """Validate avatar upload payload.

    Args:
        filename: Uploaded filename.
        mime_type: Uploaded MIME type.
        content: Uploaded binary payload.
        allowed_mime_types: Allowed MIME type whitelist.
        max_size_bytes: Maximum payload size.

    Returns:
        AvatarValidationResult: Normalized and validated avatar payload.

    Raises:
        HTTPException: If validation fails.
    """
    normalized_filename = filename.strip()
    if not normalized_filename:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="avatar_filename_missing",
        )

    normalized_mime = mime_type.strip().lower()
    if normalized_mime not in {item.lower() for item in allowed_mime_types}:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="avatar_mime_unsupported",
        )

    size_bytes = len(content)
    if size_bytes <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="avatar_empty",
        )
    if size_bytes > max_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="avatar_too_large",
        )

    return AvatarValidationResult(
        content=content,
        mime_type=normalized_mime,
        size_bytes=size_bytes,
        filename=normalized_filename,
    )
