"""Validation helpers for canonical recruitment pipeline transitions."""

from __future__ import annotations

from typing import Final

from hrm_backend.vacancies.schemas.pipeline import PipelineStage

_ALLOWED_TRANSITIONS: Final[dict[PipelineStage | None, set[PipelineStage]]] = {
    None: {"applied"},
    "applied": {"screening"},
    "screening": {"shortlist"},
    "shortlist": {"interview"},
    "interview": {"offer"},
    "offer": {"hired", "rejected"},
    "hired": set(),
    "rejected": set(),
}


def is_transition_allowed(from_stage: PipelineStage | None, to_stage: PipelineStage) -> bool:
    """Check whether candidate pipeline transition is allowed.

    Args:
        from_stage: Current stage derived from transition history.
        to_stage: Requested target stage.

    Returns:
        bool: `True` when transition is allowed by canonical matrix.
    """
    return to_stage in _ALLOWED_TRANSITIONS.get(from_stage, set())
