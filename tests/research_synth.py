"""Synthetic videos.list payloads and snapshots for Outlier score and feed tests."""

from datetime import datetime, timedelta, timezone

from cf.research import ingest

NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(days: float = 0, hours: float = 0) -> str:
    return iso(NOW - timedelta(days=days, hours=hours))


def video_item(vid: str, channel: str, published_at: str, duration_s: int, views: int | None,
               title: str | None = None, channel_title: str | None = None) -> dict:
    m, s = divmod(duration_s, 60)
    h, m = divmod(m, 60)
    dur = "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{s}S" if s else "")
    stats = {"likeCount": "1", "favoriteCount": "0"}
    if views is not None:
        stats["viewCount"] = str(views)
    return {"kind": "youtube#video", "id": vid,
            "snippet": {"publishedAt": published_at, "channelId": channel, "title": title or f"video {vid}",
                        "description": "", "channelTitle": channel_title or channel},
            "contentDetails": {"duration": dur}, "statistics": stats}


def add_videos(store, items: list[dict], taken_at: str | None = None) -> None:
    """Ingest ``items`` and record one snapshot of them at ``taken_at`` (default: NOW)."""
    p = {"items": items}
    ingest.ingest_videos(store, p)
    ingest.ingest_snapshots(store, p, taken_at=taken_at or iso(NOW))


def channel_payload(channel: str, handle: str, title: str | None = None) -> dict:
    """A ``channels.list`` payload for one synthetic channel."""
    return {"items": [{"id": channel,
                       "snippet": {"title": title or handle.lstrip("@").title(), "customUrl": handle},
                       "contentDetails": {"relatedPlaylists": {"uploads": "UU" + channel[2:]}},
                       "statistics": {"subscriberCount": "1000", "videoCount": "10", "viewCount": "100000"}}]}


def add_member(store, watchlist: str, channel: str, handle: str) -> None:
    from cf.research import watchlist as wl
    p = channel_payload(channel, handle)
    wl.add_channel(store, watchlist, channel, transport=lambda m, params: p)


class FakeYouTube:
    """A Data API stand-in: channel uploads, videos, search pages and channels from in-memory data.

    ``uploads[channel_id]`` is a list of ``videos.list`` items, newest first;
    ``searches[q]`` a list of ``search.list`` payloads (pages); ``channels`` maps a
    channel id to its ``channels.list`` item. Every call is recorded in ``calls``.
    """

    def __init__(self):
        self.uploads: dict[str, list[dict]] = {}
        self.searches: dict[str, list[dict]] = {}
        self.channels: dict[str, dict] = {}
        self.extra_videos: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []

    def methods(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for m, _ in self.calls:
            out[m] = out.get(m, 0) + 1
        return out

    def _videos(self) -> dict[str, dict]:
        allv = dict(self.extra_videos)
        for items in self.uploads.values():
            allv.update({v["id"]: v for v in items})
        return allv

    def __call__(self, method: str, params: dict) -> dict:
        self.calls.append((method, dict(params)))
        if method == "playlistItems.list":
            items = self.uploads.get("UC" + params["playlistId"][2:], [])
            start = int(params.get("pageToken") or 0)
            size = int(params.get("maxResults") or 50)
            page = items[start:start + size]
            out = {"items": [{"snippet": {"title": v["snippet"]["title"],
                                          "resourceId": {"kind": "youtube#video", "videoId": v["id"]}},
                              "contentDetails": {"videoId": v["id"], "videoPublishedAt": v["snippet"]["publishedAt"]}}
                             for v in page]}
            if start + size < len(items):
                out["nextPageToken"] = str(start + size)
            return out
        if method == "videos.list":
            allv = self._videos()
            return {"items": [allv[i] for i in params["id"].split(",") if i in allv]}
        if method == "search.list":
            pages = self.searches.get(params["q"], [{"items": []}])
            return pages[int(params.get("pageToken") or 0)]
        if method == "channels.list":
            return {"items": [self.channels[i] for i in params["id"].split(",") if i in self.channels]}
        raise AssertionError(f"unexpected call {method}")
