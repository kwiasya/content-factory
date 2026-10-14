"""Atomic writes into the Library cache: a temp file in the same folder, then ``os.replace``."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write(target: Path, data: bytes) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, 0o644)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def temp_beside(target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    return target.with_name(f".{target.stem}.part{target.suffix}")
