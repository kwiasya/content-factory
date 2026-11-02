"""Outlier score: how many times a Reference beat its own channel's norm.

Views of the Reference (latest snapshot with views) divided by the median views
(each from its latest snapshot with views) of the same channel's last ``BASELINE_SIZE`` videos of
the same kind that are at least ``MIN_AGE_DAYS`` old, excluding the Reference
itself. None when fewer than ``MIN_BASELINE`` such videos have views, or the
Reference has no views or no kind. Computed on every query, never stored
(spec #1, "Outlier score").

The rule is the same on every Platform, and per Platform by construction: a
channel lives on one Platform, so its baseline does too. Instagram reels are
``short``. An Instagram Reference without views (Business Discovery leaves
``view_count`` out on some media) falls back to likes against the median likes
of the same baseline (``basis`` says which was used).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Iterable

from cf.research.store import Store, now_iso

BASELINE_SIZE = 30
MIN_AGE_DAYS = 3
MIN_BASELINE = 5
LIKES_FALLBACK_PLATFORMS = ("instagram",)


def _latest(col: str) -> str:
    """The latest snapshot that has ``col``: a later one without it (hidden count, a gap) does not erase it."""
    return (f"(SELECT s.{col} FROM snapshot s WHERE s.video_id = v.id AND s.{col} IS NOT NULL "
            f"ORDER BY s.taken_at DESC LIMIT 1)")


_LATEST_VIEWS = _latest("views")


@dataclass(frozen=True)
class Score:
    """An Outlier score with what it was computed from: ``basis`` (views or likes), the baseline
    ``median`` and its ``baseline`` size. ``value`` None: not computable."""
    value: float | None
    basis: str | None = None
    median: float | None = None
    baseline: int = 0

    def to_dict(self) -> dict:
        return asdict(self)


def _cutoff(now: datetime | None) -> str:
    return now_iso((now or datetime.now(timezone.utc)) - timedelta(days=MIN_AGE_DAYS))


def _pool(store: Store, channel_id: int, kind: str, cutoff: str, col: str) -> list[tuple[int, int]]:
    """Newest ``BASELINE_SIZE + 1`` eligible videos of a (channel, kind) with ``col``: enough to drop the video itself."""
    rows = store.query(
        f"SELECT id, n FROM (SELECT v.id, v.published_at, {_latest(col)} AS n FROM video v "
        "WHERE v.channel_id = ? AND v.kind = ? AND v.published_at <= ?) "
        "WHERE n IS NOT NULL ORDER BY published_at DESC, id DESC LIMIT ?",
        (channel_id, kind, cutoff, BASELINE_SIZE + 1))
    return [(r["id"], r["n"]) for r in rows]


def detailed(store: Store, video_ids: Iterable[int], *, now: datetime | None = None) -> dict[int, Score]:
    """``Score`` of each store video id (``now`` defaults to the current time)."""
    cutoff = _cutoff(now)
    ids = list(dict.fromkeys(video_ids))
    out: dict[int, Score] = {}
    if not ids:
        return out
    marks = ",".join("?" * len(ids))
    videos = store.query(f"SELECT v.id, v.channel_id, v.kind, v.platform, {_LATEST_VIEWS} AS views, "
                         f"{_latest('likes')} AS likes FROM video v WHERE v.id IN ({marks})", tuple(ids))
    pools: dict[tuple, list[tuple[int, int]]] = {}
    for v in videos:
        basis = "views" if v["views"] is not None else \
            "likes" if v["likes"] is not None and v["platform"] in LIKES_FALLBACK_PLATFORMS else None
        if v["kind"] is None or v["channel_id"] is None or basis is None:
            out[v["id"]] = Score(None)
            continue
        key = (v["channel_id"], v["kind"], basis)
        if key not in pools:
            pools[key] = _pool(store, *key[:2], cutoff, basis)
        base = [n for vid, n in pools[key] if vid != v["id"]][:BASELINE_SIZE]
        m = median(base) if len(base) >= MIN_BASELINE else 0
        out[v["id"]] = Score(v[basis] / m if m else None, basis, m or None, len(base))
    for i in ids:
        out.setdefault(i, Score(None))
    return out


def scores(store: Store, video_ids: Iterable[int], *, now: datetime | None = None) -> dict[int, float | None]:
    """Outlier score of each store video id (``now`` defaults to the current time)."""
    return {i: s.value for i, s in detailed(store, video_ids, now=now).items()}


def score(store: Store, external_id: str, *, platform: str | None = None,
          now: datetime | None = None) -> float | None:
    """Outlier score of one Reference by YouTube video id or Instagram shortcode (``platform`` narrows
    it; YouTube wins a tie); None for an unknown video."""
    row = store.one("SELECT id FROM video WHERE external_id = ? AND (? IS NULL OR platform = ?) "
                    "ORDER BY platform = 'youtube' DESC LIMIT 1", (external_id, platform, platform))
    return None if row is None else scores(store, [row["id"]], now=now)[row["id"]]
