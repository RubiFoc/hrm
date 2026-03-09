"""Dependency exports for the match scoring domain."""

from hrm_backend.scoring.dependencies.scoring import (
    get_match_scoring_adapter,
    get_match_scoring_service,
    get_match_scoring_worker_service,
)

__all__ = [
    "get_match_scoring_adapter",
    "get_match_scoring_service",
    "get_match_scoring_worker_service",
]

