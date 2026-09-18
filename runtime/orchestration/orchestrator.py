"""Primary Orchestrator: the single canonical integration owner (spec 7.2).

It is the only writer of `run.yaml`, the only actor that turns worker output
into canonical state, and the only actor that may seal and release. Everything
it does is decided from receipts, never from an impression of progress.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from engine.release.seal import BundleInputs, release as release_bundle, seal as seal_bundle
from engine.verification.acceptance import REGISTRY
from engine.verification.context import Candidate
from engine.verification.gates import Gate, gate_inputs, missing_receipts, run_gate
from engine.verification.policy import QualityPolicy
from engine.verification.receipts import ReceiptStore
from runtime.orchestration import phases
from runtime.orchestration.runstore import Run


class PhaseBlocked(RuntimeError):
    """The next phase is not authorized by current PASS receipts."""


@dataclass(frozen=True)
class GateOutcome:
    gate: Gate
    passed: bool
    detail: dict


class Orchestrator:
    def __init__(self, run: Run, policy: QualityPolicy, registry=REGISTRY):
        self.run = run
        self.policy = policy
        self.registry = registry
        self.receipts = ReceiptStore(run.path("receipts"))

    def candidate(self) -> Candidate:
        return Candidate(run_root=self.run.root, policy=self.policy)

    def run_gates(self, gates: Sequence[Gate]) -> list[GateOutcome]:
        candidate = self.candidate()
        hashes = candidate.hashes()
        outcomes: list[GateOutcome] = []
        for gate in gates:
            receipt = run_gate(gate, candidate, hashes, self.receipts)
            outcomes.append(GateOutcome(gate, receipt.passed, receipt.detail))
            self.run.log(
                "gate_evaluated",
                gate=gate.key,
                name=gate.name,
                status=receipt.status,
                detail=receipt.detail,
            )
        return outcomes

    def run_phase_gates(self, phase: str) -> list[GateOutcome]:
        return self.run_gates(self.registry.required_for_phase(phase))

    def blockers(self, phase: str) -> list[str]:
        candidate = self.candidate()
        return missing_receipts(self.registry.required_for_phase(phase), candidate.hashes(), self.receipts)

    def advance(self) -> str:
        """Advance one boundary if, and only if, its gates currently authorize it."""
        current = self.run.phase
        target = phases.next_phase(current)
        if target is None:
            return current
        problems = self.blockers(target)
        if problems:
            self.run.log("phase_blocked", phase=target, blockers=problems)
            raise PhaseBlocked(
                f"cannot advance {current} -> {target}:\n  " + "\n  ".join(problems)
            )
        return self.run.advance_to(target, evidence=[g.name for g in self.registry.required_for_phase(target)])

    def frontier(self) -> tuple[str, list[str]]:
        """Where recovery should resume: the current phase and what blocks the next."""
        current = self.run.phase
        target = phases.next_phase(current)
        if target is None:
            return current, []
        return current, self.blockers(target)

    # --- seal / release ---------------------------------------------------
    def bundle(self) -> BundleInputs:
        candidate = self.candidate()
        return BundleInputs(
            lesson_html=candidate.lesson_path,
            explainer_video=candidate.video_path,
            scene_graph=candidate.scene_graph_path,
            facts=candidate.facts_path,
            quality_policy=self.policy.path,
        )

    def seal(self) -> dict:
        candidate = self.candidate()
        hashes = candidate.hashes()
        inputs = {g.name: gate_inputs(g, hashes) for g in self.registry}
        payload = seal_bundle(
            bundle=self.bundle(),
            required_gates=self.registry.names(),
            store=self.receipts,
            gate_inputs=inputs,
            seal_path=self.run.path("seal", "bundle-seal.json"),
        )
        self.run.log("bundle_sealed", lesson=payload["lesson_html_sha256"], video=payload["explainer_video_sha256"])
        return payload

    def release(self, dist_dir: str | Path | None = None) -> Path:
        target = Path(dist_dir) if dist_dir else self.run.path("dist")
        released = release_bundle(
            seal_path=self.run.path("seal", "bundle-seal.json"),
            bundle=self.bundle(),
            dist_dir=target,
        )
        self.run.log("released", dist=str(released))
        return released
