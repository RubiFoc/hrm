"""Candidate service exports with lazy imports to avoid circular dependencies.

This package exposes the public candidate-domain services while delaying heavy imports
until consumers actually request the symbols.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from hrm_backend.candidates.services.candidate_service import CandidateService
    from hrm_backend.candidates.services.cv_parsing_worker_service import CVParsingWorkerService

__all__ = ["CandidateService", "CVParsingWorkerService"]


def __getattr__(name: str) -> Any:
    """Resolve public service symbols lazily on first access."""
    if name == "CandidateService":
        from hrm_backend.candidates.services.candidate_service import CandidateService

        return CandidateService
    if name == "CVParsingWorkerService":
        from hrm_backend.candidates.services.cv_parsing_worker_service import (
            CVParsingWorkerService,
        )

        return CVParsingWorkerService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
