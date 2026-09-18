"""Canonical facts (spec 20).

Any number that appears in more than one artifact lives here once. A derived
number owns a generator expression, so the document and the video cannot drift
into two different values for the same claim.
"""

from __future__ import annotations

import ast
import json
import math
import operator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

_ALLOWED_CALLS = {
    "comb": math.comb,
    "perm": math.perm,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "isqrt": math.isqrt,
    "digits": lambda n: len(str(abs(int(n)))),
    "len": len,
    "abs": abs,
    "min": min,
    "max": max,
    "sum": sum,
    "pow": pow,
}

_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.Div: operator.truediv,
}


class GeneratorError(ValueError):
    pass


def evaluate(expression: str) -> Any:
    """Evaluate a derived-fact generator.

    Only arithmetic over literals and the whitelisted combinatorial helpers is
    accepted; a fact generator is data in the run, so it never gets `eval`.
    """
    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise GeneratorError(f"cannot parse generator {expression!r}: {exc}") from exc

    def visit(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp) and type(node.op) in _BIN_OPS:
            return _BIN_OPS[type(node.op)](visit(node.left), visit(node.right))
        if isinstance(node, ast.Tuple):
            return tuple(visit(e) for e in node.elts)
        if isinstance(node, ast.List):
            return [visit(e) for e in node.elts]
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            name = node.func.id
            if name not in _ALLOWED_CALLS or node.keywords:
                raise GeneratorError(f"generator function not allowed: {name}")
            return _ALLOWED_CALLS[name](*[visit(a) for a in node.args])
        raise GeneratorError(f"generator element not allowed: {ast.dump(node)}")

    return visit(tree)


@dataclass(frozen=True)
class Fact:
    id: str
    kind: str
    value: Any
    generator: str | None = None
    provenance: tuple[str, ...] = ()
    verification: tuple[str, ...] = ()


class FactsStore:
    def __init__(self, facts: list[Fact]):
        self.facts = facts
        self.by_id = {f.id: f for f in facts}
        if len(self.by_id) != len(facts):
            raise ValueError("duplicate fact id")

    @classmethod
    def load(cls, path: str | Path) -> "FactsStore":
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls(
            [
                Fact(
                    id=item["id"],
                    kind=item.get("kind", "value"),
                    value=item.get("value"),
                    generator=item.get("generator"),
                    provenance=tuple(item.get("provenance", [])),
                    verification=tuple(item.get("verification", [])),
                )
                for item in payload["facts"]
            ]
        )

    def recompute(self) -> list[str]:
        """Return the ids whose stored value disagrees with their generator."""
        mismatched = []
        for fact in self.facts:
            if not fact.generator:
                continue
            if evaluate(fact.generator) != fact.value:
                mismatched.append(fact.id)
        return mismatched

    def value(self, fact_id: str) -> Any:
        return self.by_id[fact_id].value
