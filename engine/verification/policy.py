"""Quality policy loading (spec 25.2).

One file owns the floors so a run cannot quietly grade itself on softer numbers.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine import minyaml
from engine.hashing import sha256_file


@dataclass(frozen=True)
class QualityPolicy:
    path: Path
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "QualityPolicy":
        path = Path(path)
        return cls(path, minyaml.loads(path.read_text(encoding="utf-8")))

    @property
    def sha256(self) -> str:
        return sha256_file(self.path)

    def section(self, name: str) -> dict[str, Any]:
        return dict(self.payload.get(name, {}))

    def get(self, section: str, key: str) -> Any:
        try:
            return self.payload[section][key]
        except KeyError as exc:
            raise KeyError(f"quality policy is missing {section}.{key}") from exc
