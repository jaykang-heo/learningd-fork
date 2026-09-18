"""Durable run state (spec 14, 15, 16).

`run.yaml` is the sole owner of a run's orchestration phase. Anything derivable
from other files - candidate hashes, gate counts, progress - is deliberately not
stored here, because a second owner is a second truth.

Only the Primary Orchestrator writes through this module (spec 7.2).
"""

from __future__ import annotations

import hashlib
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from engine import minyaml
from engine.atomic import write_text
from engine.hashing import sha256_file, sha256_text
from runtime.orchestration import events, phases

RUN_SUBDIRS = (
    "source",
    "solutions",
    "narrative",
    "document",
    "video/assets",
    "reviews",
    "receipts",
    "seal",
    "tmp",
    "dist",
)

_UNFINISHED = tuple(p for p in phases.PHASES if p != "released")


class DuplicateRunAmbiguity(RuntimeError):
    """Several resumable runs match one request; picking one is not allowed."""


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def request_fingerprint(request_text: str) -> str:
    """Stable identity of a request, insensitive to incidental whitespace."""
    normalized = re.sub(r"\s+", " ", request_text.strip().lower())
    return sha256_text(normalized)


@dataclass(frozen=True)
class Run:
    root: Path

    @property
    def run_yaml(self) -> Path:
        return self.root / "run.yaml"

    @property
    def events_path(self) -> Path:
        return self.root / "events.jsonl"

    def state(self) -> dict[str, Any]:
        return minyaml.loads(self.run_yaml.read_text(encoding="utf-8"))

    @property
    def run_id(self) -> str:
        return str(self.state()["run_id"])

    @property
    def phase(self) -> str:
        return str(self.state()["phase"])

    def path(self, *parts: str) -> Path:
        return self.root.joinpath(*parts)

    def log(self, event_type: str, **fields: Any) -> dict[str, Any]:
        return events.append(self.events_path, event_type, run_id=self.run_id, **fields)

    def advance_to(self, target: str, *, evidence: list[str] | None = None) -> str:
        """Move the run one boundary forward. Callers must already hold PASS
        receipts for the target phase; `RunStore.advance` enforces that."""
        state = self.state()
        phases.check_transition(str(state["phase"]), target)
        state["phase"] = target
        state["updated_at"] = _now()
        write_text(self.run_yaml, minyaml.dumps(state))
        self.log("phase_advanced", phase=target, evidence=evidence or [])
        return target


class RunStore:
    """Owns the `runs/` directory: creation, lookup and duplicate semantics."""

    def __init__(self, root: str | Path, *, project_revision: str = "unknown", quality_policy_path: str | Path | None = None):
        self.root = Path(root)
        self.project_revision = project_revision
        self.quality_policy_path = Path(quality_policy_path) if quality_policy_path else None

    def quality_policy_hash(self) -> str:
        if self.quality_policy_path and self.quality_policy_path.exists():
            return sha256_file(self.quality_policy_path)
        return sha256_text("")

    def all_runs(self) -> list[Run]:
        if not self.root.exists():
            return []
        return sorted(
            (Run(p) for p in self.root.iterdir() if (p / "run.yaml").exists()),
            key=lambda r: r.run_id,
        )

    def create(self, *, problem_key: str, request_text: str, run_id: str | None = None) -> Run:
        run_id = run_id or f"{time.strftime('%Y%m%d-%H%M%S', time.gmtime())}-{uuid.uuid4().hex[:8]}"
        root = self.root / run_id
        if root.exists():
            raise FileExistsError(f"run already exists: {run_id}")
        for sub in RUN_SUBDIRS:
            (root / sub).mkdir(parents=True, exist_ok=True)
        state = {
            "schema_version": 1,
            "run_id": run_id,
            "problem_key": problem_key,
            "request_fingerprint": request_fingerprint(request_text),
            "phase": "created",
            "created_at": _now(),
            "updated_at": _now(),
            "project_revision": self.project_revision,
            "quality_policy_hash": self.quality_policy_hash(),
        }
        write_text(root / "run.yaml", minyaml.dumps(state))
        run = Run(root)
        run.log("run_created", problem_key=problem_key)
        return run

    def resumable(self, *, problem_key: str, request_text: str) -> list[Run]:
        fingerprint = request_fingerprint(request_text)
        found = []
        for run in self.all_runs():
            state = run.state()
            if (
                state.get("problem_key") == problem_key
                and state.get("request_fingerprint") == fingerprint
                and state.get("phase") in _UNFINISHED
            ):
                found.append(run)
        return found

    def create_or_resume(self, *, problem_key: str, request_text: str) -> Run:
        """Spec 16: one unfinished twin resumes; several never auto-merge, and a
        released twin still starts a new run because tooling and policy move."""
        candidates = self.resumable(problem_key=problem_key, request_text=request_text)
        if len(candidates) == 1:
            run = candidates[0]
            run.log("run_resumed", phase=run.phase)
            return run
        if len(candidates) > 1:
            raise DuplicateRunAmbiguity(
                "multiple unfinished runs match this request; an explicit run id is required: "
                + ", ".join(r.run_id for r in candidates)
            )
        return self.create(problem_key=problem_key, request_text=request_text)

    def get(self, run_id: str) -> Run:
        root = self.root / run_id
        if not (root / "run.yaml").exists():
            raise FileNotFoundError(f"no such run: {run_id}")
        return Run(root)


def problem_key_from_source(platform: str | None, identifier: str | None, source_bytes: bytes | None) -> str:
    """Official platform identity when there is one, snapshot hash otherwise."""
    if platform and identifier:
        return f"{platform.strip().lower()}:{identifier.strip().lower()}"
    if source_bytes is None:
        raise ValueError("a problem key needs either a platform identity or source bytes")
    return "snapshot:" + hashlib.sha256(source_bytes).hexdigest()[:32]
