"""Hashed reads and atomic writes shared by every Desk endpoint that edits a file."""

from __future__ import annotations

import hashlib
import os
import stat
import tempfile
from pathlib import Path


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def atomic_write(target: Path, data: bytes) -> None:
    mode = stat.S_IMODE(target.stat().st_mode) if target.exists() else 0o644
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".desk", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
