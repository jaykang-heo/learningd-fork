"""Solution execution and independent oracle agreement (spec 22).

Code that appears in the lesson must run, and its published outputs must be the
outputs it actually produced - not the outputs an agent remembered.
"""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CaseResult:
    name: str
    expected: Any
    actual: Any

    @property
    def agrees(self) -> bool:
        return self.expected == self.actual


@dataclass(frozen=True)
class ExecutionReport:
    solution_path: Path
    cases: tuple[CaseResult, ...]
    stderr: str

    @property
    def passed(self) -> bool:
        return bool(self.cases) and all(case.agrees for case in self.cases)

    def failures(self) -> list[str]:
        return [
            f"{c.name}: expected {c.expected!r}, produced {c.actual!r}"
            for c in self.cases
            if not c.agrees
        ]


_HARNESS = """
import json, sys
sys.path.insert(0, {solution_dir!r})
import importlib.util
spec = importlib.util.spec_from_file_location("solution_under_test", {solution!r})
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
cases = json.loads({cases!r})
entry = getattr(module, cases["entrypoint"])
out = []
for case in cases["cases"]:
    out.append({{"name": case["name"], "expected": case["expected"], "actual": entry(*case["args"])}})
print("<<<RESULT>>>" + json.dumps(out))
"""


def run_python_solution(solution_path: str | Path, cases_path: str | Path, *, timeout: int = 60) -> ExecutionReport:
    """Execute a Python solution against its declared cases in a subprocess.

    The subprocess is an isolation and timeout boundary for code this project
    authored, not a sandbox for hostile code (spec 22.4 keeps fetched code out).
    """
    solution_path = Path(solution_path).resolve()
    cases = json.loads(Path(cases_path).read_text(encoding="utf-8"))
    script = _HARNESS.format(
        solution_dir=str(solution_path.parent),
        solution=str(solution_path),
        cases=json.dumps(cases, ensure_ascii=False),
    )
    with tempfile.TemporaryDirectory() as tmp:
        runner = Path(tmp) / "runner.py"
        runner.write_text(script, encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, str(runner)],
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    marker = "<<<RESULT>>>"
    if marker not in completed.stdout:
        return ExecutionReport(solution_path, (), completed.stderr.strip() or "solution produced no result")
    payload = json.loads(completed.stdout.split(marker, 1)[1].strip())
    return ExecutionReport(
        solution_path,
        tuple(CaseResult(name=r["name"], expected=r["expected"], actual=r["actual"]) for r in payload),
        completed.stderr.strip(),
    )
