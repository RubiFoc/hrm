"""Identifier helpers for automation trigger payloads."""

from __future__ import annotations

from uuid import UUID


def candidate_id_to_short(candidate_id: UUID) -> str:
    """Convert a UUID candidate identifier into a short stable display token."""
    return candidate_id.hex[:8]

