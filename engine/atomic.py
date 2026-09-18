"""Write-then-rename helpers (spec 18.2, 40.2).

A canonical output path is never allowed to hold a partial file, so every
producer writes into a sibling temporary path and renames on success.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path


def write_bytes(path: str | Path, data: bytes) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=".tmp")
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
            out.flush()
            os.fsync(out.fileno())
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
    return path


def write_text(path: str | Path, text: str) -> Path:
    return write_bytes(path, text.encode("utf-8"))


def replace_directory(target: str | Path, staged: str | Path) -> Path:
    """Swap `staged` into `target`, leaving `target` untouched on failure."""
    target = Path(target)
    staged = Path(staged)
    if not staged.is_dir():
        raise FileNotFoundError(f"staged directory missing: {staged}")
    target.parent.mkdir(parents=True, exist_ok=True)
    backup = target.parent / f".{target.name}.previous"
    if backup.exists():
        shutil.rmtree(backup)
    had_target = target.exists()
    if had_target:
        os.rename(target, backup)
    try:
        os.rename(staged, target)
    except BaseException:
        if had_target:
            os.rename(backup, target)
        raise
    if backup.exists():
        shutil.rmtree(backup)
    return target
