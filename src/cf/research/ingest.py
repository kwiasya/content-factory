"""Turn recorded Data API payloads into store rows.

``*_row`` functions are pure (payload item → dict of column values);
``ingest_*`` functions upsert those rows and return the store ids. This is the
layer tests feed with fixtures; the network never reaches past ``youtube``.
"""

from __future__ import annotations

import html

from cf.research.kinds import parse_iso_duration, video_kind
from cf.research.store import Store, StoreError, dumps, now_iso

WATCH_URL = "https://www.youtube.com/watch?v="


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


# --- videos -----------------------------------------------------------------

def video_url(external_id: str) -> str:
    return WATCH_URL + external_id


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


def _upsert_video(c, row: dict, channel_id: int, own: int) -> int:
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
            ids.append(_upsert_video(c, {**video_row(item), "fetched_at": ts}, cid, int(own)))
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
