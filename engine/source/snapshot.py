"""Immutable source snapshot (spec 19).

Everything downstream quotes the problem statement. The snapshot is written once
and hashed, so a later remote edit of the source can be detected instead of
silently changing what the lesson claims.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine.atomic import write_bytes, write_text
from engine.hashing import sha256_bytes, sha256_file


class SourceMutated(RuntimeError):
    """Stored bytes no longer match the recorded snapshot hash."""


@dataclass(frozen=True)
class Snapshot:
    raw_path: Path
    metadata_path: Path
    sha256: str
    metadata: dict[str, Any]


def capture(
    directory: str | Path,
    *,
    raw: bytes,
    origin: str,
    access_method: str,
    platform: str | None = None,
    identifier: str | None = None,
    extension: str = "html",
) -> Snapshot:
    directory = Path(directory)
    raw_path = directory / f"raw.{extension}"
    if raw_path.exists():
        raise FileExistsError(f"source snapshot already captured: {raw_path}")
    write_bytes(raw_path, raw)
    metadata = {
        "schema_version": 1,
        "sha256": sha256_bytes(raw),
        "bytes": len(raw),
        "origin": origin,
        "access_method": access_method,
        "platform": platform,
        "identifier": identifier,
        "captured_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "raw_file": raw_path.name,
    }
    metadata_path = write_text(
        directory / "source.json",
        json.dumps(metadata, sort_keys=True, ensure_ascii=False, indent=2) + "\n",
    )
    return Snapshot(raw_path, metadata_path, metadata["sha256"], metadata)


def load(directory: str | Path) -> Snapshot:
    directory = Path(directory)
    metadata_path = directory / "source.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    raw_path = directory / metadata["raw_file"]
    return Snapshot(raw_path, metadata_path, metadata["sha256"], metadata)


def verify(directory: str | Path) -> Snapshot:
    snapshot = load(directory)
    actual = sha256_file(snapshot.raw_path)
    if actual != snapshot.sha256:
        raise SourceMutated(
            f"source bytes changed after capture: recorded {snapshot.sha256}, found {actual}"
        )
    return snapshot


def quotes_are_faithful(source_text: str, quotes: list[str]) -> list[str]:
    """Return the quotes that do not appear verbatim in the snapshot (spec 19.3)."""
    normalized = " ".join(source_text.split())
    return [q for q in quotes if " ".join(q.split()) not in normalized]
