"""Condition evaluation utilities for automation rules."""

from __future__ import annotations

from collections.abc import Mapping

from hrm_backend.automation.schemas.conditions import (
    AndCondition,
    AutomationCondition,
    ContainsCondition,
    EqCondition,
    ExistsCondition,
    InCondition,
    NeqCondition,
    NotCondition,
    OrCondition,
)


def resolve_field_value(payload: Mapping[str, object], field_path: str) -> object:
    """Resolve a dotted path field from payload mapping.

    Args:
        payload: Event payload mapping (usually `event.payload.model_dump(...)`).
        field_path: Dotted path (for example `to_stage` or `meta.stage`).

    Returns:
        object: Resolved value or `None` when path does not exist.
    """
    current: object = payload
    for segment in field_path.split("."):
        if not isinstance(current, Mapping):
            return None
        if segment not in current:
            return None
        current = current[segment]
    return current


def evaluate_condition(condition: AutomationCondition, payload: Mapping[str, object]) -> bool:
    """Evaluate one condition tree against event payload."""
    if isinstance(condition, EqCondition):
        return resolve_field_value(payload, condition.field) == condition.value
    if isinstance(condition, NeqCondition):
        return resolve_field_value(payload, condition.field) != condition.value
    if isinstance(condition, InCondition):
        return resolve_field_value(payload, condition.field) in condition.value
    if isinstance(condition, ContainsCondition):
        value = resolve_field_value(payload, condition.field)
        if not isinstance(value, str):
            return False
        return condition.value in value
    if isinstance(condition, ExistsCondition):
        return resolve_field_value(payload, condition.field) is not None
    if isinstance(condition, AndCondition):
        return all(evaluate_condition(child, payload) for child in condition.conditions)
    if isinstance(condition, OrCondition):
        return any(evaluate_condition(child, payload) for child in condition.conditions)
    if isinstance(condition, NotCondition):
        return not evaluate_condition(condition.condition, payload)
    raise RuntimeError(f"Unsupported condition type: {type(condition)}")

