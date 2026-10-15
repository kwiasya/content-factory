"""Turn recorded Data API and Graph API payloads into store rows.

``*_row`` functions are pure (payload item → dict of column values);
``ingest_*`` functions upsert those rows and return the store ids. This is the
layer tests feed with fixtures; the network never reaches past ``youtube`` and
``instagram``.

Instagram (ADR 0010): a Reference channel is keyed by the account's Graph id
with its ``@username`` as handle; a Reference by its permalink shortcode (the
``DeUex6UKm5s`` of ``instagram.com/reel/DeUex6UKm5s/``), so a reel known from
the Graph API, from yt-dlp or only from a pasted link is one row. Reels are
``short``; other media keep no kind. The title is the caption's first line.
"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from urllib.parse import unquote, urlsplit

from cf.research.kinds import parse_iso_duration, video_kind
from cf.research.store import Store, StoreError, dumps, now_iso

WATCH_URL = "https://www.youtube.com/watch?v="
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
SHORT_LINK_HOSTS = {"youtu.be", "www.youtu.be"}


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_handle(handle: str | None) -> str | None:
    """``@name`` lowercase, or None."""
    if not handle:
        return None
    return "@" + handle.strip().lstrip("@").lower()


def channel_row(item: dict) -> dict:
    """Column values of ``channel`` from one ``channels.list`` item (own flag not included)."""
    sn = item.get("snippet") or {}
    stats = item.get("statistics") or {}
    uploads = ((item.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
    return {
        "platform": "youtube",
        "external_id": item["id"],
        "handle": normalize_handle(sn.get("customUrl")),
        "title": sn.get("title"),
        "description": sn.get("description"),
        "country": sn.get("country"),
        "published_at": sn.get("publishedAt"),
        "subscriber_count": None if stats.get("hiddenSubscriberCount") else _int(stats.get("subscriberCount")),
        "video_count": _int(stats.get("videoCount")),
        "view_count": _int(stats.get("viewCount")),
        "uploads_playlist_id": uploads,
        "raw": dumps(item),
    }


def ingest_channels(store: Store, payload: dict, *, own: bool | None = None,
                    fetched_at: str | None = None) -> list[int]:
    """Upsert every channel in a ``channels.list`` payload; return their store ids in payload order.

    ``own`` sets the own flag when given; None keeps what the store has (new rows: not own).
    """
    ts = fetched_at or now_iso()
    ids: list[int] = []
    with store.transaction() as c:
        for item in payload.get("items") or []:
            row = channel_row(item)
            row["fetched_at"] = ts
            row["own"] = int(bool(own))
            cols = list(row)
            updates = [f"{k} = excluded.{k}" for k in cols if k not in ("platform", "external_id", "own")]
            if own is not None:
                updates.append("own = excluded.own")
            c.execute(
                f"INSERT INTO channel ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
                f"ON CONFLICT (platform, external_id) DO UPDATE SET {', '.join(updates)}",
                tuple(row.values()))
            got = c.execute("SELECT id FROM channel WHERE platform = ? AND external_id = ?",
                            (row["platform"], row["external_id"])).fetchone()
            ids.append(int(got[0]))
    return ids


# --- YouTube links ------------------------------------------------------------

def video_url(external_id: str) -> str:
    """The watch URL of a YouTube video id."""
    return WATCH_URL + external_id


@dataclass(frozen=True)
class YouTubeLink:
    """A link on a YouTube host: ``short_link`` for ``youtu.be/<id>``, the non-empty path segments
    (still URL-encoded) and the query string."""
    short_link: bool
    segments: list[str]
    query: str


def youtube_link(text: str) -> YouTubeLink | None:
    """Split a YouTube link (scheme optional); None when its host is not YouTube's."""
    t = text.strip()
    parts = urlsplit(t if "://" in t else "https://" + t)
    host = (parts.hostname or "").lower()
    if host not in YOUTUBE_HOSTS and host not in SHORT_LINK_HOSTS:
        return None
    return YouTubeLink(host in SHORT_LINK_HOSTS, [s for s in parts.path.split("/") if s], parts.query)


# --- videos -----------------------------------------------------------------


def _channel_id(c, external_id: str, title: str | None) -> int:
    """Store id of a YouTube channel; an unseen one gets a bare row (a candidate, in no Watchlist)."""
    c.execute("INSERT INTO channel (platform, external_id, title) VALUES ('youtube', ?, ?) "
              "ON CONFLICT (platform, external_id) DO NOTHING", (external_id, title))
    return int(c.execute("SELECT id FROM channel WHERE platform = 'youtube' AND external_id = ?",
                         (external_id,)).fetchone()[0])


