"""Notes: the Author's remarks on one entity for the Editor, the only channel from Desk (ADR 0005).

A Note has a ``kind`` (``KINDS``) and a ``key``: a repo-relative path for a
``document``, the skill name for a ``skill``, the id of a ``video``, ``card`` or
``idea``. A ``general`` Note has an empty key and applies to every skill. A Note
is open until it is resolved; ``list`` shows open Notes unless asked for all.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

from cf.research.store import Store, now_iso

KINDS = ("document", "skill", "video", "card", "idea", "general")


class NoteError(Exception):
    """A Note request that cannot be carried out; the message says why."""


@dataclass(frozen=True)
class Note:
    id: int
    kind: str
    key: str
    text: str
    created_at: str
    resolved_at: str | None

    def to_dict(self) -> dict:
        return asdict(self)


def _note(row: dict) -> Note:
    return Note(**row)


def get(store: Store, note_id: int) -> Note:
    row = store.one("SELECT * FROM note WHERE id = ?", (note_id,))
    if row is None:
        raise NoteError(f"no Note #{note_id}")
    return _note(row)


def list(store: Store, *, kind: str | None = None, key: str | None = None,
         include_resolved: bool = False) -> list[Note]:
    where, params = [], []
    if kind is not None:
        where.append("kind = ?")
        params.append(kind)
    if key is not None:
        where.append("key = ?")
        params.append(key)
    if not include_resolved:
        where.append("resolved_at IS NULL")
    sql = "SELECT * FROM note" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id"
    return [_note(r) for r in store.query(sql, tuple(params))]


def add(store: Store, kind: str, key: str, text: str, *, now: str | None = None) -> Note:
    if kind not in KINDS:
        raise NoteError(f"unknown Note kind {kind!r}; one of: {', '.join(KINDS)}")
    key, text = key.strip(), text.strip()
    if kind == "general" and key:
        raise NoteError("a general Note has an empty key")
    if kind != "general" and not key:
        raise NoteError(f"a {kind} Note needs a key")
    if not text:
        raise NoteError("a Note needs text")
    with store.transaction():
        cur = store.conn.execute("INSERT INTO note (kind, key, text, created_at) VALUES (?, ?, ?, ?)",
                                 (kind, key, text, now or now_iso()))
    return get(store, cur.lastrowid)


def resolve(store: Store, note_id: int, *, now: str | None = None) -> Note:
    note = get(store, note_id)
    if note.resolved_at is None:
        with store.transaction():
            store.conn.execute("UPDATE note SET resolved_at = ? WHERE id = ?", (now or now_iso(), note_id))
    return get(store, note_id)


def delete(store: Store, note_id: int) -> Note:
    note = get(store, note_id)
    with store.transaction():
        store.conn.execute("DELETE FROM note WHERE id = ?", (note_id,))
    return note
