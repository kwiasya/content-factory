"""Ideas: what worked in one or more Reference, turned toward the Author's Channel.

An Idea is born in the inbox (skill ``suggest-ideas`` or ``ideas add``) with the
fields of the Sandcastles Idea Detail page (``docs/research/sandcastles-map.md``,
"Поля Idea"). The Author triages it:

    inbox       → shortlisted | discarded   (shortlist, discard)
    discarded   → inbox                     (restore)
    shortlisted → brief                     (only through ``brief.create``)

Every other move raises ``IdeaError`` naming the current status. Notes append
with a timestamp in any status. The title lives in its own column; the other
fields in ``idea.fields`` (JSON); sources are store video ids in
``idea.source_video_ids`` (JSON list).
"""

from __future__ import annotations

import builtins
import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Iterable

from cf.research import card, feed
from cf.research.store import Store, dumps, now_iso, person
from cf.research import watchlist as watchlists

STATUSES = ("inbox", "shortlisted", "discarded", "brief")
TEXT_FIELDS = ("title", "summary", "content_positioning", "hook_alignment")
FIELDS = ("title", "summary", "content_positioning", "storytelling_format", "contrast_mechanism",
          "hook_alignment", "personalizations")
PERSONALIZATIONS = 3

# action → (status it needs, status it leads to)
TRANSITIONS = {
    "shortlist": ("inbox", "shortlisted"),
    "discard": ("inbox", "discarded"),
    "restore": ("discarded", "inbox"),
    "brief": ("shortlisted", "brief"),
}


class IdeaError(Exception):
    """An Idea cannot be written or moved; ``violations`` lists broken field rules."""

    def __init__(self, message: str, violations: Iterable[str] = ()):
        super().__init__(message)
        self.violations = builtins.list(violations)


@dataclass(frozen=True)
class Idea:
    id: int
    watchlist: str
    title: str
    status: str
    fields: dict
    sources: list = field(default_factory=builtins.list)  # [{id, external_id, title, url}]
    notes: list = field(default_factory=builtins.list)    # [{at, text}]
    brief_path: str | None = None
    created_at: str = ""
    updated_at: str = ""
    videos: list = field(default_factory=builtins.list)   # [{slug, owner}] Videos made from it, oldest link first
    brief_owner: str | None = None                         # who wrote the Brief (its file is on their Mac)

    def to_dict(self) -> dict:
        return asdict(self)


# --- validation ---------------------------------------------------------------

def _text(v: Any) -> bool:
    return isinstance(v, str) and bool(v.strip())


def _object(value: Any, where: str, keys: tuple[str, ...], out: list[str]) -> None:
    for k in keys:
        if k not in value:
            out.append(f"{where}.{k}: missing")
        elif not _text(value[k]):
            out.append(f"{where}.{k}: must be a non-empty string")
    out.extend(f"{where}.{k}: unknown field" for k in value if k not in keys)


def validate(fields: dict, store: Store) -> list[str]:
    """Every broken rule of an Idea's fields (title included), one line each; empty when valid."""
    if not isinstance(fields, dict):
        return ["idea: must be a JSON object"]
    out: list[str] = []
    for k in FIELDS:
        if k not in fields:
            out.append(f"{k}: missing")
    for k in TEXT_FIELDS:
        if k in fields and not _text(fields[k]):
            out.append(f"{k}: must be a non-empty string")
    sf = fields.get("storytelling_format")
    if "storytelling_format" in fields:
        if not isinstance(sf, dict):
            out.append("storytelling_format: must be an object {category, why}")
        else:
            _object(sf, "storytelling_format", ("category", "why"), out)
            if _text(sf.get("category")):
                problem = card.category_problem(store, "storytelling_format", sf["category"].strip())
                if problem:
                    out.append(f"storytelling_format.category: {problem}")
    cm = fields.get("contrast_mechanism")
    if cm is not None:
        if not isinstance(cm, dict):
            out.append("contrast_mechanism: must be an object {common_belief, contrarian_reality} or null")
        else:
            _object(cm, "contrast_mechanism", ("common_belief", "contrarian_reality"), out)
    if "personalizations" in fields:
        p = fields["personalizations"]
        if not (isinstance(p, builtins.list) and len(p) == PERSONALIZATIONS and all(_text(x) for x in p)):
            out.append(f"personalizations: must be a list of exactly {PERSONALIZATIONS} non-empty strings")
    out.extend(f"{k}: unknown field" for k in fields if k not in FIELDS)
    return out


# --- reading ------------------------------------------------------------------

