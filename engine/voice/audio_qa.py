"""Mechanical audio QA (spec 32.4).

Mechanical checks can only refute naturalness, never prove it, so the perceptual
verdict stays a separate gate with its own reviewer evidence (spec 32.5).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path


class AudioProbeUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class AudioStats:
    duration_seconds: float
    peak_db: float
    mean_db: float


def measure(path: str | Path) -> AudioStats:
    binary = shutil.which("ffmpeg")
    probe = shutil.which("ffprobe")
    if binary is None or probe is None:
        raise AudioProbeUnavailable("ffmpeg/ffprobe are required for mechanical audio QA")
    duration = float(
        json.loads(
            subprocess.run(
                [probe, "-v", "error", "-print_format", "json", "-show_format", str(path)],
                capture_output=True,
                text=True,
                check=True,
            ).stdout
        )["format"]["duration"]
    )
    stderr = subprocess.run(
        [binary, "-hide_banner", "-i", str(path), "-af", "volumedetect", "-f", "null", "-"],
        capture_output=True,
        text=True,
    ).stderr
    peak = mean = 0.0
    for line in stderr.splitlines():
        if "max_volume:" in line:
            peak = float(line.split("max_volume:")[1].strip().split()[0])
        elif "mean_volume:" in line:
            mean = float(line.split("mean_volume:")[1].strip().split()[0])
    return AudioStats(duration_seconds=duration, peak_db=peak, mean_db=mean)


def check(stats: AudioStats, *, max_peak_db: float, min_mean_db: float) -> list[str]:
    problems: list[str] = []
    if stats.duration_seconds <= 0:
        problems.append("audio stream has no duration")
    if stats.peak_db > max_peak_db:
        problems.append(f"true peak {stats.peak_db:.1f} dB exceeds {max_peak_db:.1f} dB (clipping)")
    if stats.mean_db < min_mean_db:
        problems.append(f"mean loudness {stats.mean_db:.1f} dB is below {min_mean_db:.1f} dB")
    return problems