def video_row(item: dict) -> dict:
    """Column values of ``video`` from one ``videos.list`` item (channel and own flag not included)."""
    sn = item.get("snippet") or {}
    duration = parse_iso_duration((item.get("contentDetails") or {}).get("duration"))
    return {
        "platform": "youtube",
        "external_id": item["id"],
        "title": sn.get("title"),
        "description": sn.get("description"),
        "published_at": sn.get("publishedAt"),
        "duration_s": duration,
        "kind": video_kind(duration),
        "tags": dumps(sn.get("tags") or []),
        "url": video_url(item["id"]),
        "raw": dumps(item),
    }


def upsert_video(c, row: dict, channel_id: int | None, own: int) -> int:
    """Insert or update one ``video`` row inside an open transaction ``c``; return its store id.

    A column the row lacks (None) keeps what the store has; ``own`` never goes back to 0.
    """
    row = {**row, "channel_id": channel_id, "own": own}
    cols = list(row)
    keep = ("platform", "external_id", "own")
    # a field the payload lacks (search snippets have no duration) never erases what the store has
    updates = [f"{k} = COALESCE(excluded.{k}, {k})" for k in cols if k not in keep]
    updates.append("own = MAX(own, excluded.own)")
    c.execute(f"INSERT INTO video ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
              f"ON CONFLICT (platform, external_id) DO UPDATE SET {', '.join(updates)}",
              tuple(row.values()))
    return int(c.execute("SELECT id FROM video WHERE platform = ? AND external_id = ?",
                         (row["platform"], row["external_id"])).fetchone()[0])


def ingest_videos(store: Store, payload: dict, *, fetched_at: str | None = None) -> list[int]:
    """Upsert every video of a ``videos.list`` payload; return their store ids in payload order.

    A video's channel is found by ``snippet.channelId``; a channel the store has
    not seen gets a bare row (a candidate outside every Watchlist). A video of an
    own channel is own. Media, transcript and card flags are never touched.
    """
    ts = fetched_at or now_iso()
    ids: list[int] = []
    with store.transaction() as c:
        for item in payload.get("items") or []:
            sn = item.get("snippet") or {}
            cid = _channel_id(c, sn["channelId"], sn.get("channelTitle"))
            own = c.execute("SELECT own FROM channel WHERE id = ?", (cid,)).fetchone()[0]
            ids.append(upsert_video(c, {**video_row(item), "fetched_at": ts}, cid, int(own)))
    return ids


# --- snapshots --------------------------------------------------------------

def snapshot_row(item: dict) -> dict:
    """``views``, ``likes``, ``comments`` of one ``videos.list`` item (None where hidden or off)."""
    stats = item.get("statistics") or {}
    return {"views": _int(stats.get("viewCount")), "likes": _int(stats.get("likeCount")),
            "comments": _int(stats.get("commentCount"))}


def ingest_snapshots(store: Store, payload: dict, *, taken_at: str | None = None) -> list[int]:
    """Record one snapshot per video of a ``videos.list`` payload at ``taken_at`` (default now).

    Videos the store does not have are skipped; a second write at the same
    ``taken_at`` replaces the first. Returns the store ids of the videos snapshotted.
    """
    ts = taken_at or now_iso()
    ids: list[int] = []
    with store.transaction() as c:
        for item in payload.get("items") or []:
            got = c.execute("SELECT id FROM video WHERE platform = 'youtube' AND external_id = ?",
                            (item.get("id"),)).fetchone()
            if got is None:
                continue
            row = snapshot_row(item)
            c.execute("INSERT INTO snapshot (video_id, taken_at, views, likes, comments) VALUES (?, ?, ?, ?, ?) "
                      "ON CONFLICT (video_id, taken_at) DO UPDATE SET views = excluded.views, "
                      "likes = excluded.likes, comments = excluded.comments",
                      (got[0], ts, row["views"], row["likes"], row["comments"]))
            ids.append(int(got[0]))
    return ids


# --- search -----------------------------------------------------------------

def search_video_row(item: dict) -> dict | None:
    """Column values of ``video`` from one ``search.list`` result (HTML entities decoded); None for non-videos.

    A search snippet has no duration, so ``kind`` stays unknown until ``videos.list``.
    """
    vid = (item.get("id") or {}).get("videoId")
    if not vid:
        return None
    sn = item.get("snippet") or {}
    unescape = lambda t: html.unescape(t) if t is not None else None  # noqa: E731
    return {"platform": "youtube", "external_id": vid, "title": unescape(sn.get("title")),
            "description": unescape(sn.get("description")), "published_at": sn.get("publishedAt"),
            "url": video_url(vid)}


