"""Receipts: immutable evidence that one gate passed for one exact input set.

A receipt is usable only while every dependency hash it recorded still matches
the candidate being released (spec 39). That is what makes "the gate passed
yesterday" unable to authorize today's different bytes.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from engine.atomic import write_text
from engine.hashing import canonical_json, sha256_text

SCHEMA_VERSION = 1


class ReceiptTampered(RuntimeError):
    """A receipt file's recorded self-hash does not match its content."""


def _self_hash(payload: Mapping[str, Any]) -> str:
    body = {k: v for k, v in payload.items() if k != "receipt_sha256"}
    return sha256_text(canonical_json(body))


@dataclass(frozen=True)
class Receipt:
    gate: str
    status: str
    inputs: dict[str, str]
    tool: dict[str, str]
    created_at: str
    detail: dict[str, Any]
    receipt_sha256: str

    def to_json(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "gate": self.gate,
            "status": self.status,
            "inputs": dict(self.inputs),
            "tool": dict(self.tool),
            "created_at": self.created_at,
            "detail": self.detail,
            "receipt_sha256": self.receipt_sha256,
        }

    @property
    def passed(self) -> bool:
        return self.status == "pass"

    def current_for(self, inputs: Mapping[str, str]) -> bool:
        """True only when every recorded dependency hash still matches."""
        return dict(self.inputs) == dict(inputs)


class ReceiptStore:
    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def _path(self, gate: str) -> Path:
        return self.directory / f"{gate}.json"

    def record(
        self,
        *,
        gate: str,
        status: str,
        inputs: Mapping[str, str],
        tool_name: str,
        tool_version: str,
        detail: Mapping[str, Any] | None = None,
    ) -> Receipt:
        if status not in ("pass", "fail"):
            raise ValueError(f"receipt status must be pass or fail, got {status!r}")
        payload: dict[str, Any] = {
            "schema_version": SCHEMA_VERSION,
            "gate": gate,
            "status": status,
            "inputs": dict(inputs),
            "tool": {"name": tool_name, "version": tool_version},
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "detail": dict(detail or {}),
        }
        payload["receipt_sha256"] = _self_hash(payload)
        write_text(self._path(gate), json.dumps(payload, sort_keys=True, ensure_ascii=False, indent=2) + "\n")
        return _from_payload(payload)

    def load(self, gate: str) -> Receipt | None:
        path = self._path(gate)
        if not path.exists():
            return None
        payload = json.loads(path.read_text(encoding="utf-8"))
        expected = _self_hash(payload)
        if payload.get("receipt_sha256") != expected:
            raise ReceiptTampered(
                f"receipt {gate} was edited after it was written; delete it and rerun the gate"
            )
        return _from_payload(payload)

    def usable(self, gate: str, inputs: Mapping[str, str]) -> bool:
        receipt = self.load(gate)
        return bool(receipt and receipt.passed and receipt.current_for(inputs))


def _from_payload(payload: Mapping[str, Any]) -> Receipt:
    return Receipt(
        gate=str(payload["gate"]),
        status=str(payload["status"]),
        inputs=dict(payload["inputs"]),
        tool=dict(payload["tool"]),
        created_at=str(payload["created_at"]),
        detail=dict(payload.get("detail", {})),
        receipt_sha256=str(payload["receipt_sha256"]),
    )
