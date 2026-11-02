"""Content ids: what makes an Asset the same Asset after a rename or a move inside its Pack."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path

CHUNK = 1 << 20
ID_LEN = 16


def content_id(path: Path) -> str:
    size = path.stat().st_size
    h = hashlib.sha256(size.to_bytes(8, "big"))
    with open(path, "rb") as f:
        if size <= 2 * CHUNK:
            h.update(f.read())
        else:
            h.update(f.read(CHUNK))
            f.seek(size - CHUNK)
            h.update(f.read(CHUNK))
    return h.hexdigest()[:ID_LEN]


def bundle_id(folder: Path) -> str:
    lines = []
    for dirpath, dirnames, filenames in os.walk(folder, followlinks=False):
        dirnames.sort()
        for name in filenames:
            p = Path(dirpath) / name
            if p.is_symlink():
                continue
            lines.append(f"{p.relative_to(folder).as_posix()}\0{p.stat().st_size}\n")
    return hashlib.sha256("".join(sorted(lines)).encode()).hexdigest()[:ID_LEN]


def disambiguated(cid: str, rel: str) -> str:
    return hashlib.sha256(f"{cid}\0{rel}".encode()).hexdigest()[:ID_LEN]
