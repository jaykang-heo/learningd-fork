"""A small JSON Schema subset checker.

The schemas in `schemas/` exist to be enforced, not to document intentions, so
they are checked by this module rather than by an unused dependency. Supported
keywords: type, required, properties, items, enum, minItems, additionalProperties
(boolean form). Anything else in a schema raises, so a schema cannot quietly
assert more than is actually checked.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

_SUPPORTED = {
    "$schema", "$id", "title", "description", "type", "required", "properties",
    "items", "enum", "minItems", "additionalProperties",
}

_TYPES: dict[str, type | tuple[type, ...]] = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
    "null": type(None),
}


class UnsupportedSchema(ValueError):
    pass


def load(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate(instance: Any, schema: dict[str, Any], *, path: str = "$") -> list[str]:
    unsupported = set(schema) - _SUPPORTED
    if unsupported:
        raise UnsupportedSchema(f"{path}: schema uses unchecked keywords {sorted(unsupported)}")

    problems: list[str] = []
    declared = schema.get("type")
    if declared:
        expected = _TYPES[declared]
        ok = isinstance(instance, expected) and not (declared != "boolean" and isinstance(instance, bool))
        if declared == "boolean":
            ok = isinstance(instance, bool)
        if not ok:
            return [f"{path}: expected {declared}, found {type(instance).__name__}"]

    if "enum" in schema and instance not in schema["enum"]:
        problems.append(f"{path}: {instance!r} is not one of {schema['enum']}")

    if isinstance(instance, dict):
        for key in schema.get("required", []):
            if key not in instance:
                problems.append(f"{path}: missing required property '{key}'")
        properties = schema.get("properties", {})
        if schema.get("additionalProperties") is False:
            for key in instance:
                if key not in properties:
                    problems.append(f"{path}: unexpected property '{key}'")
        for key, subschema in properties.items():
            if key in instance:
                problems.extend(validate(instance[key], subschema, path=f"{path}.{key}"))

    if isinstance(instance, list):
        if "minItems" in schema and len(instance) < int(schema["minItems"]):
            problems.append(f"{path}: needs at least {schema['minItems']} items, found {len(instance)}")
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(instance):
                problems.extend(validate(item, item_schema, path=f"{path}[{index}]"))
    return problems
