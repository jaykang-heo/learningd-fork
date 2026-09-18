import json
import tempfile
import unittest
from pathlib import Path

from engine.atomic import write_text
from engine.release.seal import BundleInputs, ReleaseRefused, SealRefused, release, seal
from engine.verification.receipts import ReceiptStore, ReceiptTampered


def _bundle(root: Path) -> BundleInputs:
    write_text(root / "lesson.html", "<html><body>lesson</body></html>")
    write_text(root / "explainer.mp4", "fake-video-bytes")
    write_text(root / "scene-graph.json", "{}")
    write_text(root / "facts.json", "{}")
    write_text(root / "quality.yaml", "schema_version: 1\n")
    return BundleInputs(
        lesson_html=root / "lesson.html",
        explainer_video=root / "explainer.mp4",
        scene_graph=root / "scene-graph.json",
        facts=root / "facts.json",
        quality_policy=root / "quality.yaml",
    )


class Receipts(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.store = ReceiptStore(self.root / "receipts")

    def test_receipt_is_usable_only_for_its_exact_inputs(self):
        self.store.record(gate="g", status="pass", inputs={"a": "1"}, tool_name="g", tool_version="1")
        self.assertTrue(self.store.usable("g", {"a": "1"}))
        self.assertFalse(self.store.usable("g", {"a": "2"}))

    def test_failed_receipt_never_authorizes(self):
        self.store.record(gate="g", status="fail", inputs={"a": "1"}, tool_name="g", tool_version="1")
        self.assertFalse(self.store.usable("g", {"a": "1"}))

    def test_hand_edited_receipt_is_detected(self):
        self.store.record(gate="g", status="fail", inputs={"a": "1"}, tool_name="g", tool_version="1")
        path = self.root / "receipts" / "g.json"
        payload = json.loads(path.read_text())
        payload["status"] = "pass"
        path.write_text(json.dumps(payload))
        with self.assertRaises(ReceiptTampered):
            self.store.load("g")


class SealAndRelease(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.bundle = _bundle(self.root)
        self.store = ReceiptStore(self.root / "receipts")
        self.hashes = self.bundle.candidate_hashes()
        self.inputs = {"gate-a": {"lesson_html_sha256": self.hashes["lesson_html_sha256"]}}

    def _pass_gate(self):
        self.store.record(
            gate="gate-a", status="pass", inputs=self.inputs["gate-a"], tool_name="gate-a", tool_version="1"
        )

    def test_stale_receipt_cannot_seal(self):
        self._pass_gate()
        write_text(self.bundle.lesson_html, "<html><body>edited after the gate</body></html>")
        with self.assertRaises(SealRefused):
            seal(
                bundle=self.bundle,
                required_gates=["gate-a"],
                store=self.store,
                gate_inputs={"gate-a": {"lesson_html_sha256": self.bundle.candidate_hashes()["lesson_html_sha256"]}},
                seal_path=self.root / "seal" / "bundle-seal.json",
            )

    def test_release_copies_only_sealed_bytes(self):
        self._pass_gate()
        seal(
            bundle=self.bundle,
            required_gates=["gate-a"],
            store=self.store,
            gate_inputs=self.inputs,
            seal_path=self.root / "seal" / "bundle-seal.json",
        )
        dist = release(seal_path=self.root / "seal" / "bundle-seal.json", bundle=self.bundle, dist_dir=self.root / "dist")
        self.assertEqual((dist / "lesson.html").read_text(), "<html><body>lesson</body></html>")
        self.assertTrue((dist / "bundle-seal.json").exists())

    def test_mixed_bundle_is_refused_and_dist_is_untouched(self):
        self._pass_gate()
        seal(
            bundle=self.bundle,
            required_gates=["gate-a"],
            store=self.store,
            gate_inputs=self.inputs,
            seal_path=self.root / "seal" / "bundle-seal.json",
        )
        release(seal_path=self.root / "seal" / "bundle-seal.json", bundle=self.bundle, dist_dir=self.root / "dist")
        write_text(self.bundle.lesson_html, "<html><body>only the html moved on</body></html>")
        with self.assertRaises(ReleaseRefused):
            release(seal_path=self.root / "seal" / "bundle-seal.json", bundle=self.bundle, dist_dir=self.root / "dist")
        self.assertEqual((self.root / "dist" / "lesson.html").read_text(), "<html><body>lesson</body></html>")

    def test_unsealed_bundle_cannot_be_delivered(self):
        with self.assertRaises(FileNotFoundError):
            release(seal_path=self.root / "seal" / "bundle-seal.json", bundle=self.bundle, dist_dir=self.root / "dist")
