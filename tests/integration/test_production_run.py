"""One full run: created -> released, driven only by receipts."""

import json
import tempfile
import unittest
from pathlib import Path

from engine.atomic import write_text
from engine.release.seal import ReleaseRefused, SealRefused
from engine.verification.policy import QualityPolicy
from runtime.orchestration import phases
from runtime.orchestration.orchestrator import Orchestrator, PhaseBlocked
from runtime.orchestration.runstore import RunStore
from runtime.recovery.reconcile import reconcile
from tests import fixtures


@unittest.skipUnless(fixtures.ffmpeg_available(), "ffmpeg/ffprobe not installed")
class ProductionRun(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.policy_path = fixtures.write_policy(self.root / "quality.yaml")
        self.policy = QualityPolicy.load(self.policy_path)
        self.store = RunStore(self.root / "runs", project_revision="test", quality_policy_path=self.policy_path)
        self.run = self.store.create(problem_key="fixture:1", request_text="teach me")
        fixtures.build_candidate(self.run.root)
        self.orchestrator = Orchestrator(self.run, self.policy)

    def drive_to_released(self):
        while (target := phases.next_phase(self.orchestrator.run.phase)) is not None:
            if target == "released":
                self.orchestrator.release()
                self.run.advance_to("released")
                break
            self.orchestrator.run_phase_gates(target)
            if target == "sealed":
                self.orchestrator.seal()
            self.orchestrator.advance()
        return self.orchestrator.run.phase

    def test_full_run_reaches_released_with_both_artifacts(self):
        self.assertEqual(self.drive_to_released(), "released")
        dist = self.run.path("dist")
        self.assertTrue((dist / "lesson.html").exists())
        self.assertTrue((dist / "explainer.mp4").exists())
        seal = json.loads((dist / "bundle-seal.json").read_text())
        self.assertEqual(len(seal["required_receipts"]), 16)
        self.assertTrue(seal["ready_for_delivery"])

    def test_every_gate_passes_on_the_fixture(self):
        outcomes = self.orchestrator.run_gates(list(self.orchestrator.registry))
        failed = [(o.gate.key, o.detail) for o in outcomes if not o.passed]
        self.assertEqual(failed, [])

    def test_missing_receipt_blocks_the_next_phase(self):
        with self.assertRaises(PhaseBlocked) as caught:
            self.orchestrator.advance()
        self.assertIn("source-integrity", str(caught.exception))
        self.assertEqual(self.run.phase, "created")

    def test_restart_resumes_from_the_last_confirmed_boundary(self):
        self.orchestrator.run_phase_gates("source_locked")
        self.orchestrator.advance()
        # A fresh process, nothing carried over in memory.
        reopened = Orchestrator(self.store.get(self.run.run_id), self.policy)
        state = reconcile(reopened)
        self.assertEqual(state.phase, "source_locked")
        self.assertEqual(state.next_phase, "knowledge_ready")
        self.assertTrue(state.blockers)

    def test_changed_facts_after_video_render_invalidate_downstream_receipts(self):
        self.orchestrator.run_gates(list(self.orchestrator.registry))
        facts = json.loads(self.run.path("facts.json").read_text())
        facts["facts"][0]["value"] = "C(n+k-1, 2k) + 1"
        write_text(self.run.path("facts.json"), json.dumps(facts, indent=2))
        stale = reconcile(self.orchestrator).stale_receipts
        self.assertIn("fact-integrity", stale)
        self.assertIn("cross-output", stale)
        with self.assertRaises(SealRefused):
            self.orchestrator.seal()

    def test_release_refuses_when_html_changed_after_sealing(self):
        self.orchestrator.run_gates(list(self.orchestrator.registry))
        self.orchestrator.seal()
        write_text(self.run.path("document", "lesson.html"), "<html><body>edited after seal</body></html>")
        with self.assertRaises(ReleaseRefused):
            self.orchestrator.release()
        self.assertFalse((self.run.path("dist") / "lesson.html").exists())
