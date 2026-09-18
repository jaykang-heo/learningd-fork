"""Rendered media inspection (spec 28.2).

`ffprobe` owns the answer to "what is actually in this file"; nothing here
trusts a render log. When ffprobe is unavailable the probe says so, and the
caller fails the gate instead of assuming the file is fine.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class ProbeUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class MediaInfo:
    path: Path
    duration_seconds: float
    width: int
    height: int
    fps: float
    has_audio: bool
    audio_channels: int
    audio_sample_rate: int


def _fraction(text: str) -> float:
    if "/" in text:
        num, _, den = text.partition("/")
        denominator = float(den)
        return float(num) / denominator if denominator else 0.0
    return float(text)


def probe(path: str | Path) -> MediaInfo:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(path)
    binary = shutil.which("ffprobe")
    if binary is None:
        raise ProbeUnavailable(
            "ffprobe is not installed; the video technical gate cannot be evaluated"
        )
    out = subprocess.run(
        [binary, "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    payload = json.loads(out)
    video = next((s for s in payload.get("streams", []) if s.get("codec_type") == "video"), None)
    audio = next((s for s in payload.get("streams", []) if s.get("codec_type") == "audio"), None)
    if video is None:
        raise ValueError(f"{path} has no video stream")
    return MediaInfo(
        path=path,
        duration_seconds=float(payload.get("format", {}).get("duration", 0.0)),
        width=int(video.get("width", 0)),
        height=int(video.get("height", 0)),
        fps=_fraction(str(video.get("avg_frame_rate", "0/1"))),
        has_audio=audio is not None,
        audio_channels=int(audio.get("channels", 0)) if audio else 0,
        audio_sample_rate=int(audio.get("sample_rate", 0)) if audio else 0,
    )
