"""Voice adapters.

`local-say` exists so the pipeline is runnable and testable before Remaining
Decision R1 is made. It is explicitly not release quality (spec 32.2), so a run
using it can render audio but can never record a PASS on the voice gate.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Callable

from engine.voice.provider import SynthesisRequest, SynthesisResult, VoiceUnavailable


class LocalSayProvider:
    """macOS `say`: deterministic, free, robotic - development only."""

    name = "local-say"
    model = "say/v1"
    release_quality = False

    def __init__(self, voice: str = "Yuna"):
        self.voice = voice

    def synthesize(self, request: SynthesisRequest, idempotency_key: str) -> SynthesisResult:
        binary = shutil.which("say")
        if binary is None:
            raise VoiceUnavailable("`say` is not available on this host")
        with tempfile.TemporaryDirectory() as tmp:
            aiff = Path(tmp) / "out.aiff"
            subprocess.run(
                [binary, "-v", self.voice, "-o", str(aiff), request.text],
                check=True,
                capture_output=True,
            )
            audio = aiff.read_bytes()
        return SynthesisResult(
            audio=audio,
            provider_request_id=f"local-say:{idempotency_key[:16]}",
            metadata={"voice": self.voice, "release_quality": False, "container": "aiff"},
        )


class NullProvider:
    """Records the request and returns silence; used by tests and dry runs."""

    name = "null"
    model = "null/v1"
    release_quality = False

    def __init__(self) -> None:
        self.calls: list[str] = []

    def synthesize(self, request: SynthesisRequest, idempotency_key: str) -> SynthesisResult:
        self.calls.append(idempotency_key)
        return SynthesisResult(
            audio=b"\x00" * 64,
            provider_request_id=f"null:{idempotency_key[:16]}",
            metadata={"release_quality": False},
        )


_REGISTRY: dict[str, Callable[..., Any]] = {
    "local-say": LocalSayProvider,
    "null": NullProvider,
}


def build(name: str, **options: Any):
    if name not in _REGISTRY:
        raise VoiceUnavailable(
            f"voice provider {name!r} is not implemented; "
            "Remaining Decision R1 must pick one before a natural-voice release"
        )
    return _REGISTRY[name](**options)
