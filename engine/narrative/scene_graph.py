"""Master Scene Graph loading and invariants (spec 24).

The document and the video read this one graph, so scene order and message are
owned here rather than negotiated twice.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REQUIRED_SCENE_FIELDS = (
    "scene_id",
    "title",
    "phase",
    "core",
    "core_inference",
    "goal",
    "primary_message",
    "question",
    "visual_job",
    "requires_dynamic",
    "visuals",
    "narration",
    "conclusion",
    "facts",
    "prerequisites",
)

SUBSTANTIVE_VISUAL_KINDS = ("static", "dynamic", "hybrid")
DYNAMIC_VISUAL_KINDS = ("dynamic", "hybrid")


@dataclass(frozen=True)
class SceneGraph:
    payload: dict[str, Any]

    @classmethod
    def load(cls, path: str | Path) -> "SceneGraph":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def scenes(self) -> list[dict[str, Any]]:
        return list(self.payload.get("scenes", []))

    def scene_ids(self) -> list[str]:
        return [str(s.get("scene_id")) for s in self.scenes]

    def substantive_visuals(self) -> list[dict[str, Any]]:
        return [
            v
            for s in self.scenes
            for v in s.get("visuals", [])
            if v.get("kind") in SUBSTANTIVE_VISUAL_KINDS and v.get("substantive", True)
        ]

    def dynamic_visuals(self) -> list[dict[str, Any]]:
        return [v for v in self.substantive_visuals() if v.get("kind") in DYNAMIC_VISUAL_KINDS]

    def visuals_with_role(self, role: str) -> list[dict[str, Any]]:
        return [v for v in self.substantive_visuals() if role in v.get("roles", [])]

    def core_inference_scenes(self) -> list[dict[str, Any]]:
        return [s for s in self.scenes if s.get("core_inference")]


def validate(graph: SceneGraph) -> list[str]:
    """Return every invariant violation; an empty list is the only pass."""
    problems: list[str] = []
    payload = graph.payload
    if payload.get("kind") != "master-scene-graph":
        problems.append("kind must be 'master-scene-graph'")
    scenes = graph.scenes
    if not scenes:
        problems.append("scene graph has no scenes")
        return problems

    seen: set[str] = set()
    order: dict[str, int] = {}
    for position, scene in enumerate(scenes):
        sid = str(scene.get("scene_id", f"<index {position}>"))
        for field in REQUIRED_SCENE_FIELDS:
            if field not in scene:
                problems.append(f"{sid}: missing required field '{field}'")
        if sid in seen:
            problems.append(f"{sid}: duplicate scene_id")
        seen.add(sid)
        order[sid] = position

    for position, scene in enumerate(scenes):
        sid = str(scene.get("scene_id"))
        for prerequisite in scene.get("prerequisites", []):
            if prerequisite not in order:
                problems.append(f"{sid}: prerequisite {prerequisite} does not exist")
            elif order[prerequisite] >= position:
                problems.append(
                    f"{sid}: prerequisite {prerequisite} must come earlier in the graph"
                )
        messages = [m for m in [scene.get("primary_message")] if m]
        if len(messages) != 1:
            problems.append(f"{sid}: exactly one primary_message is required")
        visuals = scene.get("visuals", [])
        substantive = [v for v in visuals if v.get("kind") in SUBSTANTIVE_VISUAL_KINDS and v.get("substantive", True)]
        if scene.get("core_inference") and not substantive:
            problems.append(f"{sid}: core inference scene needs at least one substantive visual")
        if scene.get("requires_dynamic") and not [v for v in substantive if v.get("kind") in DYNAMIC_VISUAL_KINDS]:
            problems.append(f"{sid}: requires_dynamic is set but no dynamic or hybrid visual exists")
        for fact_ref in scene.get("facts", []):
            if not isinstance(fact_ref, str):
                problems.append(f"{sid}: fact references must be fact ids")

    phases_in_order = [str(s.get("phase")) for s in scenes]
    if "breakthrough" in phases_in_order and "solution" in phases_in_order:
        if phases_in_order.index("breakthrough") > phases_in_order.index("solution"):
            problems.append("breakthrough scene must precede the solution scene")
    if not any(s.get("phase") == "reconstruction" for s in scenes):
        problems.append("at least one reconstruction scene is required")
    return problems


def fact_references(graph: SceneGraph) -> set[str]:
    return {f for scene in graph.scenes for f in scene.get("facts", [])}
