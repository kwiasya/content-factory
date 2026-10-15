"""Absolute paths inside Reference JSON files (``references relativize``, ADR 0013).

A Reference folder fetched before the store was shared names its own files by absolute paths under the
Mac that fetched it (``/Users/<who>/Movies/content-factory/references/<watchlist>/<id>/...``). On the
share those paths are wrong for both people. ``relativize`` rewrites every JSON string that is an
absolute path with a ``/references/`` part: a file of the same Reference folder becomes relative to
that folder (as new fetches write it), a file of another Reference becomes
``<shared root>/references/...``. Everything else in the file is kept; files without such a path are
not touched.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

MARK = "/references/"


@dataclass
class Report:
    files: int = 0
    changed_files: list[str] = field(default_factory=list)
    paths_before: int = 0
    paths_after: int = 0

    def to_dict(self) -> dict:
        return {"files": self.files, "changed_files": self.changed_files, "absolute_paths_before": self.paths_before,
                "foreign_paths_after": self.paths_after}


def _absolute(value: Any) -> bool:
    return isinstance(value, str) and value.startswith("/") and MARK in value


def _count(node: Any, skip: str | None = None) -> int:
    if isinstance(node, dict):
        return sum(_count(v, skip) for v in node.values())
    if isinstance(node, list):
        return sum(_count(v, skip) for v in node)
    return int(_absolute(node) and not (skip and node.startswith(skip)))


def _rewrite(node: Any, own: str, root: Path) -> Any:
    if isinstance(node, dict):
        return {k: _rewrite(v, own, root) for k, v in node.items()}
    if isinstance(node, list):
        return [_rewrite(v, own, root) for v in node]
    if not _absolute(node):
        return node
    tail = node.rsplit(MARK, 1)[1]
    if tail.startswith(own + "/"):
        return tail[len(own) + 1:]
    return str(root / "references" / tail)


def relativize(root: Path, *, dry_run: bool = False) -> Report:
    """Rewrite the absolute Reference paths in every ``references/<watchlist>/<id>/*.json`` under ``root``."""
    report = Report()
    root = Path(root)
    base = root / "references"
    for path in sorted(base.glob("*/*/*.json")):
        own = f"{path.parent.parent.name}/{path.parent.name}"
        report.files += 1
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        new = _rewrite(data, own, root)
        if new == data:
            continue
        report.paths_before += _count(data)
        report.paths_after += _count(new, f"{root}{MARK}")
        report.changed_files.append(str(path.relative_to(root)))
        if not dry_run:
            tmp = path.with_name(path.name + ".tmp")
            tmp.write_text(json.dumps(new, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            os.replace(tmp, path)
    return report
