"""Scout and snapshot a Watchlist through the YouTube Data API.

``scout`` pulls each Reference channel's uploads (on the first run enough
history for the Outlier baseline: at least ``BACKFILL_PER_KIND`` videos of each
kind, or the whole history if it is shorter; afterwards only new uploads) and
runs the Watchlist's search queries, whose results bring Reference and
candidate channels. Every video it reads gets a snapshot. ``snapshot`` records
views, likes and comments of every Reference of the Watchlist. Both plan the run
with ``quota.check`` before the first call and, if the quota runs out midway,
stop cleanly and report what was done.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from cf.research import ingest, quota, youtube
from cf.research.kinds import KINDS
from cf.research import watchlist as watchlists
from cf.research.store import Store, now_iso

BACKFILL_PER_KIND = 30
DEFAULT_SEARCH_DAYS = 30
DEFAULT_SEARCH_PAGES = 1


@dataclass(frozen=True)
class Snapshot:
    taken_at: str
    views: int | None
    likes: int | None
    comments: int | None

    def to_dict(self) -> dict:
        return asdict(self)


def snapshot_history(store: Store, external_id: str) -> list[Snapshot]:
    """Every snapshot of one YouTube Reference, oldest first."""
    rows = store.query(
        "SELECT s.taken_at, s.views, s.likes, s.comments FROM snapshot s JOIN video v ON v.id = s.video_id "
        "WHERE v.platform = 'youtube' AND v.external_id = ? ORDER BY s.taken_at", (external_id,))
    return [Snapshot(**r) for r in rows]


@dataclass(frozen=True)
class Candidate:
    """A channel the Watchlist's search queries found that is not one of its Reference channels."""
    external_id: str
    handle: str | None
    title: str | None
    subscriber_count: int | None
    hits: int
    queries: list[str]

    def to_dict(self) -> dict:
        return asdict(self)


def candidates(store: Store, name: str) -> list[Candidate]:
    """Candidate channels of a Watchlist, most search hits first."""
    w = watchlists.row(store, name)
    rows = store.query(
        "SELECT c.external_id, c.handle, c.title, c.subscriber_count, COUNT(DISTINCT h.video_id) AS hits, "
        "json_group_array(DISTINCT h.query) AS queries FROM search_hit h JOIN video v ON v.id = h.video_id "
        "JOIN channel c ON c.id = v.channel_id WHERE h.watchlist_id = :wid AND c.id NOT IN "
        "(SELECT channel_id FROM watchlist_channel WHERE watchlist_id = :wid) "
        "GROUP BY c.id ORDER BY hits DESC, c.title", {"wid": w["id"]})
    return [Candidate(r["external_id"], r["handle"], r["title"], r["subscriber_count"], r["hits"],
                      sorted(json.loads(r["queries"]))) for r in rows]


# --- scout ------------------------------------------------------------------

@dataclass(frozen=True)
class ChannelScout:
    """What one Reference channel's uploads gave this run.

    ``mode`` is ``backfill`` until the first ingest has reached its target
    (``backfilled``), then ``new``. ``shorts``/``longs`` count what the store now
    knows of the channel.
    """
    external_id: str
    handle: str | None
    mode: str
    pages: int
    new_videos: int
    shorts: int
    longs: int
    history_end: bool
    backfilled: bool

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QueryScout:
    """One search query this run: pages read and distinct videos found."""
    query: str
    pages: int
    results: int

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class ScoutResult:
    watchlist: str
    taken_at: str
    channels: list[ChannelScout] = field(default_factory=list)
    queries: list[QueryScout] = field(default_factory=list)
    candidates: list[Candidate] = field(default_factory=list)
    calls: dict[str, int] = field(default_factory=dict)
    stopped: str | None = None  # why the run stopped early (quota), None when it finished

    def to_dict(self) -> dict:
        return asdict(self)


