"""Template rendering helpers for automation-planned notification content."""

from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime

from hrm_backend.automation.utils.conditions import resolve_field_value

_PLACEHOLDER_PATTERN = re.compile(r"{{\s*([a-zA-Z0-9_\.]+)\s*}}")


class TemplateRenderError(ValueError):
    """Raised when a template cannot be rendered with the provided context."""


def render_template(value: str, context: Mapping[str, object]) -> str:
    """Render `{{field}}` placeholders using the provided context."""

    def _replace(match: re.Match[str]) -> str:
        key = match.group(1)
        resolved = resolve_field_value(context, key)
        if resolved is None:
            raise TemplateRenderError(f"Missing template field: {key}")
        if isinstance(resolved, datetime):
            return resolved.isoformat()
        return str(resolved)

    return _PLACEHOLDER_PATTERN.sub(_replace, value)


def render_json_template(value: object, context: Mapping[str, object]) -> object:
    """Recursively render template placeholders inside JSON-like values."""
    if isinstance(value, str):
        return render_template(value, context)
    if isinstance(value, list):
        return [render_json_template(item, context) for item in value]
    if isinstance(value, dict):
        return {str(key): render_json_template(item, context) for key, item in value.items()}
    return value
