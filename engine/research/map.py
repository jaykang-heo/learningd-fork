"""Research map (spec 21).

A branch is closed by recorded evidence, not by an agent's sense that it has
read enough. Decision-critical branches that stay open block the knowledge gate.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResearchMap:
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "ResearchMap":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def branches(self) -> list[dict[str, Any]]:
        return list(self.payload.get("branches", []))

    def open_decision_critical(self) -> list[str]:
        return [
            str(b.get("id"))
            for b in self.branches
            if b.get("decision_critical") and b.get("status") != "closed"
        ]

    def closed_without_evidence(self) -> list[str]:
        return [
            str(b.get("id"))
            for b in self.branches
            if b.get("status") == "closed" and not b.get("evidence")
        ]


def validate(research: ResearchMap) -> list[str]:
    problems: list[str] = []
    if not research.branches:
        problems.append("research map has no branches")
    unevidenced = research.closed_without_evidence()
    if unevidenced:
        problems.append(f"branches closed without evidence: {', '.join(unevidenced)}")
    still_open = research.open_decision_critical()
    if still_open:
        problems.append(f"decision-critical branches still open: {', '.join(still_open)}")
    return problems
