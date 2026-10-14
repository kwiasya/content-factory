"""References the Author picks by hand into a Watchlist: an Instagram reel or post link, with her Note.

Business Discovery cannot look a reel up by its shortcode, so ``add_reference``
finds the owner in this order (ADR 0010):

1. the store already has the shortcode (a scout or snapshot of a Watchlist
   account read it, or an earlier pick): ``status`` ``store``;
2. yt-dlp metadata only (no download, no cookies, no login) names the owner;
   the owner is resolved through Business Discovery with one page of media,
   which brings the reel's counts and the owner's baseline for the Outlier
   score: ``ytdlp``. A reel older than that page is looked for on up to
   ``DEEPER_PAGES`` more pages, down to its publish date; if it is still not
   there, or the owner is a personal account, the yt-dlp counts are kept;
3. neither: the pick is kept unresolved (link, Note, no owner, no counts).

``YtDlpResolver`` spaces yt-dlp calls (``DELAY_S``) and stops asking once
Instagram refused ``MAX_REFUSALS`` times in a row; later picks of the run go
straight to steps 1 and 3. Tracking parameters (``igsh``, ``stkn``…) are
dropped: the stored link is the canonical one. The Note is stored verbatim as a
``card`` Note keyed by the shortcode (``notes``), once.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Callable

from cf.research import ingest, instagram, notes
from cf.research import watchlist as watchlists
from cf.research.fetch import FetchError
from cf.research.store import Store, StoreError, dumps, now_iso
from cf.research.watchlist import WatchlistError

DELAY_S = 4.0
MAX_REFUSALS = 2
DEEPER_PAGES = 3


@dataclass(frozen=True)
class Pick:
    """One picked Reference as ``add_reference`` left it."""
    shortcode: str
    url: str
    status: str  # store | ytdlp | unresolved
    owner: str | None  # @username, when known
    video: int  # store id
    title: str | None
    note: int | None = None  # the Note id (new or the same text already there)
    detail: str | None = None  # why the owner is unknown, or why Graph data is missing

    def to_dict(self) -> dict:
        return asdict(self)


class YtDlpResolver:
    """yt-dlp metadata of Instagram links, politely: ``delay_s`` between calls, no more calls once
    Instagram refused ``max_refusals`` times in a row. ``extract(url) -> info`` raises ``FetchError``."""

    def __init__(self, extract: Callable[[str], dict] | None = None, *, delay_s: float = DELAY_S,
                 max_refusals: int = MAX_REFUSALS, sleep: Callable[[float], None] = time.sleep,
                 clock: Callable[[], float] = time.monotonic):
        if extract is None:
            from cf.research import ytdlp
            extract = ytdlp.metadata
        self.extract, self.delay_s, self.max_refusals = extract, delay_s, max_refusals
        self.sleep, self.clock = sleep, clock
        self.refusals, self.calls, self.stopped = 0, 0, None
        self._last: float | None = None

    def info(self, url: str) -> tuple[dict | None, str | None]:
        """``(info, None)``, or ``(None, why)`` when yt-dlp failed or is no longer asked."""
        if self.stopped:
            return None, self.stopped
        if self._last is not None:
            wait = self.delay_s - (self.clock() - self._last)
            if wait > 0:
                self.sleep(wait)
        self.calls += 1
        try:
            got = self.extract(url)
        except FetchError as exc:
            self.refusals += 1
            if self.refusals >= self.max_refusals:
                self.stopped = (f"yt-dlp not asked: Instagram refused {self.refusals} times in a row "
                                f"(last: {str(exc)[:160]})")
            return None, str(exc)[:300]
        finally:
            self._last = self.clock()
        self.refusals = 0
        return got, None


def owner_from_info(info: dict) -> str | None:
    """The owner's ``@username`` in a yt-dlp Instagram info dict (``channel``), or None."""
    name = str(info.get("channel") or "").strip().lstrip("@")
    return "@" + name.lower() if name and watchlists.IG_HANDLE_RE.fullmatch(name) else None


def _video(store: Store, code: str) -> dict | None:
    return store.one("SELECT v.id, v.title, v.channel_id, c.handle FROM video v LEFT JOIN channel c "
                     "ON c.id = v.channel_id WHERE v.platform = 'instagram' AND v.external_id = ?", (code,))


def _from_info(store: Store, code: str, url: str, info: dict, owner: str | None, channel_id: int | None,
               reel: bool, ts: str) -> int:
    """A video row (and a snapshot) from yt-dlp metadata, for a reel the Graph API did not give."""
    caption = info.get("description")
    stamp = info.get("timestamp")
    row = {"platform": "instagram", "external_id": code, "title": ingest.first_line(caption) or info.get("title"),
           "description": caption, "url": url, "kind": "short" if reel else None,
           "published_at": now_iso(datetime.fromtimestamp(int(stamp), timezone.utc)) if stamp else None,
           "duration_s": float(info["duration"]) if info.get("duration") else None,
           "tags": dumps(ingest.HASHTAG_RE.findall(caption or "")),
           "raw": dumps({"source": "yt-dlp", "owner": owner, "uploader_id": info.get("uploader_id")}),
           "fetched_at": ts}
    with store.transaction() as c:
        own = 0 if channel_id is None else int(c.execute("SELECT own FROM channel WHERE id = ?",
                                                          (channel_id,)).fetchone()[0])
        vid = ingest.upsert_video(c, row, channel_id, own)
        views, likes, comments = (ingest._int(info.get(k)) for k in ("view_count", "like_count", "comment_count"))
        if any(x is not None for x in (views, likes, comments)):
            c.execute("INSERT OR REPLACE INTO snapshot (video_id, taken_at, views, likes, comments) "
                      "VALUES (?, ?, ?, ?, ?)", (vid, ts, views, likes, comments))
    return vid


