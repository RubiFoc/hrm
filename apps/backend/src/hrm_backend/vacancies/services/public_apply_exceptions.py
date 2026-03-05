"""Custom exception types for public vacancy application protection logic."""

from __future__ import annotations

from fastapi import HTTPException

from hrm_backend.vacancies.schemas.application import PublicApplyReasonCode


class PublicApplyRejectedError(HTTPException):
    """Structured rejection error for blocked public application requests.

    Attributes:
        reason_code: Stable machine-readable reason code used by audit and monitoring.
    """

    def __init__(
        self,
        *,
        reason_code: PublicApplyReasonCode,
        status_code: int,
        detail: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        """Initialize structured public apply rejection.

        Args:
            reason_code: Stable rejection reason code.
            status_code: HTTP response status code.
            detail: Human-readable error detail.
            headers: Optional HTTP headers for response.
        """
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.reason_code = reason_code
