"""Cross-output agreement between lesson.html and the video (spec 37 K14).

The document and the video are two renderings of one scene graph and one fact
set. This is where that claim is checked instead of assumed.
"""

from __future__ import annotations

from typing import Iterable

from engine.document.inspect import DocumentReport
from engine.facts.store import FactsStore
from engine.narrative.scene_graph import SceneGraph
from engine.video.storyboard import Storyboard


def check(
    graph: SceneGraph,
    document: DocumentReport,
    storyboard: Storyboard,
    facts: FactsStore,
    narration_scene_ids: Iterable[str],
) -> list[str]:
    problems: list[str] = []
    scene_ids = graph.scene_ids()

    if list(document.scenes) != scene_ids:
        problems.append(
            "document scene order differs from the master scene graph: "
            f"{list(document.scenes)} != {scene_ids}"
        )
    if storyboard.scene_order() != scene_ids:
        problems.append(
            "video scene order differs from the master scene graph: "
            f"{storyboard.scene_order()} != {scene_ids}"
        )
    narration_ids = list(narration_scene_ids)
    if narration_ids != scene_ids:
        problems.append(
            f"narration covers {narration_ids}, the scene graph defines {scene_ids}"
        )

    unknown_doc_facts = sorted(set(document.fact_refs) - set(facts.by_id))
    if unknown_doc_facts:
        problems.append(f"document references facts that do not exist: {', '.join(unknown_doc_facts)}")

    graph_facts = {f for scene in graph.scenes for f in scene.get("facts", [])}
    unknown_graph_facts = sorted(graph_facts - set(facts.by_id))
    if unknown_graph_facts:
        problems.append(f"scene graph references facts that do not exist: {', '.join(unknown_graph_facts)}")

    mismatched = facts.recompute()
    if mismatched:
        problems.append(f"derived facts disagree with their generators: {', '.join(mismatched)}")
    return problems
