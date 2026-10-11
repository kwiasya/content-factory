"""Controlled vocabulary for Reference cards: hook categories, storytelling formats,
editing styles, visual layouts.

The seed lives in the repo (``research/taxonomy.json``) and is loaded into the
store as ``approved`` on every open; only values the store lacks are inserted, so
a value the Author rejected stays rejected. Cards may carry ``proposed:`` values,
which land here as ``proposed`` (``propose``) until the Author approves or rejects
them (``approve``, ``reject``; ``proposals`` lists what waits). Rules:
``docs/research/reference-card.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from cf.research.store import REPO_ROOT, Store, now_iso

SEED_PATH = REPO_ROOT / "research" / "taxonomy.json"
SEED_SCHEMA = "cf-taxonomy-seed/1"
KINDS = ("hook_category", "storytelling_format", "editing_style", "visual_layout")
STATUSES = ("approved", "proposed", "rejected")
VALUE_RE = re.compile(r"^[a-z0-9]+(_[a-z0-9]+)*$")


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


@dataclass(frozen=True)
class TaxonomyChange:
    """Result of approve/reject: the value now, and the YouTube ids of the cards it touches
    (approve: cards whose ``proposed:`` prefix was dropped; reject: cards that now fail validation)."""
    value: TaxonomyValue
    cards: list[str]

    def to_dict(self) -> dict:
        return {**self.value.to_dict(), "cards": self.cards}


def _check(kind: str, value: str) -> None:
    if kind not in KINDS:
        raise TaxonomyError(f"unknown taxonomy kind {kind!r}, expected one of {KINDS}")
    if not VALUE_RE.match(value or ""):
        raise TaxonomyError(f"taxonomy value {value!r} must be snake_case (a-z, 0-9, _)")


def get(store: Store, kind: str, value: str) -> TaxonomyValue | None:
    row = store.one("SELECT kind, value, status, source, label, note FROM taxonomy WHERE kind = ? AND value = ?",
                    (kind, value))
    return None if row is None else TaxonomyValue(**row)


def propose(store: Store, kind: str, value: str, *, source: str) -> TaxonomyValue:
    """Add ``value`` as proposed unless the kind already has it (any status stays as it is)."""
    _check(kind, value)
    with store.transaction() as c:
        c.execute("INSERT OR IGNORE INTO taxonomy (kind, value, status, source, created_at) "
                  "VALUES (?, ?, 'proposed', ?, ?)", (kind, value, source, now_iso()))
    return get(store, kind, value)


def _set_status(store: Store, kind: str, value: str, status: str) -> TaxonomyValue:
    _check(kind, value)
    with store.transaction() as c:
        c.execute("INSERT INTO taxonomy (kind, value, status, source, created_at) VALUES (?, ?, ?, 'author', ?) "
                  "ON CONFLICT (kind, value) DO UPDATE SET status = excluded.status",
                  (kind, value, status, now_iso()))
    return get(store, kind, value)


def approve(store: Store, kind: str, value: str, *, root: Path | None = None) -> TaxonomyChange:
    """Make ``value`` valid for cards (a value the store lacks is added with source ``author``);
    cards that proposed it lose the ``proposed:`` prefix."""
    from cf.research import card
    v = _set_status(store, kind, value, "approved")
    return TaxonomyChange(v, card.drop_proposed_prefix(store, kind, value, root=root))


def reject(store: Store, kind: str, value: str) -> TaxonomyChange:
    """Make ``value`` invalid for cards, with or without ``proposed:``; it stays rejected when the seed loads."""
    from cf.research import card
    v = _set_status(store, kind, value, "rejected")
    ids = list(dict.fromkeys(h["external_id"] for h in card.cards_using(store, kind, value)))
    return TaxonomyChange(v, ids)


def proposals(store: Store, kind: str | None = None) -> list[TaxonomyValue]:
    """Values awaiting the Author's approval."""
    return values(store, kind=kind, status="proposed")
