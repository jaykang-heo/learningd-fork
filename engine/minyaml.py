"""Minimal YAML reader/writer for the flat mappings this project owns.

`run.yaml` (spec 14.2) and the `config/*.yaml` policies are flat or one-level
nested scalar mappings plus scalar lists. A full YAML dependency would buy
nothing the product needs, so the supported subset is kept explicit and the
parser refuses anything outside it instead of guessing.
"""

from __future__ import annotations

from typing import Any


class YamlSubsetError(ValueError):
    """Raised when input uses YAML features outside the supported subset."""


def _parse_scalar(token: str) -> Any:
    token = token.strip()
    if token.startswith(('"', "'")) and token.endswith(('"', "'")) and len(token) >= 2:
        return token[1:-1]
    if token in ("true", "false"):
        return token == "true"
    if token in ("null", "~", ""):
        return None
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def loads(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    # Each frame is (indent, container, owner_mapping, owner_key); the owner lets
    # an empty block become a list the first time a `- ` item appears under it.
    stack: list[tuple[int, Any, dict[str, Any] | None, str | None]] = [(-1, root, None, None)]
    for raw_line in text.splitlines():
        line = raw_line.split(" #")[0].rstrip() if " #" in raw_line else raw_line.rstrip()
        if not line.strip() or line.strip().startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        body = line.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        if not stack:
            raise YamlSubsetError(f"unbalanced indentation: {raw_line!r}")
        frame_indent, container, owner, owner_key = stack[-1]
        if body.startswith("- "):
            if isinstance(container, dict) and not container and owner is not None:
                container = []
                owner[owner_key] = container
                stack[-1] = (frame_indent, container, owner, owner_key)
            if not isinstance(container, list):
                raise YamlSubsetError(f"list item outside a list: {raw_line!r}")
            container.append(_parse_scalar(body[2:]))
            continue
        if ":" not in body:
            raise YamlSubsetError(f"unsupported line: {raw_line!r}")
        key, _, rest = body.partition(":")
        key = key.strip()
        rest = rest.strip()
        if not isinstance(container, dict):
            raise YamlSubsetError(f"mapping key inside a list: {raw_line!r}")
        if rest == "":
            child: dict[str, Any] = {}
            container[key] = child
            stack.append((indent, child, container, key))
        elif rest == "[]":
            container[key] = []
        elif rest == "{}":
            container[key] = {}
        else:
            container[key] = _parse_scalar(rest)
    return root


def _dump_scalar(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace('"', '\\"') + '"'


def dumps(mapping: dict[str, Any], indent: int = 0) -> str:
    lines: list[str] = []
    pad = " " * indent
    for key, value in mapping.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}:")
            lines.append(dumps(value, indent + 2).rstrip("\n"))
        elif isinstance(value, list):
            if not value:
                lines.append(f"{pad}{key}: []")
            else:
                lines.append(f"{pad}{key}:")
                for item in value:
                    lines.append(f"{pad}  - {_dump_scalar(item)}")
        else:
            lines.append(f"{pad}{key}: {_dump_scalar(value)}")
    return "\n".join(lines) + "\n"
