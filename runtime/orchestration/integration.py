"""Worker result integration (spec 17.3, 17.4, 18.6).

Workers produce proposals. Only the Primary Orchestrator turns a proposal into
canonical state, and only when the world the worker started from is still the
world it is landing into.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


class StaleResult(RuntimeError):
    """The dependencies this worker started from have since changed."""


class OutOfOrderResult(RuntimeError):
    """A late result would overwrite a newer accepted one."""


@dataclass(frozen=True)
class WorkerResult:
    task_id: str
    attempt: int
    base_revision: str
    base_artifact_hashes: dict[str, str]
    result_revision: str
    status: str = "completed"
    evidence: tuple[str, ...] = ()


@dataclass
class IntegrationLedger:
    """Remembers which attempt of each task was accepted."""

    accepted_attempt: dict[str, int] = field(default_factory=dict)

    def check(
        self,
        result: WorkerResult,
        *,
        current_hashes: Mapping[str, str],
        relevant_dependencies: set[str],
    ) -> None:
        if result.status != "completed":
            raise StaleResult(f"{result.task_id}: worker reported status {result.status!r}")
        changed = {
            key
            for key, value in result.base_artifact_hashes.items()
            if current_hashes.get(key) != value
        }
        blocking = changed & relevant_dependencies
        if blocking:
            raise StaleResult(
                f"{result.task_id}: dependencies changed since attempt {result.attempt} "
                f"({', '.join(sorted(blocking))}); rerun on the new base"
            )
        previous = self.accepted_attempt.get(result.task_id)
        if previous is not None and result.attempt <= previous:
            raise OutOfOrderResult(
                f"{result.task_id}: attempt {result.attempt} arrived after attempt {previous} "
                "was accepted; the newer result stands"
            )

    def accept(self, result: WorkerResult) -> None:
        self.accepted_attempt[result.task_id] = result.attempt
