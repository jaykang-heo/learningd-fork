"""Bundle seal and atomic release (spec 40).

A seal binds exact bytes to the exact receipts that authorized them. Release
copies only those bytes, and a failure mid-release leaves the previous `dist/`
untouched.
"""

from __future__ import annotations

import json
import shutil
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from engine.atomic import replace_directory, write_text
from engine.hashing import sha256_file
from engine.verification.receipts import ReceiptStore

SEAL_KIND = "verified-learning-bundle-seal"
SCHEMA_VERSION = 1


class SealRefused(RuntimeError):
    """Required evidence is missing, failed or stale; nothing is sealed."""


class ReleaseRefused(RuntimeError):
    """The sealed bytes do not match what is on disk; `dist/` is untouched."""


@dataclass(frozen=True)
class BundleInputs:
    lesson_html: Path
    explainer_video: Path
    scene_graph: Path
    facts: Path
    quality_policy: Path

    def candidate_hashes(self) -> dict[str, str]:
        return {
            "lesson_html_sha256": sha256_file(self.lesson_html),
            "explainer_video_sha256": sha256_file(self.explainer_video),
            "scene_graph_sha256": sha256_file(self.scene_graph),
            "facts_sha256": sha256_file(self.facts),
            "quality_policy_sha256": sha256_file(self.quality_policy),
        }


def seal(
    *,
    bundle: BundleInputs,
    required_gates: Sequence[str],
    store: ReceiptStore,
    gate_inputs: Mapping[str, Mapping[str, str]],
    seal_path: str | Path,
) -> dict:
    hashes = bundle.candidate_hashes()
    problems: list[str] = []
    for gate in required_gates:
        receipt = store.load(gate)
        if receipt is None:
            problems.append(f"{gate}: no receipt")
        elif not receipt.passed:
            problems.append(f"{gate}: status {receipt.status}")
        elif not receipt.current_for(gate_inputs[gate]):
            problems.append(f"{gate}: receipt is stale for this candidate")
    if problems:
        raise SealRefused("cannot seal this bundle: " + "; ".join(problems))

    payload = {
        "kind": SEAL_KIND,
        "schema_version": SCHEMA_VERSION,
        **hashes,
        "required_receipts": sorted(required_gates),
        "sealed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "ready_for_delivery": True,
    }
    write_text(seal_path, json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n")
    return payload


def release(*, seal_path: str | Path, bundle: BundleInputs, dist_dir: str | Path) -> Path:
    payload = json.loads(Path(seal_path).read_text(encoding="utf-8"))
    if payload.get("kind") != SEAL_KIND or not payload.get("ready_for_delivery"):
        raise ReleaseRefused("seal is not a delivery authorization")
    current = bundle.candidate_hashes()
    drifted = [
        key
        for key in ("lesson_html_sha256", "explainer_video_sha256", "scene_graph_sha256", "facts_sha256")
        if payload.get(key) != current[key]
    ]
    if drifted:
        raise ReleaseRefused(
            "sealed bytes changed since the seal was written: " + ", ".join(drifted)
        )

    dist_dir = Path(dist_dir)
    staging = Path(tempfile.mkdtemp(dir=dist_dir.parent, prefix=".dist.tmp."))
    try:
        shutil.copy2(bundle.lesson_html, staging / "lesson.html")
        shutil.copy2(bundle.explainer_video, staging / "explainer.mp4")
        shutil.copy2(seal_path, staging / "bundle-seal.json")
        copied = {
            "lesson_html_sha256": sha256_file(staging / "lesson.html"),
            "explainer_video_sha256": sha256_file(staging / "explainer.mp4"),
        }
        for key, value in copied.items():
            if payload[key] != value:
                raise ReleaseRefused(f"copied artifact hash mismatch for {key}")
        return replace_directory(dist_dir, staging)
    except BaseException:
        shutil.rmtree(staging, ignore_errors=True)
        raise
