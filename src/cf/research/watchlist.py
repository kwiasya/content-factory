"""Watchlists and their Reference channels and search queries.

A Reference channel is added by handle or URL: ``parse_channel_ref`` turns what
the Author pasted into a handle, channel id or legacy username; a channel the
store already knows is reused, otherwise ``channels.list`` is called through
``youtube`` (quota-charged) and its payload ingested by ``ingest``.

A Watchlist holds channels of both Platforms. An Instagram account is given as
``ig:<username>`` or an ``instagram.com/<username>`` link and resolved through
Business Discovery (``instagram``, one call of the hourly bucket), which sees
public business and creator accounts only (ADR 0007). Search queries are
YouTube's: Instagram has no search API.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import asdict, dataclass
from urllib.parse import unquote

from cf.research import env, formats, ingest, instagram, youtube
from cf.research.store import Store, dumps, now_iso


class WatchlistError(Exception):
    """A Watchlist request that cannot be carried out; the message says why."""


@dataclass(frozen=True)
class ChannelRef:
    """What the Author pointed at: ``kind`` is ``handle`` (``@name``, lowercase),
    ``id`` (``UC…``), ``username`` (legacy ``/user/`` URLs) or ``custom`` (legacy
    ``/c/`` URLs, resolved as a handle first, then as a username). ``platform`` is
    ``instagram`` for an Instagram account (kind ``handle``, ``@username`` lowercase)."""
    kind: str
    value: str
    platform: str = "youtube"


# patterns are used with fullmatch: ``$`` would let a trailing newline in
CHANNEL_ID_RE = re.compile(r"UC[\w-]{22}")
HANDLE_RE = re.compile(r"[\w.-]{3,100}")
IG_HANDLE_RE = re.compile(r"[A-Za-z0-9._]{1,30}")
IG_PREFIXES = ("ig:", "instagram:")
IG_NOT_ACCOUNT_PATHS = {"explore", "stories", "accounts", "direct", "about", "legal", "developer"}
VIDEO_PATHS = {"watch", "shorts", "live", "embed", "v"}
NOT_CHANNEL_PATHS = {"playlist", "results", "feed", "hashtag", "post", "channel", "user", "c"}


def _handle(name: str, text: str) -> ChannelRef:
    name = unquote(name).strip().lstrip("@")
    if not HANDLE_RE.fullmatch(name):
        raise WatchlistError(f"not a channel handle: {text!r} (expected @name, a channel URL or a UC… id)")
    return ChannelRef("handle", "@" + name.lower())


def _ig_handle(name: str, text: str) -> ChannelRef:
    name = unquote(name).strip().lstrip("@")
    if not IG_HANDLE_RE.fullmatch(name):
        raise WatchlistError(f"not an Instagram username: {text!r} (expected ig:<username> or instagram.com/<username>)")
    return ChannelRef("handle", "@" + name.lower(), "instagram")


def parse_instagram_ref(text: str) -> ChannelRef | None:
    """``ig:<username>``, ``instagram:<username>`` or an ``instagram.com/<username>[/reels]`` link as an
    Instagram ``ChannelRef``; None when ``text`` is neither; WatchlistError for a media or other link."""
    t = (text or "").strip()
    for prefix in IG_PREFIXES:
        if t.lower().startswith(prefix):
            return _ig_handle(t[len(prefix):], text)
    segs = ingest.instagram_segments(t) if ("/" in t or "instagram.com" in t.lower()) else None
    if segs is None:
        return None
    if not segs:
        raise WatchlistError(f"{text!r} has no Instagram account in it")
    if segs[0] in ingest.IG_MEDIA_PATHS or ingest.instagram_shortcode(t):
        raise WatchlistError(f"{text!r} is a reel or post link, not an account; add it with "
                             f"`watchlist add-reference`")
    if segs[0] in IG_NOT_ACCOUNT_PATHS:
        raise WatchlistError(f"{text!r} has no Instagram account in it")
    return _ig_handle(segs[0], text)


def parse_channel_ref(text: str) -> ChannelRef:
    """Turn a handle, channel id or YouTube channel URL, or an Instagram account (``ig:<username>``,
    ``instagram.com/<username>``), into a ``ChannelRef``."""
    t = (text or "").strip()
    if not t:
        raise WatchlistError("empty channel reference")
    ig = parse_instagram_ref(t)
    if ig is not None:
        return ig
    if CHANNEL_ID_RE.fullmatch(t):
        return ChannelRef("id", t)
    looks_like_url = "/" in t or "://" in t
    if not looks_like_url:
        return _handle(t, text)
    link = ingest.youtube_link(t)
    if link is None:
        raise WatchlistError(f"{text!r} is not a YouTube link")
    if link.short_link:
        raise WatchlistError(f"{text!r} is a video link, not a channel; paste the channel URL or @handle")
    segs = link.segments
    if not segs:
        raise WatchlistError(f"{text!r} has no channel in it")
    head = segs[0]
    if head.startswith("@"):
        return _handle(head, text)
    if head in VIDEO_PATHS:
        raise WatchlistError(f"{text!r} is a video link, not a channel; paste the channel URL or @handle")
    if head == "playlist":
        raise WatchlistError(f"{text!r} is a playlist link, not a channel")
    if head == "channel" and len(segs) > 1 and CHANNEL_ID_RE.fullmatch(unquote(segs[1]).strip()):
        return ChannelRef("id", unquote(segs[1]).strip())
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

NAME_RE = re.compile(r"[\w][\w.-]*")


@dataclass(frozen=True)
class Watchlist:
    name: str
    format_id: str
    author_channel: str | None  # the Author's Channel this Watchlist serves (a folder name, not a YouTube id)
    language: str
    region: str | None
    queries: list[str]
    channel_count: int
    created_at: str

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ReferenceChannel:
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


def _channel(r: dict) -> ReferenceChannel:
    return ReferenceChannel(**{**r, "own": bool(r["own"])})


def row(store: Store, name: str) -> dict:
    """The store row of Watchlist ``name`` (``id``, ``name``, ``format_id``, ``author_channel``, …);
    WatchlistError naming it when there is none."""
    found = store.one("SELECT * FROM watchlist WHERE name = ?", (name,))
    if found is None:
        raise WatchlistError(f"no Watchlist named {name!r}")
    return found


def _watchlist(store: Store, r: dict) -> Watchlist:
    n = store.one("SELECT COUNT(*) AS n FROM watchlist_channel WHERE watchlist_id = ?", (r["id"],))["n"]
    return Watchlist(r["name"], r["format_id"], r["author_channel"], r["language"], r["region"],
                     json.loads(r["queries"]), int(n), r["created_at"])


def create(store: Store, name: str, *, format_id: str, author_channel: str | None = None,
           language: str = "en", region: str | None = None,
           queries: list[str] | None = None) -> Watchlist:
    """Create a Watchlist. ``name`` doubles as a folder name under ``references/`` (names
    starting with ``_`` are reserved for folders like ``_adhoc``);
    ``author_channel`` names the Author's Channel it serves (Brief folder)."""
    if name and name.startswith("_"):
        raise WatchlistError(f"Watchlist name {name!r}: names starting with '_' are reserved "
                             f"(references/_adhoc holds References fetched without a Watchlist)")
    if not name or not NAME_RE.fullmatch(name):
        raise WatchlistError(f"Watchlist name {name!r}: use letters, digits, '-', '_' or '.', "
                             f"no spaces or slashes, not starting with '.' or '_'")
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
            c.execute("INSERT INTO watchlist (name, format_id, author_channel, language, region, queries, created_at) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?)",
                      (name, format_id.strip(), author_channel or None, language or "en", region or None,
                       dumps(qs), now_iso()))
    except sqlite3.IntegrityError as exc:
        raise WatchlistError(f"Watchlist {name!r} already exists") from exc
    return get(store, name)


