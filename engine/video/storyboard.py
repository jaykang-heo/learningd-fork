"""Storyboard / shot ledger (spec 28.4).

Shots carry the visual events the video gate counts, and they reference the
scene ids of the master scene graph so the video cannot invent its own order.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Storyboard:
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "Storyboard":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def shots(self) -> list[dict[str, Any]]:
        return list(self.payload.get("shots", []))

    def scene_order(self) -> list[str]:
        order: list[str] = []
        for shot in self.shots:
            scene_id = str(shot.get("scene_id"))
            if not order or order[-1] != scene_id:
                order.append(scene_id)
        return order

    def total_duration(self) -> float:
        return round(sum(float(shot.get("duration_seconds", 0.0)) for shot in self.shots), 3)


def validate(board: Storyboard, scene_ids: list[str], *, max_seconds_without_event: float) -> list[str]:
    problems: list[str] = []
    if not board.shots:
        return ["storyboard has no shots"]
    unknown = [s for s in board.scene_order() if s not in scene_ids]
    if unknown:
        problems.append(f"storyboard references unknown scenes: {', '.join(unknown)}")
    deduped = [s for s in board.scene_order() if s in scene_ids]
    expected = [s for s in scene_ids if s in deduped]
    if deduped != expected:
        problems.append("storyboard scene order does not follow the master scene graph")
    for shot in board.shots:
        shot_id = shot.get("shot_id", "<unnamed>")
        duration = float(shot.get("duration_seconds", 0.0))
        events = shot.get("visual_events", [])
        if duration <= 0:
            problems.append(f"{shot_id}: duration must be positive")
        if not events:
            problems.append(f"{shot_id}: a shot needs at least one visual event")
            continue
        gaps = _event_gaps(duration, [float(e.get("at_seconds", 0.0)) for e in events])
        if gaps > max_seconds_without_event:
            problems.append(
                f"{shot_id}: {gaps:.1f}s without a meaningful visual event "
                f"(limit {max_seconds_without_event:.1f}s)"
            )
        for event in events:
            if not event.get("kind"):
                problems.append(f"{shot_id}: visual event without a kind")
    return problems


def _event_gaps(duration: float, times: list[float]) -> float:
    marks = sorted(t for t in times if 0.0 <= t <= duration)
    largest = 0.0
    previous = 0.0
    for mark in marks:
        largest = max(largest, mark - previous)
        previous = mark
    return max(largest, duration - previous)
