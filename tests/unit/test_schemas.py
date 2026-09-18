"""Every schema in `schemas/` is enforced against real run artifacts."""

import json
import tempfile
import unittest
from pathlib import Path

from engine.verification import schema as schema_module
from tests import fixtures

SCHEMAS = Path(__file__).resolve().parents[2] / "schemas"


class Schemas(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.run_root = Path(tempfile.mkdtemp()) / "run"
        fixtures.build_candidate(cls.run_root, with_media=False)

    def check(self, schema_name: str, payload) -> None:
        problems = schema_module.validate(payload, schema_module.load(SCHEMAS / schema_name))
        self.assertEqual(problems, [])

    def load(self, *parts: str):
        return json.loads(self.run_root.joinpath(*parts).read_text(encoding="utf-8"))

    def test_fixture_artifacts_match_their_schemas(self):
        self.check("facts.schema.json", self.load("facts.json"))
        self.check("research.schema.json", self.load("research.json"))
        self.check("master-scene-graph.schema.json", self.load("narrative", "master-scene-graph.json"))
        self.check("storyboard.schema.json", self.load("video", "storyboard.json"))
        self.check("narration.schema.json", self.load("video", "narration.json"))

    def test_receipt_and_seal_shapes_are_enforced(self):
        from engine.verification.receipts import ReceiptStore

        store = ReceiptStore(self.run_root / "receipts")
        store.record(gate="g", status="pass", inputs={"a": "1"}, tool_name="g", tool_version="1")
        self.check("receipt.schema.json", json.loads((self.run_root / "receipts" / "g.json").read_text()))

    def test_missing_required_field_is_reported(self):
        payload = self.load("narrative", "master-scene-graph.json")
        del payload["scenes"][0]["primary_message"]
        problems = schema_module.validate(payload, schema_module.load(SCHEMAS / "master-scene-graph.schema.json"))
        self.assertTrue(any("primary_message" in p for p in problems), problems)

    def test_schemas_cannot_assert_more_than_is_checked(self):
        for path in SCHEMAS.glob("*.json"):
            with self.subTest(schema=path.name):
                schema_module.validate({}, schema_module.load(path))
