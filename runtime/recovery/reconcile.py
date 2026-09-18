"""Restart reconciliation (spec 43).

After any interruption the run is re-derived from durable state: the phase in
`run.yaml`, the receipts on disk and the bytes they bind to. Nothing is trusted
because a previous process said it finished.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from runtime.orchestration import phases
from runtime.orchestration.orchestrator import Orchestrator


@dataclass(frozen=True)
class Reconciliation:
    phase: str
    next_phase: str | None
    blockers: list[str]
    stale_receipts: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "phase": self.phase,
            "next_phase": self.next_phase,
            "blockers": list(self.blockers),
            "stale_receipts": list(self.stale_receipts),
        }


def reconcile(orchestrator: Orchestrator) -> Reconciliation:
    phase, blockers = orchestrator.frontier()
    candidate = orchestrator.candidate()
    hashes = candidate.hashes()
    stale: list[str] = []
    for gate in orchestrator.registry:
        receipt = orchestrator.receipts.load(gate.name)
        if receipt is None:
            continue
        expected = {k: hashes[k] for k in gate.inputs}
        if receipt.passed and not receipt.current_for(expected):
            stale.append(gate.name)
    result = Reconciliation(phase, phases.next_phase(phase), blockers, stale)
    orchestrator.run.log("reconciled", **result.as_dict())
    return result