def ingest_search(store: Store, payload: dict, *, watchlist: str, query: str,
                  found_at: str | None = None) -> list[str]:
    """Record the video results of one ``search.list`` page as hits of ``watchlist`` for ``query``.

    Unseen videos get a row from the snippet (no duration or kind yet: follow with
    ``videos.list``); unseen channels get a bare row and stay outside the
    Watchlist as candidates. Returns the video ids in result order.
    """
    ts = found_at or now_iso()
    out: list[str] = []
    with store.transaction() as c:
        w = c.execute("SELECT id FROM watchlist WHERE name = ?", (watchlist,)).fetchone()
        if w is None:
            raise StoreError(f"no Watchlist named {watchlist!r}")
        for item in payload.get("items") or []:
            row = search_video_row(item)
            if row is None:
                continue
            sn = item.get("snippet") or {}
            cid = _channel_id(c, sn["channelId"], html.unescape(sn.get("channelTitle") or "") or None)
            c.execute("INSERT INTO video (platform, external_id, channel_id, title, description, published_at, url, "
                      "fetched_at) VALUES (:platform, :external_id, :cid, :title, :description, :published_at, "
                      ":url, :ts) ON CONFLICT (platform, external_id) DO NOTHING", {**row, "cid": cid, "ts": ts})
            vid = c.execute("SELECT id FROM video WHERE platform = 'youtube' AND external_id = ?",
                            (row["external_id"],)).fetchone()[0]
            c.execute("INSERT OR IGNORE INTO search_hit (watchlist_id, video_id, query, found_at) VALUES (?, ?, ?, ?)",
                      (w[0], vid, query, ts))
            out.append(row["external_id"])
    return out


# --- Instagram --------------------------------------------------------------------

INSTAGRAM_HOSTS = {"instagram.com", "www.instagram.com", "m.instagram.com", "instagr.am", "www.instagr.am"}
IG_MEDIA_PATHS = {"reel", "reels", "p", "tv"}
SHORTCODE_RE = re.compile(r"[\w-]{5,40}")  # always fullmatch


def instagram_segments(text: str) -> list[str] | None:
    """The non-empty path segments of an Instagram link (scheme optional, query and tracking
    parameters dropped); None when the host is not Instagram's."""
    t = text.strip()
    parts = urlsplit(t if "://" in t else "https://" + t)
    if (parts.hostname or "").lower() not in INSTAGRAM_HOSTS:
        return None
    return [unquote(x).strip() for x in parts.path.split("/") if x.strip()]


def instagram_shortcode(text: str) -> str | None:
    """The shortcode of a reel or post link (``/reel/<code>/``, ``/p/<code>/``, ``/<user>/reel/<code>/``);
    None for anything else."""
    segs = instagram_segments(text or "")
    if not segs:
        return None
    for i, seg in enumerate(segs[:-1]):
        if seg in IG_MEDIA_PATHS and SHORTCODE_RE.fullmatch(segs[i + 1]):
            return segs[i + 1]
    return None


def instagram_url(shortcode: str, media_product_type: str | None = "REELS") -> str:
    """The canonical link of a media: ``/reel/<code>/`` for reels, ``/p/<code>/`` for the rest."""
    return f"https://www.instagram.com/{'reel' if media_product_type in ('REELS', None) else 'p'}/{shortcode}/"


def ig_time(ts: str | None) -> str | None:
    """Graph API ``2026-10-10T16:15:44+0000`` as ISO UTC with ``Z``."""
    if not ts:
        return None
    return ts[:19] + "Z" if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(\+0000|Z)?", ts) else ts


def first_line(caption: str | None) -> str | None:
    """The first non-empty line of a caption, whitespace collapsed; None without one."""
    for line in (caption or "").splitlines():
        line = " ".join(line.split())
        if line:
            return line
    return None


HASHTAG_RE = re.compile(r"#(\w+)")


def ig_channel_row(acct: dict) -> dict:
    """Column values of ``channel`` from a Business Discovery or own account object (own flag not included)."""
    return {
        "platform": "instagram",
        "external_id": str(acct["id"]),
        "handle": normalize_handle(acct.get("username")),
        "title": acct.get("name") or acct.get("username"),
        "description": acct.get("biography"),
        "subscriber_count": _int(acct.get("followers_count")),
        "video_count": _int(acct.get("media_count")),
        "raw": dumps({k: v for k, v in acct.items() if k not in ("media", "_usage")}),
    }