def _watchlist_id(store: Store, name: str) -> int:
    return watchlists.row(store, name)["id"]


def _sources(store: Store, ids: list[int]) -> list[dict]:
    out = []
    for vid in ids:
        r = store.one("SELECT id, external_id, title, url FROM video WHERE id = ?", (vid,))
        out.append(r if r is not None else {"id": vid, "external_id": None, "title": None, "url": None})
    return out


def _idea(store: Store, row: dict) -> Idea:
    return Idea(id=row["id"], watchlist=row["watchlist"], title=row["title"], status=row["status"],
                fields=json.loads(row["fields"] or "{}"),
                sources=_sources(store, json.loads(row["source_video_ids"] or "[]")),
                notes=json.loads(row["notes"] or "[]"), brief_path=row["brief_path"],
                created_at=row["created_at"], updated_at=row["updated_at"], videos=_videos(store, row["id"]),
                brief_owner=row["brief_owner"])


def _videos(store: Store, idea_id: int) -> builtins.list[dict]:
    return [{"slug": r["video_slug"], "owner": r["owner"]} for r in store.query(
        "SELECT video_slug, owner FROM idea_video WHERE idea_id = ? ORDER BY linked_at, rowid", (idea_id,))]


def mine(owner: str | None) -> bool:
    """True when a row of ``owner`` belongs to the person on this Mac. ``''``/None only exists in a store that
    was never merged (``db merge`` writes every owner) and means that store's single person (ADR 0014)."""
    return owner in (None, "", person())


def link_video(store: Store, idea_id: int, slug: str, *, owner: str | None = None) -> Idea:
    """Record that the Video ``slug`` of ``owner`` (default: this Mac's person) was made from Idea ``idea_id``
    (idempotent)."""
    get(store, idea_id)
    with store.transaction() as c:
        c.execute("INSERT OR IGNORE INTO idea_video (idea_id, owner, video_slug, linked_at) VALUES (?, ?, ?, ?)",
                  (int(idea_id), person() if owner is None else owner, slug, now_iso()))
    return get(store, idea_id)


_SELECT = "SELECT i.*, w.name AS watchlist FROM idea i JOIN watchlist w ON w.id = i.watchlist_id"


def get(store: Store, idea_id: int) -> Idea:
    row = store.one(_SELECT + " WHERE i.id = ?", (int(idea_id),))
    if row is None:
        raise IdeaError(f"no Idea {idea_id}")
    return _idea(store, row)


def list(store: Store, watchlist: str, status: str | None = None) -> list[Idea]:  # noqa: A001 (spec name)
    """Ideas of a Watchlist, oldest first; only those in ``status`` when given."""
    wid = _watchlist_id(store, watchlist)
    if status is not None and status not in STATUSES:
        raise IdeaError(f"status must be one of {', '.join(STATUSES)}, got {status!r}")
    sql, params = _SELECT + " WHERE i.watchlist_id = ?", [wid]
    if status is not None:
        sql += " AND i.status = ?"
        params.append(status)
    return [_idea(store, r) for r in store.query(sql + " ORDER BY i.id", tuple(params))]


# --- writing ------------------------------------------------------------------

def _resolve_source(store: Store, ref: int | str) -> int:
    try:
        return card.video(store, ref)["id"]
    except card.CardError as exc:
        raise IdeaError(f"source Reference {ref!r}: {exc}") from exc


def check(store: Store, source_video_ids: Iterable[int | str], fields: dict) -> list[str]:
    """Every reason ``add`` would refuse these sources and fields, one line each; empty when it would not."""
    refs = source_video_ids if isinstance(source_video_ids, (builtins.list, tuple)) else None
    out: list[str] = []
    if source_video_ids is None:
        out.append("sources: missing (a list of Reference: store id, YouTube id or URL)")
    elif refs is None:
        out.append("sources: must be a list of Reference (store id, YouTube id or URL)")
    elif not refs:
        out.append("sources: an Idea needs at least one source Reference")
    for ref in refs or ():
        try:
            _resolve_source(store, ref)
        except IdeaError as exc:
            out.append(f"sources: {exc}")
    return out + validate(fields, store)


