import copy
import unittest

from engine.facts.store import Fact, FactsStore, GeneratorError, evaluate
from engine.narrative.scene_graph import SceneGraph, validate
from tests.fixtures import scene_graph_payload


class DerivedFacts(unittest.TestCase):
    def test_generator_reproduces_the_published_number(self):
        self.assertEqual(evaluate("digits(comb(499500,500))"), 1716)
        self.assertEqual(evaluate("comb(36,14)"), 3796297200)

    def test_generators_cannot_reach_outside_arithmetic(self):
        for hostile in ("__import__('os').system('true')", "open('/etc/passwd').read()", "(1).__class__"):
            with self.assertRaises(GeneratorError):
                evaluate(hostile)

    def test_hand_edited_number_is_caught(self):
        store = FactsStore([Fact(id="x", kind="derived_number", value=1470, generator="digits(comb(499500,500))")])
        self.assertEqual(store.recompute(), ["x"])


class SceneGraphInvariants(unittest.TestCase):
    def graph(self, mutate=None) -> SceneGraph:
        payload = copy.deepcopy(scene_graph_payload())
        if mutate:
            mutate(payload)
        return SceneGraph(payload)

    def test_fixture_graph_is_valid(self):
        self.assertEqual(validate(self.graph()), [])

    def test_core_inference_without_a_visual_is_rejected(self):
        def strip(payload):
            payload["scenes"][1]["visuals"] = []
        problems = validate(self.graph(strip))
        self.assertTrue(any("substantive visual" in p for p in problems), problems)

    def test_static_only_representation_transform_is_rejected(self):
        def make_static(payload):
            payload["scenes"][1]["visuals"][0]["kind"] = "static"
        problems = validate(self.graph(make_static))
        self.assertTrue(any("requires_dynamic" in p for p in problems), problems)

    def test_prerequisite_must_come_earlier(self):
        def forward_reference(payload):
            payload["scenes"][0]["prerequisites"] = ["S03"]
        problems = validate(self.graph(forward_reference))
        self.assertTrue(any("must come earlier" in p for p in problems), problems)

    def test_breakthrough_must_precede_the_solution(self):
        def swap(payload):
            payload["scenes"][1]["phase"], payload["scenes"][2]["phase"] = "solution", "breakthrough"
        problems = validate(self.graph(swap))
        self.assertTrue(any("breakthrough" in p for p in problems), problems)

    def test_missing_primary_message_is_rejected(self):
        def blank(payload):
            payload["scenes"][2]["primary_message"] = ""
        problems = validate(self.graph(blank))
        self.assertTrue(any("primary_message" in p for p in problems), problems)

    def test_reconstruction_scene_is_required(self):
        def drop(payload):
            payload["scenes"] = payload["scenes"][:3]
        problems = validate(self.graph(drop))
        self.assertTrue(any("reconstruction" in p for p in problems), problems)

    def test_duplicate_scene_ids_are_rejected(self):
        def duplicate(payload):
            payload["scenes"][2]["scene_id"] = "S02"
        problems = validate(self.graph(duplicate))
        self.assertTrue(any("duplicate scene_id" in p for p in problems), problems)
