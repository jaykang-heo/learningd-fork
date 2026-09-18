#!/usr/bin/env python3
"""`distro` - the deterministic half of a production run.

Agents call these commands instead of judging for themselves whether a boundary
was met. Every command prints what it checked and exits non-zero when the run is
not allowed to move.

    distro new      --problem-key leetcode:1621 --request "..."
    distro status   --run <id>
    distro gate     --run <id> [--phase <phase> | --gate K7]
    distro advance  --run <id>
    distro reconcile --run <id>
    distro seal     --run <id>
    distro release  --run <id>
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from engine import minyaml  # noqa: E402
from engine.release.seal import ReleaseRefused, SealRefused  # noqa: E402
from engine.verification.acceptance import REGISTRY  # noqa: E402
from engine.verification.policy import QualityPolicy  # noqa: E402
from runtime.orchestration.orchestrator import Orchestrator, PhaseBlocked  # noqa: E402
from runtime.orchestration.runstore import DuplicateRunAmbiguity, RunStore  # noqa: E402
from runtime.recovery.reconcile import reconcile  # noqa: E402


def _product_config() -> dict:
    return minyaml.loads((REPO_ROOT / "config" / "product.yaml").read_text(encoding="utf-8"))


def _policy() -> QualityPolicy:
    return QualityPolicy.load(REPO_ROOT / "config" / "quality.yaml")


def _store(root: Path | None) -> RunStore:
    config = _product_config()
    run_root = root or (REPO_ROOT / str(config.get("run_root", "runs")))
    try:
        revision = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        revision = "unknown"
    return RunStore(run_root, project_revision=revision, quality_policy_path=REPO_ROOT / "config" / "quality.yaml")


def _orchestrator(args) -> Orchestrator:
    return Orchestrator(_store(args.run_root).get(args.run), _policy())


def cmd_new(args) -> int:
    store = _store(args.run_root)
    try:
        run = store.create_or_resume(problem_key=args.problem_key, request_text=args.request)
    except DuplicateRunAmbiguity as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({"run_id": run.run_id, "phase": run.phase, "root": str(run.root)}, indent=2))
    return 0


def cmd_status(args) -> int:
    orchestrator = _orchestrator(args)
    phase, blockers = orchestrator.frontier()
    print(json.dumps({"run_id": orchestrator.run.run_id, "phase": phase, "blockers": blockers}, indent=2, ensure_ascii=False))
    return 0


def cmd_gate(args) -> int:
    orchestrator = _orchestrator(args)
    if args.gate:
        gates = [REGISTRY.get(args.gate)]
    elif args.phase:
        gates = list(REGISTRY.required_for_phase(args.phase))
    else:
        gates = list(REGISTRY)
    outcomes = orchestrator.run_gates(gates)
    for outcome in outcomes:
        mark = "PASS" if outcome.passed else "FAIL"
        print(f"{mark} {outcome.gate.key} {outcome.gate.name}: {json.dumps(outcome.detail, ensure_ascii=False)}")
    return 0 if all(o.passed for o in outcomes) else 1


def cmd_advance(args) -> int:
    orchestrator = _orchestrator(args)
    try:
        phase = orchestrator.advance()
    except PhaseBlocked as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 1
    print(f"phase={phase}")
    return 0


def cmd_reconcile(args) -> int:
    print(json.dumps(reconcile(_orchestrator(args)).as_dict(), indent=2, ensure_ascii=False))
    return 0


def cmd_seal(args) -> int:
    try:
        payload = _orchestrator(args).seal()
    except SealRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(payload, indent=2))
    return 0


def cmd_release(args) -> int:
    orchestrator = _orchestrator(args)
    try:
        dist = orchestrator.release()
    except (ReleaseRefused, FileNotFoundError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1
    orchestrator.run.advance_to("released", evidence=["bundle-seal.json"])
    print(f"released -> {dist}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="distro", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-root", type=Path, default=None, help="override the runs/ directory")
    sub = parser.add_subparsers(dest="command", required=True)

    new = sub.add_parser("new", help="create or resume a run")
    new.add_argument("--problem-key", required=True)
    new.add_argument("--request", required=True)
    new.set_defaults(func=cmd_new)

    for name, func, help_text in (
        ("status", cmd_status, "show the phase and what blocks the next one"),
        ("advance", cmd_advance, "advance one phase if its gates authorize it"),
        ("reconcile", cmd_reconcile, "re-derive the resume point after an interruption"),
        ("seal", cmd_seal, "seal the candidate bundle"),
        ("release", cmd_release, "atomically publish the sealed bytes"),
    ):
        sp = sub.add_parser(name, help=help_text)
        sp.add_argument("--run", required=True)
        sp.set_defaults(func=func)

    gate = sub.add_parser("gate", help="evaluate gates and write receipts")
    gate.add_argument("--run", required=True)
    gate.add_argument("--phase")
    gate.add_argument("--gate")
    gate.set_defaults(func=cmd_gate)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
