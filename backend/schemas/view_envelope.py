"""
Vision — View Envelope Validator.

Validates json_view workspace item content against the Dynamic View Envelope
JSON Schema. Rejects non-dict content and schema violations with descriptive
error messages that agents can self-correct.

Uses a two-pass approach for better error messages:
  1. Structural validation (top-level schema, viewType enum)
  2. View-specific validation (only the matching branch)
This avoids the "not valid under any of the given schemas" noise from oneOf.
"""

from __future__ import annotations

import json
from pathlib import Path

from jsonschema import validate, ValidationError

# ---------------------------------------------------------------------------
# Load schema at module level
# ---------------------------------------------------------------------------

_SCHEMA_PATH = Path(__file__).resolve().parent / "view_envelope_schema.json"

with open(_SCHEMA_PATH, "r") as f:
    VIEW_ENVELOPE_SCHEMA = json.load(f)

# Extract the per-view-type schemas for targeted validation
_TABLE_SCHEMA = {
    "$schema": VIEW_ENVELOPE_SCHEMA["$schema"],
    "type": "object",
    "required": ["viewType", "title", "data"],
    "properties": {
        "viewType": {"const": "table"},
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "data": {
            "type": "object",
            "required": ["headers", "rows"],
            "properties": {
                "headers": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string", "minLength": 1},
                },
                "rows": {
                    "type": "array",
                    "maxItems": 500,
                    "items": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {
                            "id": {"type": "string", "minLength": 1},
                        },
                        "additionalProperties": {"type": "string"},
                    },
                },
            },
        },
    },
}

_LIST_SCHEMA = {
    "$schema": VIEW_ENVELOPE_SCHEMA["$schema"],
    "type": "object",
    "required": ["viewType", "title", "data"],
    "properties": {
        "viewType": {"const": "list"},
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "data": {
            "type": "object",
            "required": ["listStyle", "items"],
            "properties": {
                "listStyle": {
                    "type": "string",
                    "enum": ["checkbox", "ordered", "bullet"],
                },
                "items": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 200,
                    "items": {
                        "type": "object",
                        "required": ["id", "text"],
                        "properties": {
                            "id": {"type": "string", "minLength": 1},
                            "text": {"type": "string", "minLength": 1},
                            "completed": {"type": "boolean", "default": False},
                            "notes": {"type": "string"},
                        },
                    },
                },
            },
        },
    },
}

_CARDS_SCHEMA = {
    "$schema": VIEW_ENVELOPE_SCHEMA["$schema"],
    "type": "object",
    "required": ["viewType", "title", "data"],
    "properties": {
        "viewType": {"const": "cards"},
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "data": {
            "type": "object",
            "required": ["pairs"],
            "properties": {
                "pairs": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 50,
                    "items": {
                        "type": "object",
                        "required": ["key", "value"],
                        "properties": {
                            "key": {"type": "string", "minLength": 1},
                            "value": {"type": "string"},
                            "emphasis": {
                                "type": "string",
                                "enum": [
                                    "default", "warning", "danger",
                                    "success", "info",
                                ],
                                "default": "default",
                            },
                        },
                    },
                },
            },
        },
    },
}

_CHART_SCHEMA = {
    "$schema": VIEW_ENVELOPE_SCHEMA["$schema"],
    "type": "object",
    "required": ["viewType", "title", "data"],
    "properties": {
        "viewType": {"const": "chart"},
        "title": {"type": "string", "minLength": 1},
        "description": {"type": "string"},
        "data": {
            "type": "object",
            "required": ["chartType", "headers", "rows"],
            "properties": {
                "chartType": {
                    "type": "string",
                    "enum": ["bar", "line", "pie"],
                },
                "headers": {
                    "type": "array",
                    "minItems": 1,
                    "maxItems": 20,
                    "items": {"type": "string", "minLength": 1},
                },
                "rows": {
                    "type": "array",
                    "maxItems": 500,
                    "items": {
                        "type": "object",
                        "required": ["id"],
                        "properties": {
                            "id": {"type": "string", "minLength": 1},
                        },
                        "additionalProperties": {"type": "string"},
                    },
                },
            },
        },
    },
}

_VIEW_SCHEMAS = {
    "table": _TABLE_SCHEMA,
    "list": _LIST_SCHEMA,
    "cards": _CARDS_SCHEMA,
    "chart": _CHART_SCHEMA,
}

VALID_VIEW_TYPES = sorted(_VIEW_SCHEMAS.keys())


# ---------------------------------------------------------------------------
# Error helpers
# ---------------------------------------------------------------------------

def _format_error(exc: ValidationError, prefix: str = "View envelope validation failed") -> str:
    """Build a readable error message from a jsonschema ValidationError."""
    path = " → ".join(str(p) for p in exc.absolute_path)
    if path:
        return f"{prefix} at '{path}': {exc.message}"
    return f"{prefix}: {exc.message}"


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def validate_view_envelope(content: dict | list | None) -> tuple[bool, str | None]:
    """Validate json_view content against the view envelope schema.

    Args:
        content: The drafts.content value to validate. Must be a dict
                 matching {documentMetadata, views[]}. Lists are rejected
                 (json_view uses a direct object, unlike markdown's array wrap).

    Returns:
        (is_valid, error_message). error_message is None on success,
        or a human-readable description of the violation on failure.
    """
    # ---- Type guards ----
    if content is None:
        return False, "Content must not be null — expected a view envelope object"

    if isinstance(content, list):
        return False, (
            "Content must be a view envelope object {documentMetadata, views[]}, "
            "not an array. json_view items use a direct object, unlike markdown "
            "which uses array wrapping."
        )

    if not isinstance(content, dict):
        return False, f"Content must be a JSON object, got {type(content).__name__}"

    # ---- Top-level structure ----
    # jsonschema handles documentMetadata, views array, minItems, maxItems
    try:
        validate(instance=content, schema=VIEW_ENVELOPE_SCHEMA)
    except ValidationError as exc:
        # If the error is in the views array (oneOf), we handle it below
        # with per-view validation. Otherwise, return the error directly.
        path = list(exc.absolute_path)
        if exc.validator != "oneOf" or not path or path[0] != "views":
            return False, _format_error(exc)

    # ---- Per-view validation ----
    # Validate each view against its specific schema for precise error messages.
    views = content.get("views", [])
    for i, view in enumerate(views):
        if not isinstance(view, dict):
            return False, (
                f"View envelope validation failed at 'views → {i}': "
                f"expected an object, got {type(view).__name__}"
            )

        view_type = view.get("viewType")

        if view_type not in _VIEW_SCHEMAS:
            return False, (
                f"View envelope validation failed at 'views → {i}': "
                f"unknown viewType '{view_type}'. "
                f"Expected one of: {', '.join(VALID_VIEW_TYPES)}"
            )

        view_schema = _VIEW_SCHEMAS[view_type]
        try:
            validate(instance=view, schema=view_schema)
        except ValidationError as exc:
            return False, _format_error(
                exc,
                prefix=f"View envelope validation failed at 'views → {i}'",
            )

    return True, None