class _Run:
    """One scout or snapshot run: the store, transport, snapshot time and call count."""

    def __init__(self, store: Store, transport, taken_at: str):
        self.store, self.transport, self.taken_at = store, transport, taken_at
        self.calls: Counter = Counter()

    def videos(self, ids: list[str]) -> dict:
        """``videos.list`` for ``ids``; every returned video is ingested and snapshotted."""
        p = youtube.videos_list(self.store, ids, transport=self.transport)
        self.calls["videos.list"] += 1
        ingest.ingest_videos(self.store, p, fetched_at=self.taken_at)
        ingest.ingest_snapshots(self.store, p, taken_at=self.taken_at)
        return p

    def kind_counts(self, channel_id: int) -> dict[str, int]:
        rows = self.store.query("SELECT kind, COUNT(*) AS n FROM video WHERE channel_id = ? AND kind IS NOT NULL "
                                "GROUP BY kind", (channel_id,))
        got = {r["kind"]: r["n"] for r in rows}
        return {k: got.get(k, 0) for k in KINDS}

    def known(self, ids: list[str]) -> set[str]:
        """Those of ``ids`` the store has with a known duration."""
        if not ids:
            return set()
        rows = self.store.query(f"SELECT external_id FROM video WHERE platform = 'youtube' AND kind IS NOT NULL "
                                f"AND external_id IN ({','.join('?' * len(ids))})", tuple(ids))
        return {r["external_id"] for r in rows}


def _uploads(run: _Run, ch: dict, progress: list) -> ChannelScout:
    """Page one channel's uploads; append its ``ChannelScout`` to ``progress`` even if the quota stops it."""
    playlist = ch["uploads_playlist_id"] or "UU" + ch["external_id"][2:]
    backfill = ch["backfilled_at"] is None
    state = {"pages": 0, "new": 0, "end": False, "done": not backfill}

    def report() -> ChannelScout:
        counts = run.kind_counts(ch["id"])
        return ChannelScout(ch["external_id"], ch["handle"], "backfill" if backfill else "new", state["pages"],
                            state["new"], counts["short"], counts["long"], state["end"], state["done"])

    progress.append(report)
    token = None
    while True:
        page = youtube.playlist_items_list(run.store, playlist, page_token=token, transport=run.transport)
        run.calls["playlistItems.list"] += 1
        state["pages"] += 1
        ids = [(it.get("contentDetails") or {}).get("videoId") for it in page.get("items") or []
               if (it.get("contentDetails") or {}).get("videoPublishedAt")]  # private/deleted have no date
        ids = [i for i in ids if i]
        known = run.known(ids)
        fresh = [i for i in ids if i not in known]
        if fresh:
            got = run.videos(fresh)
            state["new"] += len(got.get("items") or [])
        token = page.get("nextPageToken")
        if not token:
            state["end"] = True
            break
        if backfill:
            if min(run.kind_counts(ch["id"]).values()) >= BACKFILL_PER_KIND:
                break
        elif known:
            break
    if backfill:
        with run.store.transaction() as c:
            c.execute("UPDATE channel SET backfilled_at = ? WHERE id = ?", (run.taken_at, ch["id"]))
        state["done"] = True
    return report()


def _search(run: _Run, w: dict, query: str, *, published_after: str, pages: int,
            video_duration: str | None, progress: list) -> None:
    found: list[str] = []
    state = {"pages": 0}
    progress.append(lambda: QueryScout(query, state["pages"], len(found)))
    token = None
    for _ in range(pages):
        p = youtube.search_list(run.store, query, published_after=published_after, order="viewCount",
                                relevance_language=w["language"], region_code=w["region"],
                                video_duration=video_duration, page_token=token, transport=run.transport)
        run.calls["search.list"] += 1
        state["pages"] += 1
        ids = ingest.ingest_search(run.store, p, watchlist=w["name"], query=query, found_at=run.taken_at)
        found.extend(i for i in ids if i not in found)
        if ids:
            run.videos(ids)
        token = p.get("nextPageToken")
        if not token:
            break


def _fill_channels(run: _Run, wid: int) -> None:
    """``channels.list`` for candidate channels the store knows only by id (handle, subscribers)."""
    rows = run.store.query(
        "SELECT DISTINCT c.external_id FROM search_hit h JOIN video v ON v.id = h.video_id "
        "JOIN channel c ON c.id = v.channel_id WHERE h.watchlist_id = ? AND c.fetched_at IS NULL "
        "ORDER BY c.external_id", (wid,))
    ids = [r["external_id"] for r in rows]
    for i in range(0, len(ids), youtube.MAX_IDS):
        p = youtube.channels_list(run.store, ids=ids[i:i + youtube.MAX_IDS], transport=run.transport)
        run.calls["channels.list"] += 1
        ingest.ingest_channels(run.store, p, fetched_at=run.taken_at)


