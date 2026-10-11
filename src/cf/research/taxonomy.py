"""Controlled vocabulary for Reference cards: hook categories, storytelling formats,
editing styles, visual layouts.

The seed lives in the repo (``research/taxonomy.json``) and is loaded into the
store as ``approved`` on every open; only values the store lacks are inserted, so
a value the Author rejected stays rejected. Cards may carry ``proposed:`` values,
which land here as ``proposed`` until the Author approves or rejects them.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from cf.research.store import Store, now_iso

REPO_ROOT = Path(__file__).resolve().parents[3]
SEED_PATH = REPO_ROOT / "research" / "taxonomy.json"
SEED_SCHEMA = "cf-taxonomy-seed/1"
KINDS = ("hook_category", "storytelling_format", "editing_style", "visual_layout")
STATUSES = ("approved", "proposed", "rejected")


class TaxonomyError(Exception):
    """The seed file or a taxonomy request breaks the rules."""


@dataclass(frozen=True)
class TaxonomyValue:
    kind: str
    value: str
    status: str
    source: str
    label: str | None = None
    note: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def read_seed(path: str | Path = SEED_PATH) -> list[TaxonomyValue]:
    """Seed entries in file order, first occurrence of a (kind, value) wins."""
    try:
        data = json.loads(Path(path).read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise TaxonomyError(f"taxonomy seed {path}: {exc}") from exc
    if data.get("schema") != SEED_SCHEMA:
        raise TaxonomyError(f"taxonomy seed {path}: schema must be {SEED_SCHEMA!r}")
    out: list[TaxonomyValue] = []
    seen: set[tuple[str, str]] = set()
    for kind, groups in (data.get("kinds") or {}).items():
        if kind not in KINDS:
            raise TaxonomyError(f"taxonomy seed {path}: unknown kind {kind!r}, expected one of {KINDS}")
        for group in groups:
            source = group.get("source") or "seed"
            for item in group.get("values", []):
                value = item.get("value")
                if not value or not isinstance(value, str):
                    raise TaxonomyError(f"taxonomy seed {path}: {kind} entry without a value: {item!r}")
                if (kind, value) in seen:
                    continue
                seen.add((kind, value))
                out.append(TaxonomyValue(kind, value, "approved", source,
                                         item.get("label"), item.get("note")))
    return out


def load_seed(store: Store, path: str | Path = SEED_PATH) -> int:
    """Insert seed values the store lacks as approved; return how many were new."""
    entries = read_seed(path)
    ts = now_iso()
    with store.transaction() as c:
        before = c.total_changes
        c.executemany(
            "INSERT OR IGNORE INTO taxonomy (kind, value, label, note, status, source, created_at) "
            "VALUES (?, ?, ?, ?, 'approved', ?, ?)",
            [(e.kind, e.value, e.label, e.note, e.source, ts) for e in entries])
        return c.total_changes - before


def values(store: Store, kind: str | None = None, status: str | None = None) -> list[TaxonomyValue]:
    """Taxonomy rows, optionally narrowed by kind and status, ordered by kind then value."""
    if kind is not None and kind not in KINDS:
        raise TaxonomyError(f"unknown taxonomy kind {kind!r}, expected one of {KINDS}")
    if status is not None and status not in STATUSES:
        raise TaxonomyError(f"unknown taxonomy status {status!r}, expected one of {STATUSES}")
    where, params = [], []
    if kind is not None:
        where.append("kind = ?")
        params.append(kind)
    if status is not None:
        where.append("status = ?")
        params.append(status)
    sql = "SELECT kind, value, status, source, label, note FROM taxonomy"
    if where:
        sql += " WHERE " + " AND ".join(where)
    rows = store.query(sql + " ORDER BY kind, value", tuple(params))
    return [TaxonomyValue(**r) for r in rows]
