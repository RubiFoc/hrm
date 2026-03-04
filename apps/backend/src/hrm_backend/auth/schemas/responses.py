"""Response payload schemas for auth endpoints."""

from pydantic import BaseModel


class TokenResponse(BaseModel):
    """Token pair payload returned by login and refresh operations.

    Attributes:
        access_token: Signed short-lived JWT used for API authorization.
        refresh_token: Signed JWT used to obtain a rotated token pair.
        token_type: Token type marker (`bearer`).
        expires_in: Access token lifetime in seconds.
        session_id: Session identifier shared across issued token pairs.
    """

    access_token: str
    refresh_token: str
    token_type: str
    expires_in: int
    session_id: str


class MeResponse(BaseModel):
    """Authenticated identity payload for `/api/v1/auth/me` endpoint.

    Attributes:
        subject_id: Authenticated actor identifier.
        role: Authenticated role claim.
        session_id: Current session identifier.
        access_token_expires_at: Access token expiration timestamp.
    """

    subject_id: str
    role: str
    session_id: str
    access_token_expires_at: int
