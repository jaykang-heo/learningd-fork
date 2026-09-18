"""The candidate a gate is evaluated against.

A candidate is a set of files plus their hashes. Gates read this object only, so
the same gate function works in a run directory, in a fixture and in a test.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path
from typing import Any

from engine.document.inspect import DocumentReport, inspect as inspect_document
from engine.facts.store import FactsStore
from engine.hashing import sha256_file, sha256_text
from engine.narrative.scene_graph import SceneGraph
from engine.research.map import ResearchMap
from engine.verification.policy import QualityPolicy
from engine.video.storyboard import Storyboard


def _hash_or_absent(path: Path) -> str:
    return sha256_file(path) if path.exists() else "absent"


@dataclass(frozen=True)
class Candidate:
    run_root: Path
    policy: QualityPolicy

    # --- canonical paths -------------------------------------------------
    @property
    def source_dir(self) -> Path:
        return self.run_root / "source"

    @property
    def facts_path(self) -> Path:
        return self.run_root / "facts.json"

    @property
    def research_path(self) -> Path:
        return self.run_root / "research.json"

    @property
    def scene_graph_path(self) -> Path:
        return self.run_root / "narrative" / "master-scene-graph.json"

    @property
    def lesson_path(self) -> Path:
        return self.run_root / "document" / "lesson.html"

    @property
    def video_path(self) -> Path:
        return self.run_root / "video" / "explainer.mp4"

    @property
    def storyboard_path(self) -> Path:
        return self.run_root / "video" / "storyboard.json"

    @property
    def narration_path(self) -> Path:
        return self.run_root / "video" / "narration.json"

    @property
    def captions_path(self) -> Path:
        return self.run_root / "video" / "captions.vtt"

    @property
    def solution_path(self) -> Path:
        return self.run_root / "solutions" / "primary.py"

    @property
    def cases_path(self) -> Path:
        return self.run_root / "solutions" / "cases.json"

    @property
    def reviews_dir(self) -> Path:
        return self.run_root / "reviews"

    # --- loaded state ----------------------------------------------------
    @cached_property
    def facts(self) -> FactsStore:
        return FactsStore.load(self.facts_path)

    @cached_property
    def research(self) -> ResearchMap:
        return ResearchMap.load(self.research_path)

    @cached_property
    def scene_graph(self) -> SceneGraph:
        return SceneGraph.load(self.scene_graph_path)

    @cached_property
    def document(self) -> DocumentReport:
        return inspect_document(self.lesson_path)

    @cached_property
    def storyboard(self) -> Storyboard:
        return Storyboard.load(self.storyboard_path)

    @cached_property
    def narration(self) -> dict[str, Any]:
        return json.loads(self.narration_path.read_text(encoding="utf-8"))

    def review(self, name: str) -> dict[str, Any] | None:
        path = self.reviews_dir / f"{name}.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # --- hashes ----------------------------------------------------------
    def hashes(self) -> dict[str, str]:
        """Every dependency hash a receipt may bind to."""
        source_meta = self.source_dir / "source.json"
        return {
            "source_sha256": _hash_or_absent(source_meta),
            "facts_sha256": _hash_or_absent(self.facts_path),
            "research_sha256": _hash_or_absent(self.research_path),
            "scene_graph_sha256": _hash_or_absent(self.scene_graph_path),
            "lesson_html_sha256": _hash_or_absent(self.lesson_path),
            "explainer_video_sha256": _hash_or_absent(self.video_path),
            "storyboard_sha256": _hash_or_absent(self.storyboard_path),
            "narration_sha256": _hash_or_absent(self.narration_path),
            "captions_sha256": _hash_or_absent(self.captions_path),
            "solution_sha256": _hash_or_absent(self.solution_path),
            "quality_policy_sha256": self.policy.sha256,
            "reviews_sha256": sha256_text(
                "".join(
                    f"{p.name}:{sha256_file(p)}"
                    for p in sorted(self.reviews_dir.glob("*.json"))
                )
            ),
        }
