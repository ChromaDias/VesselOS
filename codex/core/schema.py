from __future__ import annotations

from typing import Any, Dict

ENTRY_SCHEMA: Dict[str, Any] = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "tags": {"type": "array", "items": {"type": "string"}},
        "created_at": {"type": "string"},
        "anchor_date": {"type": ["string", "null"]},
        "body": {"type": "string"},
        "metadata": {"type": "object"},
        "type": {"type": "string"},
    },
    "required": ["title", "body"],
    "additionalProperties": True,
}


def validate_entry(data: Dict[str, Any]) -> bool:
    try:
        import jsonschema  # type: ignore
    except Exception:
        # Best-effort validation
        return isinstance(data.get("title"), str) and isinstance(data.get("body"), str)
    try:
        jsonschema.validate(instance=data, schema=ENTRY_SCHEMA)  # type: ignore
        return True
    except Exception:
        return False