def scout(store: Store, name: str, *, search: bool = True, search_days: float = DEFAULT_SEARCH_DAYS,
          search_pages: int = DEFAULT_SEARCH_PAGES, video_duration: str | None = None,
          transport: youtube.Transport | None = None, now: datetime | None = None) -> ScoutResult:
    """Pull uploads of every Reference channel of the Watchlist, then run its search queries.

    Search reads ``search_pages`` pages (50 results each) per query, ordered by
    views, published in the last ``search_days``, with the Watchlist's language
    and region; ``video_duration`` is the API's any/short/medium/long filter.
    Raises ``QuotaExceeded`` before any call when even one page per channel and
    query does not fit today's quota; a refusal later ends the run with
    ``stopped`` set and everything read so far kept.
    """
    w = watchlists.row(store, name)
    now = now or datetime.now(timezone.utc)
    run = _Run(store, transport, now_iso(now))
    chans = store.query(
        "SELECT c.id, c.external_id, c.handle, c.uploads_playlist_id, c.backfilled_at FROM channel c "
        "JOIN watchlist_channel wc ON wc.channel_id = c.id WHERE wc.watchlist_id = ? "
        "ORDER BY wc.added_at, c.id", (w["id"],))
    queries = json.loads(w["queries"]) if search and search_pages > 0 else []
    # the least a useful run needs: one page per channel and per query, their videos, candidate channels
    plan = {"playlistItems.list": len(chans), "videos.list": len(chans) + len(queries),
            "search.list": len(queries), "channels.list": 1 if queries else 0}
    quota.check(store, {m: n for m, n in plan.items() if n})
    ch_progress: list = []
    q_progress: list = []
    stopped = None
    try:
        for ch in chans:
            _uploads(run, ch, ch_progress)
        after = now_iso(now - timedelta(days=search_days))
        for q in queries:
            _search(run, w, q, published_after=after, pages=search_pages,
                    video_duration=video_duration, progress=q_progress)
        if queries:
            _fill_channels(run, w["id"])
    except quota.QuotaExceeded as exc:
        stopped = str(exc)
    return ScoutResult(name, run.taken_at, [r() for r in ch_progress], [r() for r in q_progress],
                       candidates(store, name), dict(run.calls), stopped)


# --- snapshot ---------------------------------------------------------------

@dataclass(frozen=True)
class SnapshotResult:
    watchlist: str
    taken_at: str
    videos: int  # Reference snapshotted this run
    missing: list[str] = field(default_factory=list)  # gone from YouTube (deleted or private)
    calls: dict[str, int] = field(default_factory=dict)
    stopped: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def snapshot(store: Store, name: str, *, transport: youtube.Transport | None = None,
             now: datetime | None = None) -> SnapshotResult:
    """Record views, likes and comments of every Reference of the Watchlist (its channels' videos
    and its search hits), one snapshot per video, ``videos.list`` in batches of 50.

    Raises ``QuotaExceeded`` before any call when the whole run does not fit today.
    """
    w = watchlists.row(store, name)
    run = _Run(store, transport, now_iso(now))
    ids = [r["external_id"] for r in store.query(
        "SELECT v.external_id FROM video v WHERE v.platform = 'youtube' AND (v.channel_id IN "
        "(SELECT channel_id FROM watchlist_channel WHERE watchlist_id = :wid) OR v.id IN "
        "(SELECT video_id FROM search_hit WHERE watchlist_id = :wid)) ORDER BY v.published_at DESC, v.id",
        {"wid": w["id"]})]
    batches = [ids[i:i + youtube.MAX_IDS] for i in range(0, len(ids), youtube.MAX_IDS)]
    if batches:
        quota.check(store, {"videos.list": len(batches)})
    done, missing, stopped = 0, [], None
    try:
        for batch in batches:
            got = {it["id"] for it in run.videos(batch).get("items") or []}
            done += len(got)
            missing += [i for i in batch if i not in got]
    except quota.QuotaExceeded as exc:
        stopped = str(exc)
    return SnapshotResult(name, run.taken_at, done, missing, dict(run.calls), stopped)
