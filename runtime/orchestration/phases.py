"""Run phases (spec 15).

A phase names the last boundary a run fully passed. Failure never becomes a
phase: it is an event plus a failed attempt receipt, so recovery restarts at the
step after the last confirmed phase.
"""

from __future__ import annotations

PHASES: tuple[str, ...] = (
    "created",
    "source_locked",
    "knowledge_ready",
    "narrative_ready",
    "document_ready",
    "video_ready",
    "acceptance_ready",
    "sealed",
    "released",
)

_INDEX = {name: i for i, name in enumerate(PHASES)}


class InvalidTransition(ValueError):
    pass


def index(phase: str) -> int:
    try:
        return _INDEX[phase]
    except KeyError as exc:
        raise InvalidTransition(f"unknown phase: {phase}") from exc


def next_phase(phase: str) -> str | None:
    i = index(phase)
    return PHASES[i + 1] if i + 1 < len(PHASES) else None


def check_transition(current: str, target: str) -> None:
    """Only the immediate successor is a legal transition (spec 15.2)."""
    if index(target) != index(current) + 1:
        raise InvalidTransition(
            f"illegal phase transition {current} -> {target}; "
            "only the immediate next phase is allowed"
        )
