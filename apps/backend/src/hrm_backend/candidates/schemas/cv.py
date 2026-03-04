"""Schemas for candidate CV upload/download contracts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class CandidateCVUploadResponse(BaseModel):
    """Metadata payload returned after successful CV upload."""

    document_id: str
    candidate_id: str
    filename: str
    mime_type: str
    size_bytes: int
    checksum_sha256: str
    uploaded_at: datetime


class CandidateCVDownloadPayload(BaseModel):
    """Internal service payload for CV download streaming."""

    filename: str
    mime_type: str
    content: bytes
