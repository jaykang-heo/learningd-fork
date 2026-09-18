"""Acceptance gate registry and runner (spec 37, 38).

Gates are fail-closed: the bundle is releasable only when every required gate
holds a PASS receipt whose dependency hashes equal the current candidate's. No
averaging, no "mostly passed".
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Mapping, Sequence

from engine.verification.receipts import ReceiptStore

TOOL_VERSION = "1"


@dataclass(frozen=True)
class GateResult:
    passed: bool
    detail: dict[str, Any] = field(default_factory=dict)

    @staticmethod
    def ok(**detail: Any) -> "GateResult":
        return GateResult(True, dict(detail))

    @staticmethod
    def failed(reason: str, **detail: Any) -> "GateResult":
        payload = {"reason": reason}
        payload.update(detail)
        return GateResult(False, payload)


@dataclass(frozen=True)
class Gate:
    key: str          # K1..K16
    name: str         # receipt file name
    phase: str        # the phase this gate is required for
    inputs: tuple[str, ...]   # candidate hash keys this gate depends on
    check: Callable[[Any], GateResult]
    semantic: bool = False    # True when a reviewer, not code, produces the verdict


class GateRegistry:
    def __init__(self, gates: Sequence[Gate]):
        by_key: dict[str, Gate] = {}
        for gate in gates:
            if gate.key in by_key:
                raise ValueError(f"duplicate gate key: {gate.key}")
            by_key[gate.key] = gate
        self._gates = tuple(gates)
        self._by_key = by_key
        self._by_name = {g.name: g for g in gates}

    def __iter__(self):
        return iter(self._gates)

    def get(self, key_or_name: str) -> Gate:
        if key_or_name in self._by_key:
            return self._by_key[key_or_name]
        if key_or_name in self._by_name:
            return self._by_name[key_or_name]
        raise KeyError(f"unknown gate: {key_or_name}")

    def required_for_phase(self, phase: str) -> tuple[Gate, ...]:
        return tuple(g for g in self._gates if g.phase == phase)

    def names(self) -> tuple[str, ...]:
        return tuple(g.name for g in self._gates)


def gate_inputs(gate: Gate, candidate: Mapping[str, str]) -> dict[str, str]:
    missing = [key for key in gate.inputs if key not in candidate]
    if missing:
        raise KeyError(f"gate {gate.key} needs candidate hashes {missing}")
    return {key: candidate[key] for key in gate.inputs}


def run_gate(gate: Gate, context: Any, candidate: Mapping[str, str], store: ReceiptStore):
    inputs = gate_inputs(gate, candidate)
    result = gate.check(context)
    return store.record(
        gate=gate.name,
        status="pass" if result.passed else "fail",
        inputs=inputs,
        tool_name=gate.name,
        tool_version=TOOL_VERSION,
        detail=result.detail,
    )


def missing_receipts(
    gates: Sequence[Gate], candidate: Mapping[str, str], store: ReceiptStore
) -> list[str]:
    """Gates that do not currently authorize this candidate, with the reason."""
    problems: list[str] = []
    for gate in gates:
        inputs = gate_inputs(gate, candidate)
        receipt = store.load(gate.name)
        if receipt is None:
            problems.append(f"{gate.key} {gate.name}: no receipt")
        elif not receipt.passed:
            problems.append(f"{gate.key} {gate.name}: last run failed")
        elif not receipt.current_for(inputs):
            changed = sorted(k for k in inputs if receipt.inputs.get(k) != inputs[k])
            problems.append(f"{gate.key} {gate.name}: stale receipt (changed: {', '.join(changed)})")
    return problems