def deepen(store: Store, channel_id: int, code: str, published_at: str | None, *, after: str | None = None,
           pages: int = DEEPER_PAGES, transport: instagram.Transport | None = None) -> bool:
    """Page an Instagram account's media from ``after`` (None: the newest page), looking for ``code``;
    stop at ``published_at`` (when known), the end, or after ``pages`` pages. True when the reel came in."""
    from cf.research import env
    ch = store.one("SELECT handle FROM channel WHERE id = ?", (channel_id,))
    for _ in range(pages):
        p = instagram.business_discovery(store, env.ig_user_id(), ch["handle"], after=after, transport=transport)
        media = (p.get("business_discovery") or {}).get("media") or {}
        items = media.get("data") or []
        ingest.ingest_ig_media(store, channel_id, items)
        if any(ingest.instagram_shortcode(i.get("permalink") or "") == code for i in items):
            return True
        dates = [d for d in (ingest.ig_time(i.get("timestamp")) for i in items) if d]
        after = ((media.get("paging") or {}).get("cursors") or {}).get("after")
        if not after or len(items) < instagram.MEDIA_PAGE or (published_at and dates and min(dates) < published_at):
            return False
    return False


def _bare(store: Store, code: str, url: str, reel: bool, ts: str) -> int:
    """An unresolved pick: the link only (owner unknown, no counts)."""
    with store.transaction() as c:
        return ingest.upsert_video(c, {"platform": "instagram", "external_id": code, "url": url,
                                       "kind": "short" if reel else None, "fetched_at": ts}, None, 0)


def add_reference(store: Store, name: str, ref: str, *, note: str | None = None,
                  resolver: YtDlpResolver | None = None, ig_transport: instagram.Transport | None = None) -> Pick:
    """Pick an Instagram reel or post link into Watchlist ``name`` with the Author's ``note`` (verbatim)."""
    w = watchlists.row(store, name)
    code = ingest.instagram_shortcode(ref or "")
    if code is None:
        raise WatchlistError(f"{ref!r} is not an Instagram reel or post link (instagram.com/reel/<code>/ or /p/<code>/)")
    segs = ingest.instagram_segments(ref) or []
    reel = "p" not in segs
    url = ingest.instagram_url(code, "REELS" if reel else "FEED")
    ts = now_iso()
    status, detail = "store", None
    found = _video(store, code)
    if found is None or found["channel_id"] is None:
        info, why = (resolver or YtDlpResolver()).info(url)
        owner = owner_from_info(info) if info else None
        if owner:
            status = "ytdlp"
            known = store.one("SELECT id FROM channel WHERE platform = 'instagram' AND handle = ?", (owner,))
            cid = known["id"] if known else None
            start = None  # where paging deeper starts: past the page Business Discovery just gave
            if cid is None:
                try:
                    cid, bd = watchlists.resolve_instagram(store, owner, media_limit=instagram.MEDIA_PAGE,
                                                           transport=ig_transport)
                    media = bd.get("media") or {}
                    start = ((media.get("paging") or {}).get("cursors") or {}).get("after")
                    if len(media.get("data") or []) < instagram.MEDIA_PAGE:
                        start = "end"
                except (WatchlistError, instagram.InstagramError, StoreError) as exc:
                    detail = f"owner {owner} not on Business Discovery ({exc}); counts from yt-dlp"
            found = _video(store, code)
            if (found is None or found["channel_id"] is None) and cid is not None and detail is None:
                stamp = info.get("timestamp")
                when = now_iso(datetime.fromtimestamp(int(stamp), timezone.utc)) if stamp else None
                try:
                    if start != "end" and deepen(store, cid, code, when, after=start, transport=ig_transport):
                        found = _video(store, code)
                except (instagram.InstagramError, StoreError) as exc:
                    detail = f"paging {owner} deeper failed ({exc}); counts from yt-dlp"
            if found is None or found["channel_id"] is None:
                if cid is not None and detail is None:
                    detail = f"not in the owner's newest pages (up to {DEEPER_PAGES + 1}); counts from yt-dlp"
                _from_info(store, code, url, info, owner, cid, reel, ts)
        elif found is None:
            status = "unresolved"
            detail = why or "yt-dlp named no owner"
            _bare(store, code, url, reel, ts)
        else:
            status = "unresolved"
            detail = why or "yt-dlp named no owner"
    found = _video(store, code)
    with store.transaction() as c:
        c.execute("INSERT OR IGNORE INTO watchlist_pick (watchlist_id, video_id, added_at) VALUES (?, ?, ?)",
                  (w["id"], found["id"], ts))
    note_id = None
    if note and note.strip():
        same = [n for n in notes.list(store, kind="card", key=code, include_resolved=True) if n.text == note]
        note_id = same[0].id if same else notes.add(store, "card", code, note).id
    owner = found["handle"]
    if owner is None and status == "ytdlp":
        raw = store.one("SELECT raw FROM video WHERE id = ?", (found["id"],))["raw"] or "{}"
        owner = json.loads(raw).get("owner")
    return Pick(code, url, status, owner, found["id"], found["title"], note_id, detail)


def picks(store: Store, name: str) -> list[dict]:
    """The Author's picks of a Watchlist: ``video`` (store id), ``external_id``, ``url``, ``handle``, ``added_at``."""
    wid = watchlists.row(store, name)["id"]
    return store.query("SELECT v.id AS video, v.external_id, v.url, c.handle, p.added_at FROM watchlist_pick p "
                       "JOIN video v ON v.id = p.video_id LEFT JOIN channel c ON c.id = v.channel_id "
                       "WHERE p.watchlist_id = ? ORDER BY p.added_at, v.id", (wid,))
