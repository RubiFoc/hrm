"""Opaque token generation and hashing helpers for interview invitations."""

from __future__ import annotations

import base64
import hmac
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256


@dataclass(frozen=True)
class InterviewTokenIssue:
    """Issued token payload returned before persistence."""

    token: str
    token_hash: str
    token_nonce: str
    expires_at: datetime


class InterviewTokenManager:
    """Generate and hash public interview registration tokens."""

    def __init__(self, secret: str) -> None:
        """Initialize token manager with HMAC secret."""
        self._secret = secret.encode("utf-8")

    def issue_token(
        self,
        *,
        interview_id: str,
        schedule_version: int,
        scheduled_end_at: datetime,
        now: datetime | None = None,
    ) -> InterviewTokenIssue:
        """Generate one opaque token, its persisted hash, and expiration timestamp."""
        issued_at = now or datetime.now(UTC)
        normalized_scheduled_end_at = _ensure_utc_datetime(scheduled_end_at)
        token_nonce = secrets.token_urlsafe(24)
        token = self.compose_token(
            interview_id=interview_id,
            schedule_version=schedule_version,
            token_nonce=token_nonce,
        )
        return InterviewTokenIssue(
            token=token,
            token_hash=self.hash_token(token),
            token_nonce=token_nonce,
            expires_at=min(
                normalized_scheduled_end_at + timedelta(hours=12),
                issued_at + timedelta(days=30),
            ),
        )

    def compose_token(
        self,
        *,
        interview_id: str,
        schedule_version: int,
        token_nonce: str,
    ) -> str:
        """Compose one reconstructable opaque token from nonce and signed metadata."""
        payload = f"{interview_id}:{schedule_version}:{token_nonce}"
        signature = hmac.new(self._secret, payload.encode("utf-8"), sha256).digest()
        encoded_signature = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
        return f"{token_nonce}.{encoded_signature}"

    def hash_token(self, token: str) -> str:
        """Hash a public token into a deterministic HMAC-SHA256 hex digest."""
        normalized = token.strip()
        return hmac.new(self._secret, normalized.encode("utf-8"), sha256).hexdigest()


def _ensure_utc_datetime(value: datetime) -> datetime:
    """Normalize persisted schedule timestamps to aware UTC datetimes."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