def ingest_ig_account(store: Store, acct: dict, *, own: bool | None = None, fetched_at: str | None = None) -> int:
    """Upsert one Instagram account; return its store id. ``own`` as in ``ingest_channels``."""
    row = {**ig_channel_row(acct), "fetched_at": fetched_at or now_iso(), "own": int(bool(own))}
    cols = list(row)
    updates = [f"{k} = excluded.{k}" for k in cols if k not in ("platform", "external_id", "own")]
    if own is not None:
        updates.append("own = excluded.own")
    with store.transaction() as c:
        c.execute(f"INSERT INTO channel ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
                  f"ON CONFLICT (platform, external_id) DO UPDATE SET {', '.join(updates)}", tuple(row.values()))
        return int(c.execute("SELECT id FROM channel WHERE platform = 'instagram' AND external_id = ?",
                             (row["external_id"],)).fetchone()[0])


def ig_media_row(item: dict) -> dict | None:
    """Column values of ``video`` from one Graph API media object; None without a permalink shortcode."""
    code = instagram_shortcode(item.get("permalink") or "")
    if code is None:
        return None
    caption = item.get("caption")
    product = item.get("media_product_type")
    return {
        "platform": "instagram",
        "external_id": code,
        "title": first_line(caption),
        "description": caption,
        "published_at": ig_time(item.get("timestamp")),
        "kind": "short" if product == "REELS" else None,
        "tags": dumps(HASHTAG_RE.findall(caption or "")),
        "url": instagram_url(code, product),
        "raw": dumps({k: v for k, v in item.items() if k != "insights"}),
    }


def ig_snapshot_row(item: dict) -> dict:
    """``views``, ``likes``, ``comments`` of one media object (own media: views from its insights)."""
    views = _int(item.get("view_count"))
    if views is None:
        views = insight_values(item).get("views")
    return {"views": views, "likes": _int(item.get("like_count")), "comments": _int(item.get("comments_count"))}


def insight_values(item: dict) -> dict[str, int]:
    """``{metric: value}`` of the insights nested in a media object or of an ``/insights`` payload."""
    data = (item.get("insights") or {}).get("data") if "insights" in item else item.get("data")
    out = {}
    for m in data or []:
        vals = m.get("values") or []
        v = _int(vals[0].get("value")) if vals else _int(m.get("total_value", {}).get("value"))
        if m.get("name") and v is not None:
            out[m["name"]] = v
    return out


def _snapshot(c, vid: int, ts: str, snap: dict) -> None:
    c.execute("INSERT INTO snapshot (video_id, taken_at, views, likes, comments) VALUES (?, ?, ?, ?, ?) "
              "ON CONFLICT (video_id, taken_at) DO UPDATE SET views = excluded.views, "
              "likes = excluded.likes, comments = excluded.comments",
              (vid, ts, snap["views"], snap["likes"], snap["comments"]))


def ingest_ig_media(store: Store, channel_id: int, items: list[dict], *, reels_only: bool = True,
                    fetched_at: str | None = None, taken_at: str | None = None) -> list[int]:
    """Upsert media of one account (reels only unless ``reels_only`` is false) and record one snapshot
    each at ``taken_at``; return their store ids in payload order. Media of an own account are own."""
    ts = fetched_at or now_iso()
    snap_ts = taken_at or ts
    ids: list[int] = []
    with store.transaction() as c:
        own = int(c.execute("SELECT own FROM channel WHERE id = ?", (channel_id,)).fetchone()[0])
        for item in items:
            if reels_only and item.get("media_product_type") != "REELS":
                continue
            row = ig_media_row(item)
            if row is None:
                continue
            vid = upsert_video(c, {**row, "fetched_at": ts}, channel_id, own)
            _snapshot(c, vid, snap_ts, ig_snapshot_row(item))
            ids.append(vid)
    return ids


INSIGHT_COLUMNS = {"views": "views", "reach": "reach", "saved": "saved", "shares": "shares",
                   "total_interactions": "interactions", "ig_reels_avg_watch_time": "avg_watch_ms",
                   "ig_reels_video_view_total_time": "total_watch_ms"}


def ingest_insights(store: Store, video_id: int, values: dict[str, int], *, likes: int | None = None,
                    comments: int | None = None, taken_at: str | None = None) -> None:
    """Record one ``insight`` row of an own reel (metric names as the Graph API gives them)."""
    row = {col: values.get(metric) for metric, col in INSIGHT_COLUMNS.items()}
    row.update(likes=likes, comments=comments)
    cols = list(row)
    with store.transaction() as c:
        c.execute(f"INSERT INTO insight (video_id, taken_at, {', '.join(cols)}) VALUES (?, ?, "
                  f"{', '.join('?' for _ in cols)}) ON CONFLICT (video_id, taken_at) DO UPDATE SET "
                  f"{', '.join(f'{k} = excluded.{k}' for k in cols)}",
                  (video_id, taken_at or now_iso(), *row.values()))
