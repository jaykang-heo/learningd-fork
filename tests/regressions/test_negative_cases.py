"""Spec 53: candidates that must be rejected.

Each test names the regression it guards, so a future change that softens a
gate fails here with the reason rather than silently shipping.
"""

import copy
import json
import tempfile
import unittest
from pathlib import Path

from engine.atomic import write_text
from engine.narrative.scene_graph import SceneGraph, validate as validate_graph
from engine.verification.acceptance import REGISTRY
from engine.verification.context import Candidate
from engine.verification.policy import QualityPolicy
from engine.video.storyboard import Storyboard, validate as validate_storyboard
from tests import fixtures


class NegativeCases(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.policy = QualityPolicy.load(fixtures.write_policy(self.root / "quality.yaml"))
        self.run_root = self.root / "run"
        fixtures.build_candidate(self.run_root, with_media=False)

    def candidate(self) -> Candidate:
        return Candidate(run_root=self.run_root, policy=self.policy)

    def gate(self, key: str):
        return REGISTRY.get(key).check(self.candidate())

    # 1. padded prose without substance
    def test_prose_wall_without_visuals_is_rejected(self):
        scenes = self.candidate().scene_graph.scene_ids()
        write_text(
            self.run_root / "document" / "lesson.html",
            "<html><body>"
            + "".join(f'<section data-scene="{s}"><p>{"설명 " * 4000}</p></section>' for s in scenes)
            + "</body></html>",
        )
        self.assertFalse(self.gate("K7").passed)

    # 2/3. core inference without a visual, static-only transform
    def test_scene_graph_rejects_missing_and_static_core_visuals(self):
        payload = copy.deepcopy(self.candidate().scene_graph.payload)
        payload["scenes"][1]["visuals"] = []
        self.assertTrue(validate_graph(SceneGraph(payload)))

    # 4. animation without an explanatory job
    def test_shot_without_a_visual_event_is_rejected(self):
        board = Storyboard({"shots": [{"shot_id": "s1", "scene_id": "S01", "duration_seconds": 30.0, "visual_events": []}]})
        problems = validate_storyboard(board, ["S01"], max_seconds_without_event=6.0)
        self.assertTrue(any("visual event" in p for p in problems), problems)

    # 5/6. document and video disagree on a number
    def test_hand_edited_derived_number_is_rejected(self):
        facts = json.loads((self.run_root / "facts.json").read_text())
        facts["facts"][1]["value"] = 1470
        write_text(self.run_root / "facts.json", json.dumps(facts, indent=2))
        self.assertFalse(self.gate("K2").passed)

    # 7. a quote that is not in the official source
    def test_misquoted_source_is_rejected(self):
        payload = json.loads((self.run_root / "narrative" / "master-scene-graph.json").read_text())
        payload["scenes"][0]["source_quotes"] = ["1 <= nums.length <= 5000"]
        write_text(self.run_root / "narrative" / "master-scene-graph.json", json.dumps(payload, indent=2))
        self.assertFalse(self.gate("K1").passed)

    # 9. video narration that is just the document prose
    def test_narration_missing_a_scene_is_rejected(self):
        narration = json.loads((self.run_root / "video" / "narration.json").read_text())
        narration["scenes"] = narration["scenes"][:2]
        write_text(self.run_root / "video" / "narration.json", json.dumps(narration, ensure_ascii=False, indent=2))
        self.assertFalse(self.gate("K14").passed)

    # 10. long stretches with no visual event
    def test_static_stretch_beyond_the_cadence_limit_is_rejected(self):
        board = Storyboard(
            {"shots": [{"shot_id": "s1", "scene_id": "S01", "duration_seconds": 40.0,
                        "visual_events": [{"at_seconds": 1.0, "kind": "reveal"}]}]}
        )
        problems = validate_storyboard(board, ["S01"], max_seconds_without_event=6.0)
        self.assertTrue(any("without a meaningful visual event" in p for p in problems), problems)

    # 13. robotic OS voice cannot pass the release voice gate
    @unittest.skipUnless(fixtures.ffmpeg_available(), "ffmpeg/ffprobe not installed")
    def test_non_release_quality_voice_cannot_pass_under_the_shipped_policy(self):
        fixtures.render_placeholder_video(self.run_root / "video" / "explainer.mp4", seconds=4)
        shipped = QualityPolicy.load(Path(__file__).resolve().parents[2] / "config" / "quality.yaml")
        result = REGISTRY.get("K13").check(Candidate(run_root=self.run_root, policy=shipped))
        self.assertFalse(result.passed)
        self.assertTrue(any("release quality" in p for p in result.detail["problems"]))

    # 14. dynamic visual without a static fallback
    def test_dynamic_visual_without_static_fallback_is_rejected(self):
        html = (self.run_root / "document" / "lesson.html").read_text()
        write_text(
            self.run_root / "document" / "lesson.html",
            html.replace(' data-static-fallback="true"', ""),
        )
        result = self.gate("K7")
        self.assertFalse(result.passed)
        self.assertTrue(any("static fallback" in p for p in result.detail["problems"]))

    # 22 / 45.4. a lesson that depends on the network is not self-contained
    def test_remote_script_in_the_lesson_is_rejected(self):
        html = (self.run_root / "document" / "lesson.html").read_text()
        write_text(
            self.run_root / "document" / "lesson.html",
            html.replace("</body>", '<script src="https://cdn.example.com/x.js"></script></body>'),
        )
        result = self.gate("K8")
        self.assertFalse(result.passed)

    # semantic gates never pass by default
    def test_absent_reviewer_blocks_instead_of_passing(self):
        (self.run_root / "reviews" / "reconstruction.json").unlink()
        result = self.gate("K15")
        self.assertFalse(result.passed)
        self.assertIn("no reviewer verdict", result.detail["reason"])

    # research that closed a decision-critical branch with no evidence
    def test_unevidenced_research_closure_is_rejected(self):
        research = json.loads((self.run_root / "research.json").read_text())
        research["branches"][0]["evidence"] = []
        write_text(self.run_root / "research.json", json.dumps(research, indent=2))
        self.assertFalse(self.gate("K3").passed)