def get(store: Store, name: str) -> Watchlist:
    return _watchlist(store, row(store, name))


def list_watchlists(store: Store) -> list[Watchlist]:
    return [_watchlist(store, r) for r in store.query("SELECT * FROM watchlist ORDER BY name")]


def remove(store: Store, name: str, *, force: bool = False) -> None:
    """Delete the Watchlist with its memberships, search hits and Ideas (Brief files on disk stay);
    channels and their videos stay in the store.

    Refuses while one of its Ideas has a Brief, unless ``force``."""
    wid = row(store, name)["id"]
    briefed = store.query("SELECT id, brief_path FROM idea WHERE watchlist_id = ? AND status = 'brief' "
                          "ORDER BY id", (wid,))
    if briefed and not force:
        ids = ", ".join(str(r["id"]) for r in briefed)
        raise WatchlistError(f"Watchlist {name!r} has {len(briefed)} Idea(s) with a Brief ({ids}); removing it "
                             f"deletes its Ideas (the Brief files stay). Pass --force to remove it anyway")
    with store.transaction() as c:
        c.execute("DELETE FROM watchlist WHERE id = ?", (wid,))


def add_query(store: Store, name: str, query: str) -> Watchlist:
    """Attach a search query (whitespace collapsed; a query already there is not repeated)."""
    q = " ".join((query or "").split())
    if not q:
        raise WatchlistError("empty search query")
    w = row(store, name)
    qs = json.loads(w["queries"])
    if q not in qs:
        qs.append(q)
        with store.transaction() as c:
            c.execute("UPDATE watchlist SET queries = ? WHERE id = ?", (dumps(qs), w["id"]))
    return get(store, name)


