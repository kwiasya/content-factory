"""Watchlists and their Reference channels and search queries.

A Reference channel is added by handle or URL: ``parse_channel_ref`` turns what
the Author pasted into a handle, channel id or legacy username; a channel the
store already knows is reused, otherwise ``channels.list`` is called through
``youtube`` (quota-charged) and its payload ingested by ``ingest``.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from urllib.parse import unquote, urlsplit

from cf.research import formats, ingest, youtube
from cf.research.store import Store, dumps, now_iso


class WatchlistError(Exception):
    """A Watchlist request that cannot be carried out; the message says why."""


@dataclass(frozen=True)
class ChannelRef:
    """What the Author pointed at: ``kind`` is ``handle`` (``@name``, lowercase),
    ``id`` (``UC…``), ``username`` (legacy ``/user/`` URLs) or ``custom`` (legacy
    ``/c/`` URLs, resolved as a handle first, then as a username)."""
    kind: str
    value: str


CHANNEL_ID_RE = re.compile(r"^UC[\w-]{22}$")
HANDLE_RE = re.compile(r"^[\w.-]{3,100}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com"}
VIDEO_PATHS = {"watch", "shorts", "live", "embed", "v"}
NOT_CHANNEL_PATHS = {"playlist", "results", "feed", "hashtag", "post", "channel", "user", "c"}


def _handle(name: str, text: str) -> ChannelRef:
    name = unquote(name).lstrip("@")
    if not HANDLE_RE.match(name):
        raise WatchlistError(f"not a channel handle: {text!r} (expected @name, a channel URL or a UC… id)")
    return ChannelRef("handle", "@" + name.lower())


def parse_channel_ref(text: str) -> ChannelRef:
    """Turn a handle, channel id or YouTube channel URL into a ``ChannelRef``."""
    t = (text or "").strip()
    if not t:
        raise WatchlistError("empty channel reference")
    if CHANNEL_ID_RE.match(t):
        return ChannelRef("id", t)
    looks_like_url = "/" in t or "://" in t
    if not looks_like_url:
        return _handle(t, text)
    parts = urlsplit(t if "://" in t else "https://" + t)
    host = (parts.hostname or "").lower()
    if host in {"youtu.be", "www.youtu.be"}:
        raise WatchlistError(f"{text!r} is a video link, not a channel; paste the channel URL or @handle")
    if host not in YOUTUBE_HOSTS:
        raise WatchlistError(f"{text!r} is not a YouTube link")
    segs = [s for s in parts.path.split("/") if s]
    if not segs:
        raise WatchlistError(f"{text!r} has no channel in it")
    head = segs[0]
    if head.startswith("@"):
        return _handle(head, text)
    if head in VIDEO_PATHS:
        raise WatchlistError(f"{text!r} is a video link, not a channel; paste the channel URL or @handle")
    if head == "playlist":
        raise WatchlistError(f"{text!r} is a playlist link, not a channel")
    if head == "channel" and len(segs) > 1 and CHANNEL_ID_RE.match(segs[1]):
        return ChannelRef("id", segs[1])
    if head == "user" and len(segs) > 1:
        return ChannelRef("username", unquote(segs[1]))
    if head == "c" and len(segs) > 1:
        name = unquote(segs[1])
        _handle(name, text)  # same character rules
        return ChannelRef("custom", name)
    if head in NOT_CHANNEL_PATHS:
        raise WatchlistError(f"{text!r} has no channel in it")
    return _handle(head, text)  # legacy vanity URL youtube.com/<name>


# --- Watchlists ------------------------------------------------------------

NAME_RE = re.compile(r"^[\w][\w.-]*$")


@dataclass(frozen=True)
class Watchlist:
    name: str
    format_id: str
    channel_id: str | None
    language: str
    region: str | None
    queries: list[str]
    channel_count: int
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Channel:
    """A Reference channel as the store holds it."""
    external_id: str
    handle: str | None
    title: str | None
    subscriber_count: int | None
    video_count: int | None
    view_count: int | None
    uploads_playlist_id: str | None
    own: bool
    platform: str = "youtube"
    country: str | None = None
    fetched_at: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


_CHANNEL_COLS = ("external_id, handle, title, subscriber_count, video_count, view_count, "
                 "uploads_playlist_id, own, platform, country, fetched_at")


def _channel(row: dict) -> Channel:
    return Channel(**{**row, "own": bool(row["own"])})


def _row(store: Store, name: str) -> dict:
    row = store.one("SELECT * FROM watchlist WHERE name = ?", (name,))
    if row is None:
        raise WatchlistError(f"no Watchlist named {name!r}")
    return row


def _watchlist(store: Store, row: dict) -> Watchlist:
    n = store.one("SELECT COUNT(*) AS n FROM watchlist_channel WHERE watchlist_id = ?", (row["id"],))["n"]
    return Watchlist(row["name"], row["format_id"], row["channel_id"], row["language"], row["region"],
                     json.loads(row["queries"]), int(n), row["created_at"])


def create(store: Store, name: str, *, format_id: str, channel_id: str | None = None,
           language: str = "en", region: str | None = None,
           queries: list[str] | None = None) -> Watchlist:
    """Create a Watchlist. ``name`` doubles as a folder name under ``references/``."""
    if not name or not NAME_RE.match(name):
        raise WatchlistError(f"Watchlist name {name!r}: use letters, digits, '-', '_' or '.', "
                             f"no spaces or slashes, not starting with '.'")
    if not (format_id or "").strip():
        raise WatchlistError("a Watchlist needs a Format id (e.g. walk-reel, tech-explainer)")
    why = formats.problem(format_id.strip())
    if why:
        raise WatchlistError(why)
    qs: list[str] = []
    for q in queries or []:
        q = " ".join(q.split())
        if q and q not in qs:
            qs.append(q)
    try:
        with store.transaction() as c:
            c.execute("INSERT INTO watchlist (name, format_id, channel_id, language, region, queries, created_at) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (name, format_id.strip(), channel_id or None, language or "en", region or None,
                       dumps(qs), now_iso()))
    except sqlite3.IntegrityError as exc:
        raise WatchlistError(f"Watchlist {name!r} already exists") from exc
    return get(store, name)


def get(store: Store, name: str) -> Watchlist:
    return _watchlist(store, _row(store, name))


def list_watchlists(store: Store) -> list[Watchlist]:
    return [_watchlist(store, r) for r in store.query("SELECT * FROM watchlist ORDER BY name")]


def remove(store: Store, name: str) -> None:
    """Delete the Watchlist and its memberships; channels and their videos stay in the store."""
    wid = _row(store, name)["id"]
    with store.transaction() as c:
        c.execute("DELETE FROM watchlist WHERE id = ?", (wid,))


def add_query(store: Store, name: str, query: str) -> Watchlist:
    """Attach a search query (whitespace collapsed; a query already there is not repeated)."""
    q = " ".join((query or "").split())
    if not q:
        raise WatchlistError("empty search query")
    row = _row(store, name)
    qs = json.loads(row["queries"])
    if q not in qs:
        qs.append(q)
        with store.transaction() as c:
            c.execute("UPDATE watchlist SET queries = ? WHERE id = ?", (dumps(qs), row["id"]))
    return get(store, name)


# --- Reference channels ----------------------------------------------------

def channels(store: Store, name: str) -> list[Channel]:
    """Reference channels of a Watchlist in the order they were added."""
    wid = _row(store, name)["id"]
    rows = store.query(
        f"SELECT {', '.join('c.' + k.strip() for k in _CHANNEL_COLS.split(','))} FROM channel c "
        "JOIN watchlist_channel wc ON wc.channel_id = c.id WHERE wc.watchlist_id = ? "
        "ORDER BY wc.added_at, c.id", (wid,))
    return [_channel(r) for r in rows]


def find_channel(store: Store, ref: ChannelRef) -> tuple[int, Channel] | None:
    """The stored channel a reference points at (handle or id), or None. Usernames are never stored."""
    if ref.kind == "id":
        where, value = "external_id = ?", ref.value
    elif ref.kind in ("handle", "custom"):
        where, value = "handle = ?", _handle(ref.value, ref.value).value
    else:
        return None
    row = store.one(f"SELECT id, {_CHANNEL_COLS} FROM channel WHERE platform = 'youtube' AND {where}", (value,))
    if row is None:
        return None
    cid = row.pop("id")
    return cid, _channel(row)


def add_channel(store: Store, name: str, ref: str, *, own: bool = False, refresh: bool = False,
                transport: youtube.Transport | None = None) -> Channel:
    """Add a Reference channel to a Watchlist by handle, channel id or URL.

    A channel the store already knows is reused without an API call unless
    ``refresh``; otherwise ``channels.list`` is called (1 quota unit) and ingested.
    ``own`` marks the channel as the Author's. Adding twice is harmless.
    """
    wid = _row(store, name)["id"]
    parsed = parse_channel_ref(ref)
    found = None if refresh else find_channel(store, parsed)
    if found is None:
        if parsed.kind == "id":
            attempts = [{"ids": [parsed.value]}]
        elif parsed.kind == "handle":
            attempts = [{"handle": parsed.value}]
        elif parsed.kind == "username":
            attempts = [{"username": parsed.value}]
        else:  # custom URLs mostly became handles of the same name; older ones are usernames
            attempts = [{"handle": _handle(parsed.value, ref).value}, {"username": parsed.value}]
        ids: list[int] = []
        for kw in attempts:
            payload = youtube.channels_list(store, transport=transport, **kw)
            ids = ingest.ingest_channels(store, payload, own=True if own else None)
            if ids:
                break
        if not ids:
            raise WatchlistError(f"no YouTube channel for {parsed.value!r} ({ref!r})")
        cid = ids[0]
    else:
        cid = found[0]
    with store.transaction() as c:
        if own:
            c.execute("UPDATE channel SET own = 1 WHERE id = ?", (cid,))
        c.execute("INSERT OR IGNORE INTO watchlist_channel (watchlist_id, channel_id, added_at) VALUES (?, ?, ?)",
                  (wid, cid, now_iso()))
    row = store.one(f"SELECT {_CHANNEL_COLS} FROM channel WHERE id = ?", (cid,))
    return _channel(row)


def remove_channel(store: Store, name: str, ref: str) -> Channel:
    """Take a Reference channel out of a Watchlist (no API call); the channel stays in the store."""
    wid = _row(store, name)["id"]
    parsed = parse_channel_ref(ref)
    found = find_channel(store, parsed)
    if found is not None:
        with store.transaction() as c:
            cur = c.execute("DELETE FROM watchlist_channel WHERE watchlist_id = ? AND channel_id = ?",
                            (wid, found[0]))
            if cur.rowcount:
                return found[1]
    raise WatchlistError(f"{ref!r} is not in Watchlist {name!r}")
