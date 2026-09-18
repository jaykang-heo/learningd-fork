import tempfile
import unittest
from pathlib import Path

from runtime.orchestration import phases
from runtime.orchestration.integration import (
    IntegrationLedger,
    OutOfOrderResult,
    StaleResult,
    WorkerResult,
)
from runtime.orchestration.runstore import DuplicateRunAmbiguity, RunStore, problem_key_from_source
from runtime.tasks.graph import CyclicTaskGraph, Task, TaskGraph


class PhaseTransitions(unittest.TestCase):
    def setUp(self):
        self.store = RunStore(Path(tempfile.mkdtemp()) / "runs", project_revision="test")

    def test_only_the_next_phase_is_reachable(self):
        run = self.store.create(problem_key="leetcode:1", request_text="teach me")
        run.advance_to("source_locked")
        with self.assertRaises(phases.InvalidTransition):
            run.advance_to("video_ready")
        with self.assertRaises(phases.InvalidTransition):
            run.advance_to("created")
        self.assertEqual(run.phase, "source_locked")

    def test_failure_does_not_become_a_phase(self):
        run = self.store.create(problem_key="leetcode:1", request_text="teach me")
        run.advance_to("source_locked")
        run.log("gate_evaluated", gate="K11", status="fail")
        self.assertEqual(run.phase, "source_locked")

    def test_duplicate_request_resumes_the_single_unfinished_run(self):
        first = self.store.create_or_resume(problem_key="leetcode:1", request_text="LC1 가르쳐줘")
        again = self.store.create_or_resume(problem_key="leetcode:1", request_text="  lc1 가르쳐줘 ")
        self.assertEqual(first.run_id, again.run_id)

    def test_two_unfinished_runs_refuse_to_auto_resolve(self):
        self.store.create(problem_key="leetcode:1", request_text="same")
        self.store.create(problem_key="leetcode:1", request_text="same")
        with self.assertRaises(DuplicateRunAmbiguity):
            self.store.create_or_resume(problem_key="leetcode:1", request_text="same")

    def test_released_twin_starts_a_new_run(self):
        run = self.store.create(problem_key="leetcode:1", request_text="same")
        for phase in phases.PHASES[1:]:
            run.advance_to(phase)
        fresh = self.store.create_or_resume(problem_key="leetcode:1", request_text="same")
        self.assertNotEqual(fresh.run_id, run.run_id)

    def test_problem_key_falls_back_to_the_snapshot_hash(self):
        self.assertEqual(problem_key_from_source("LeetCode", "1621", None), "leetcode:1621")
        self.assertTrue(problem_key_from_source(None, None, b"statement").startswith("snapshot:"))


class WorkerResults(unittest.TestCase):
    def test_stale_base_is_rejected(self):
        ledger = IntegrationLedger()
        result = WorkerResult(
            task_id="document",
            attempt=1,
            base_revision="r1",
            base_artifact_hashes={"facts_sha256": "old"},
            result_revision="r2",
        )
        with self.assertRaises(StaleResult):
            ledger.check(result, current_hashes={"facts_sha256": "new"}, relevant_dependencies={"facts_sha256"})

    def test_irrelevant_change_still_integrates(self):
        ledger = IntegrationLedger()
        result = WorkerResult(
            task_id="document",
            attempt=1,
            base_revision="r1",
            base_artifact_hashes={"captions_sha256": "old"},
            result_revision="r2",
        )
        ledger.check(result, current_hashes={"captions_sha256": "new"}, relevant_dependencies={"facts_sha256"})
        ledger.accept(result)
        self.assertEqual(ledger.accepted_attempt["document"], 1)

    def test_late_result_never_overwrites_a_newer_one(self):
        ledger = IntegrationLedger()
        newer = WorkerResult("document", 2, "r1", {}, "r3")
        ledger.check(newer, current_hashes={}, relevant_dependencies=set())
        ledger.accept(newer)
        late = WorkerResult("document", 1, "r1", {}, "r2")
        with self.assertRaises(OutOfOrderResult):
            ledger.check(late, current_hashes={}, relevant_dependencies=set())


class TaskGraphOrdering(unittest.TestCase):
    def test_ready_set_follows_dependencies(self):
        graph = TaskGraph()
        graph.add(Task("source", "source_locked"))
        graph.add(Task("facts", "knowledge_ready", ("source",)))
        graph.add(Task("scenes", "narrative_ready", ("facts",)))
        self.assertEqual(graph.ready(set()), ["source"])
        self.assertEqual(graph.ready({"source"}), ["facts"])
        self.assertEqual(graph.topological_order(), ["source", "facts", "scenes"])

    def test_cycles_are_refused(self):
        graph = TaskGraph()
        graph.add(Task("a", "p", ("b",)))
        graph.add(Task("b", "p", ("a",)))
        with self.assertRaises(CyclicTaskGraph):
            graph.validate()
