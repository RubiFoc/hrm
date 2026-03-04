"""Shared HTTP exception factories for backend services and dependencies."""

from fastapi import HTTPException, status


def unauthorized(detail: str) -> HTTPException:
    """Build standardized unauthorized HTTP error.

    Args:
        detail: Human-readable error detail.

    Returns:
        HTTPException: 401 unauthorized exception.
    """
    return HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)


def service_unavailable(detail: str) -> HTTPException:
    """Build standardized service unavailable HTTP error.

    Args:
        detail: Human-readable error detail.

    Returns:
        HTTPException: 503 service unavailable exception.
    """
    return HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)
