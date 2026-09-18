"""Voice provider boundary and synthesis cache (spec 18.4, 32.3, 33).

The product does not know its release voice vendor yet (Remaining Decision R1),
so the domain depends on this narrow port only. Adapters are registered by name
from `config/providers.yaml`.

Two things are enforced here regardless of vendor:
  * synthesis happens per scene, never as one long take (spec 32.3);
  * an identical request is never paid for twice, and an ambiguous outcome is
    never blindly retried (spec 18.4, 18.5).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from engine.atomic import write_bytes, write_text
from engine.hashing import sha256_bytes, sha256_json


class VoiceUnavailable(RuntimeError):
    """No configured provider can produce release-quality audio."""


class UnknownExternalOutcome(RuntimeError):
    """A paid call may or may not have happened; a blind retry is forbidden."""


@dataclass(frozen=True)
class SynthesisRequest:
    scene_id: str
    text: str
    voice_id: str
    locale: str
    pronunciation: dict[str, str] = field(default_factory=dict)
    prosody: dict[str, Any] = field(default_factory=dict)

    def cache_key(self, provider: str, model: str) -> str:
        return sha256_json(
            {
                "provider": provider,
                "model": model,
                "scene_id": self.scene_id,
                "text": " ".join(self.text.split()),
                "voice_id": self.voice_id,
                "locale": self.locale,
                "pronunciation": self.pronunciation,
                "prosody": self.prosody,
            }
        )


@dataclass(frozen=True)
class SynthesisResult:
    audio: bytes
    provider_request_id: str
    metadata: dict[str, Any]


class VoiceProvider(Protocol):
    name: str
    model: str
    release_quality: bool

    def synthesize(self, request: SynthesisRequest, idempotency_key: str) -> SynthesisResult: ...


class SynthesisCache:
    """Content-addressed store of already-paid-for audio."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)

    def _audio_path(self, key: str) -> Path:
        return self.directory / f"{key}.mp3"

    def _meta_path(self, key: str) -> Path:
        return self.directory / f"{key}.json"

    def get(self, key: str) -> tuple[Path, dict[str, Any]] | None:
        audio, meta = self._audio_path(key), self._meta_path(key)
        if audio.exists() and meta.exists():
            return audio, json.loads(meta.read_text(encoding="utf-8"))
        return None

    def put(self, key: str, result: SynthesisResult) -> Path:
        audio_path = write_bytes(self._audio_path(key), result.audio)
        write_text(
            self._meta_path(key),
            json.dumps(
                {
                    "provider_request_id": result.provider_request_id,
                    "audio_sha256": sha256_bytes(result.audio),
                    "metadata": result.metadata,
                },
                sort_keys=True,
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
        )
        return audio_path


def synthesize_scene(
    provider: VoiceProvider,
    request: SynthesisRequest,
    cache: SynthesisCache,
) -> tuple[Path, bool]:
    """Return (audio path, whether the provider was actually called)."""
    key = request.cache_key(provider.name, provider.model)
    cached = cache.get(key)
    if cached:
        return cached[0], False
    result = provider.synthesize(request, idempotency_key=key)
    return cache.put(key, result), True
