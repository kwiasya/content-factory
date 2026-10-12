"""Scout and snapshot a Watchlist through the YouTube Data API.

``scout`` pulls each Reference channel's uploads (on the first run enough
history for the Outlier baseline: at least ``BACKFILL_PER_KIND`` videos of each
kind, or the whole history if it is shorter; afterwards only new uploads) and
runs the Watchlist's search queries, whose results bring Reference and
candidate channels.

When the uploads are caught up: a channel remembers ``uploads_through``, the
publish time of the newest upload of the last run that paged without a gap.
A later run pages its uploads, newest first, until a page reaches an upload
published at or before that mark (or the list ends). A video the store already
knows is no proof: a search hit or a fetch can bring a new upload before the
scout does, and a run the quota or an API error cut short leaves a gap below
the uploads it did read. Such a run does not move the mark, so the next run
pages through the gap. A channel scouted before the mark existed (no
``uploads_through`` yet) pages until a page brings nothing new, then gets one. Every video it reads gets a snapshot. ``snapshot`` records
views, likes and comments of every Reference of the Watchlist. Both plan the run
with ``quota.check`` before the first call and, if the quota runs out midway,
stop cleanly and report what was done.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from cf.research import env, ingest, quota, youtube
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
    knows of the channel. ``error`` is the API error that ended this channel's
    paging (what was read before it is kept), None when it went through.
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
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class QueryScout:
    """One search query this run: pages read, distinct videos found, the API error that ended it."""
    query: str
    pages: int
    results: int
    error: str | None = None

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
    candidates_error: str | None = None  # the API error of channels.list for candidate channels

    def failed(self) -> bool:
        """Every channel and query of the run (at least one) ended on an API error."""
        parts = [c.error for c in self.channels] + [q.error for q in self.queries]
        return bool(parts) and all(parts)

    def to_dict(self) -> dict:
        return asdict(self)


class _Run:
    """One scout or snapshot run: the store, transport, snapshot time and call count."""

    def __init__(self, store: Store, transport, taken_at: str):
        self.store, self.transport, self.taken_at = store, transport, taken_at
        self.calls: Counter = Counter()

    def call(self, method: str, fn, *args, **kwargs) -> dict:
        """``fn`` (a ``youtube`` function for ``method``), counted in ``calls`` once charged:
        an API error after the charge counts too, a quota refusal does not."""
        try:
            out = fn(self.store, *args, transport=self.transport, **kwargs)
        except youtube.YouTubeError:
            self.calls[method] += 1
            raise
        self.calls[method] += 1
        return out

    def videos(self, ids: list[str]) -> dict:
        """``videos.list`` for ``ids``; every returned video is ingested and snapshotted."""
        p = self.call("videos.list", youtube.videos_list, ids)
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
    mark = ch["uploads_through"]  # every upload published up to here is in the store
    state = {"pages": 0, "new": 0, "end": False, "done": not backfill, "error": None}

    def report() -> ChannelScout:
        counts = run.kind_counts(ch["id"])
        return ChannelScout(ch["external_id"], ch["handle"], "backfill" if backfill else "new", state["pages"],
                            state["new"], counts["short"], counts["long"], state["end"], state["done"],
                            state["error"])

    progress.append(report)
    try:
        _page_uploads(run, ch, playlist, backfill, mark, state)
    except youtube.YouTubeError as exc:  # the channel is gone, private, or the API failed: the rest goes on
        state["error"] = str(exc)
    return report()


def _page_uploads(run: _Run, ch: dict, playlist: str, backfill: bool, mark: str | None, state: dict) -> None:
    newest = None
    token = None
    while True:
        page = run.call("playlistItems.list", youtube.playlist_items_list, playlist, page_token=token)
        state["pages"] += 1
        items = [it.get("contentDetails") or {} for it in page.get("items") or []]
        items = [it for it in items if it.get("videoId") and it.get("videoPublishedAt")]  # private/deleted: no date
        ids = [it["videoId"] for it in items]
        dates = [it["videoPublishedAt"] for it in items]
        if newest is None and dates:
            newest = max(dates)
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
        elif mark is not None:
            if any(d <= mark for d in dates):
                break
        elif not fresh:  # no mark yet (scouted before it existed): a page with nothing new
            break
    # reached only when no call failed: everything from ``newest`` down to the old mark is in
    through = max(d for d in (mark, newest) if d) if (mark or newest) else None
    with run.store.transaction() as c:
        c.execute("UPDATE channel SET backfilled_at = COALESCE(backfilled_at, ?), uploads_through = ? WHERE id = ?",
                  (run.taken_at, through, ch["id"]))
    state["done"] = True


def _search(run: _Run, w: dict, query: str, *, published_after: str, pages: int,
            video_duration: str | None, progress: list) -> None:
    found: list[str] = []
    state = {"pages": 0, "error": None}
    progress.append(lambda: QueryScout(query, state["pages"], len(found), state["error"]))
    try:
        _page_search(run, w, query, published_after, pages, video_duration, found, state)
    except youtube.YouTubeError as exc:
        state["error"] = str(exc)


def _page_search(run: _Run, w: dict, query: str, published_after: str, pages: int,
                 video_duration: str | None, found: list[str], state: dict) -> None:
    token = None
    for _ in range(pages):
        p = run.call("search.list", youtube.search_list, query, published_after=published_after,
                     order="viewCount", relevance_language=w["language"], region_code=w["region"],
                     video_duration=video_duration, page_token=token)
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
        p = run.call("channels.list", youtube.channels_list, ids=ids[i:i + youtube.MAX_IDS])
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
    ``stopped`` set and everything read so far kept. An API error on one channel
    or query (a deleted channel, a bad filter) is recorded on its ``error`` and the
    run goes on; the call stays charged. A missing API key is refused up front.
    """
    w = watchlists.row(store, name)
    now = now or datetime.now(timezone.utc)
    run = _Run(store, transport, now_iso(now))
    chans = store.query(
        "SELECT c.id, c.external_id, c.handle, c.uploads_playlist_id, c.backfilled_at, c.uploads_through FROM channel c "
        "JOIN watchlist_channel wc ON wc.channel_id = c.id WHERE wc.watchlist_id = ? "
        "ORDER BY wc.added_at, c.id", (w["id"],))
    queries = json.loads(w["queries"]) if search and search_pages > 0 else []
    # the least a useful run needs: one page per channel and per query, their videos, candidate channels
    plan = {"playlistItems.list": len(chans), "videos.list": len(chans) + len(queries),
            "search.list": len(queries), "channels.list": 1 if queries else 0}
    quota.check(store, {m: n for m, n in plan.items() if n})
    if transport is None and not env.api_key():
        raise youtube.YouTubeError(env.KEY_HELP)
    ch_progress: list = []
    q_progress: list = []
    stopped = cand_error = None
    try:
        for ch in chans:
            _uploads(run, ch, ch_progress)
        after = now_iso(now - timedelta(days=search_days))
        for q in queries:
            _search(run, w, q, published_after=after, pages=search_pages,
                    video_duration=video_duration, progress=q_progress)
        if queries:
            try:
                _fill_channels(run, w["id"])
            except youtube.YouTubeError as exc:
                cand_error = str(exc)
    except quota.QuotaExceeded as exc:
        stopped = str(exc)
    return ScoutResult(name, run.taken_at, [r() for r in ch_progress], [r() for r in q_progress],
                       candidates(store, name), dict(run.calls), stopped, cand_error)


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
