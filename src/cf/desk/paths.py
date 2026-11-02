"""The one rule for a path Desk serves or writes under a root: plain relative parts, no symlink on the way.

A path qualifies when it is relative, has no empty, `.`, `..` or hidden part, and resolves inside the root
along exactly those parts (so neither a symlink out of the root nor one inside it is followed).
"""

from __future__ import annotations

from pathlib import Path


def plain_parts(rel: str) -> tuple[str, ...] | None:
    parts = tuple(rel.split("/"))
    if not rel or rel.startswith("/") or any(p in ("", ".", "..") or p.startswith(".") for p in parts):
        return None
    return parts


def contained(root: Path, rel: str) -> Path | None:
    """`root / rel` when `rel` qualifies; the file itself may not exist yet."""
    parts = plain_parts(rel)
    if parts is None:
        return None
    base = Path(root).resolve()
    resolved = (base / rel).resolve()
    if not resolved.is_relative_to(base) or resolved.relative_to(base).parts != parts:
        return None
    return Path(root) / rel


def relative_under(root: Path, path: Path) -> str | None:
    """`path` as a relative path under `root` (as given or resolved), without resolving `path` itself."""
    for base in (Path(root), Path(root).resolve()):
        try:
            return Path(path).relative_to(base).as_posix()
        except ValueError:
            continue
    return None