# --- Reference channels ----------------------------------------------------

def channels(store: Store, name: str) -> list[ReferenceChannel]:
    """Reference channels of a Watchlist in the order they were added."""
    wid = row(store, name)["id"]
    rows = store.query(
        f"SELECT {', '.join('c.' + k.strip() for k in _CHANNEL_COLS.split(','))} FROM channel c "
        "JOIN watchlist_channel wc ON wc.channel_id = c.id WHERE wc.watchlist_id = ? "
        "ORDER BY wc.added_at, c.id", (wid,))
    return [_channel(r) for r in rows]


def find_channel(store: Store, ref: ChannelRef) -> tuple[int, ReferenceChannel] | None:
    """The stored channel a reference points at (handle or id), or None. Usernames are never stored."""
    if ref.kind == "id":
        where, value = "external_id = ?", ref.value
    elif ref.platform == "instagram":
        where, value = "handle = ?", ref.value
    elif ref.kind in ("handle", "custom"):
        where, value = "handle = ?", _handle(ref.value, ref.value).value
    else:
        return None
    found = store.one(f"SELECT id, {_CHANNEL_COLS} FROM channel WHERE platform = ? AND {where}",
                      (ref.platform, value))
    if found is None:
        return None
    cid = found.pop("id")
    return cid, _channel(found)


def resolve_instagram(store: Store, username: str, *, own: bool | None = None, media_limit: int = 0,
                      transport: instagram.Transport | None = None) -> tuple[int, dict]:
    """Business Discovery of ``@username``: ingest the account (and, with ``media_limit``, its newest
    reels with a snapshot each); return its store id and the payload's ``business_discovery`` object."""
    user_id = env.ig_user_id()
    if not user_id:
        raise instagram.InstagramError(env.IG_HELP)
    handle = username.lstrip("@")
    try:
        p = instagram.business_discovery(store, user_id, handle, media_limit=media_limit, transport=transport)
    except instagram.InstagramError as exc:
        if exc.subcode in instagram.NOT_FOUND_SUBCODES or exc.code == 110:
            raise WatchlistError(f"@{handle}: Business Discovery found no public business or creator account "
                                 f"(a personal or private account is invisible to the API; ADR 0007)") from None
        raise
    bd = p.get("business_discovery") or {}
    if not bd.get("id"):
        raise WatchlistError(f"@{handle}: Business Discovery answered without an account")
    cid = ingest.ingest_ig_account(store, bd, own=own)
    items = (bd.get("media") or {}).get("data") or []
    if items:
        ingest.ingest_ig_media(store, cid, items)
    return cid, bd


def add_channel(store: Store, name: str, ref: str, *, own: bool = False, refresh: bool = False,
                transport: youtube.Transport | None = None,
                ig_transport: instagram.Transport | None = None) -> ReferenceChannel:
    """Add a Reference channel to a Watchlist by handle, channel id or URL, or an Instagram account.

    A channel the store already knows is reused without an API call unless
    ``refresh``; otherwise ``channels.list`` is called (1 quota unit) and ingested,
    or for Instagram Business Discovery (1 call of the hourly bucket; followers
    and media count, no media yet: ``scout`` reads those).
    ``own`` marks the channel as the Author's. Adding twice is harmless.
    """
    wid = row(store, name)["id"]
    parsed = parse_channel_ref(ref)
    found = None if refresh else find_channel(store, parsed)
    if found is None and parsed.platform == "instagram":
        cid = resolve_instagram(store, parsed.value, own=True if own else None, transport=ig_transport)[0]
    elif found is None:
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
    else:  # a channel the store already has
        cid = found[0]
    with store.transaction() as c:
        if own:
            c.execute("UPDATE channel SET own = 1 WHERE id = ?", (cid,))
        c.execute("INSERT OR IGNORE INTO watchlist_channel (watchlist_id, channel_id, added_at) VALUES (?, ?, ?)",
                  (wid, cid, now_iso()))
    return _channel(store.one(f"SELECT {_CHANNEL_COLS} FROM channel WHERE id = ?", (cid,)))


def remove_channel(store: Store, name: str, ref: str) -> ReferenceChannel:
    """Take a Reference channel out of a Watchlist (no API call); the channel stays in the store."""
    wid = row(store, name)["id"]
    parsed = parse_channel_ref(ref)
    found = find_channel(store, parsed)
    if found is not None:
        with store.transaction() as c:
            cur = c.execute("DELETE FROM watchlist_channel WHERE watchlist_id = ? AND channel_id = ?",
                            (wid, found[0]))
            if cur.rowcount:
                return found[1]
    raise WatchlistError(f"{ref!r} is not in Watchlist {name!r}")
