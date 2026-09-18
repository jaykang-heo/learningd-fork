"""Append-only run event log (spec 51.1)."""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any


def append(events_path: str | Path, event_type: str, **fields: Any) -> dict[str, Any]:
    record: dict[str, Any] = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "type": event_type,
    }
    record.update(fields)
    path = Path(events_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, sort_keys=True, ensure_ascii=False) + "\n"
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(line)
        handle.flush()
        os.fsync(handle.fileno())
    return record


def read(events_path: str | Path) -> list[dict[str, Any]]:
    path = Path(events_path)
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