def add(store: Store, watchlist: str, source_video_ids: Iterable[int | str], fields: dict) -> Idea:
    """A new inbox Idea of ``watchlist`` from its source Reference (store ids, YouTube ids or URLs).

    Refuses (nothing written) when a source is not in the store or a field breaks a rule;
    ``IdeaError.violations`` lists every reason (see ``check``)."""
    wid = _watchlist_id(store, watchlist)
    refs = builtins.list(source_video_ids)
    problems = check(store, refs, fields)
    if problems:
        raise IdeaError(f"Idea breaks {len(problems)} rule(s): {problems[0]}", problems)
    ids = builtins.list(dict.fromkeys(_resolve_source(store, r) for r in refs))
    data = {k: (v.strip() if isinstance(v, str) else v) for k, v in fields.items()}
    title = data.pop("title")
    sf = data["storytelling_format"]
    data["storytelling_format"] = {k: v.strip() for k, v in sf.items()}
    if data.get("contrast_mechanism"):
        data["contrast_mechanism"] = {k: v.strip() for k, v in data["contrast_mechanism"].items()}
    data["personalizations"] = [p.strip() for p in data["personalizations"]]
    now = now_iso()
    with store.transaction() as c:
        new_id = c.execute(
            "INSERT INTO idea (watchlist_id, source_video_ids, title, fields, status, notes, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 'inbox', '[]', ?, ?)",
            (wid, dumps(ids), title, dumps(data), now, now)).lastrowid
    return get(store, new_id)


def _move(store: Store, idea_id: int, action: str, **columns: Any) -> Idea:
    need, to = TRANSITIONS[action]
    current = get(store, idea_id)
    if current.status != need:
        hint = f"; its Brief is {current.brief_path}" if current.brief_path else ""
        raise IdeaError(f"Idea {current.id} is {current.status}; {action} needs an Idea that is {need}{hint}")
    sets = ", ".join(f"{k} = ?" for k in ("status", "updated_at", *columns))
    with store.transaction() as c:
        c.execute(f"UPDATE idea SET {sets} WHERE id = ? AND status = ?",
                  (to, now_iso(), *columns.values(), current.id, need))
    return get(store, current.id)


def shortlist(store: Store, idea_id: int) -> Idea:
    """inbox → shortlisted."""
    return _move(store, idea_id, "shortlist")


def discard(store: Store, idea_id: int) -> Idea:
    """inbox → discarded."""
    return _move(store, idea_id, "discard")


def restore(store: Store, idea_id: int) -> Idea:
    """discarded → inbox (Sandcastles: Shortlist after Discard brings it back to triage)."""
    return _move(store, idea_id, "restore")


def mark_brief(store: Store, idea_id: int, brief_path: str, *, owner: str | None = None) -> Idea:
    """shortlisted → brief with the Brief's path and its owner (default: this Mac's person). Called by
    ``brief.create`` once the file is written."""
    return _move(store, idea_id, "brief", brief_path=str(brief_path),
                 brief_owner=person() if owner is None else owner)


def note(store: Store, idea_id: int, text: str) -> Idea:
    """Append an Author's note ``{at, text}``; any status."""
    if not _text(text):
        raise IdeaError("a note needs text")
    current = get(store, idea_id)
    notes = current.notes + [{"at": now_iso(), "text": text.strip()}]
    with store.transaction() as c:
        c.execute("UPDATE idea SET notes = ?, updated_at = ? WHERE id = ?", (dumps(notes), now_iso(), current.id))
    return get(store, current.id)


# --- input for suggest-ideas ----------------------------------------------------

DEFAULT_CANDIDATE_DAYS = 30
DEFAULT_CANDIDATE_LIMIT = 10


def used_sources(store: Store) -> set[int]:
    """Store video ids that are a source of any Idea, in any status and any Watchlist."""
    rows = store.query("SELECT DISTINCT j.value AS vid FROM idea, json_each(idea.source_video_ids) AS j")
    return {int(r["vid"]) for r in rows}


def candidates(store: Store, watchlist: str, days: float = DEFAULT_CANDIDATE_DAYS,
               min_outlier: float | None = None, limit: int | None = DEFAULT_CANDIDATE_LIMIT,
               *, now: datetime | None = None) -> list[feed.FeedRow]:
    """The Watchlist's analyzed Reference of the last ``days`` that no Idea uses yet, best outlier first.

    "Analyzed" means the card has its analysis section (``card save`` ran); measured-only
    and uncarded Reference are left out, as are Reference already a source of any Idea."""
    rows = feed.feed(store, watchlist, lookback_days=days, min_outlier=min_outlier, limit=None, now=now)
    used = used_sources(store)
    analyzed = {r["external_id"] for r in store.query(
        "SELECT v.external_id FROM card JOIN video v ON v.id = card.video_id "
        "WHERE card.analysis IS NOT NULL AND v.id NOT IN (SELECT value FROM json_each(?))",
        (dumps(sorted(used)),))}
    out = [r for r in rows if r.external_id in analyzed]
    return out[:limit] if limit is not None else out
