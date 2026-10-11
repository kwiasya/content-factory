"""Outlier score: how many times a Reference beat its own channel's norm.

Views of the Reference (latest snapshot) divided by the median views (each
from its latest snapshot) of the same channel's last ``BASELINE_SIZE`` videos of
the same kind that are at least ``MIN_AGE_DAYS`` old, excluding the Reference
itself. None when fewer than ``MIN_BASELINE`` such videos have views, or the
Reference has no views or no kind. Computed on every query, never stored
(spec #1, "Outlier score").
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median
from typing import Iterable

from cf.research.store import Store

BASELINE_SIZE = 30
MIN_AGE_DAYS = 3
MIN_BASELINE = 5

_LATEST_VIEWS = ("(SELECT s.views FROM snapshot s WHERE s.video_id = v.id "
                 "ORDER BY s.taken_at DESC LIMIT 1)")


def _cutoff(now: datetime | None) -> str:
    now = now or datetime.now(timezone.utc)
    return (now - timedelta(days=MIN_AGE_DAYS)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def scores(store: Store, video_ids: Iterable[int], *, now: datetime | None = None) -> dict[int, float | None]:
    """Outlier score of each store video id (``now`` defaults to the current time)."""
    cutoff = _cutoff(now)
    ids = list(dict.fromkeys(video_ids))
    out: dict[int, float | None] = {}
    if not ids:
        return out
    marks = ",".join("?" * len(ids))
    videos = store.query(f"SELECT v.id, v.channel_id, v.kind, {_LATEST_VIEWS} AS views FROM video v "
                         f"WHERE v.id IN ({marks})", tuple(ids))
    # newest BASELINE_SIZE + 1 eligible videos per (channel, kind): enough to drop the video itself
    pools: dict[tuple[int, str], list[tuple[int, int]]] = {}
    for v in videos:
        key = (v["channel_id"], v["kind"])
        if v["kind"] is None or key in pools:
            continue
        rows = store.query(
            f"SELECT id, views FROM (SELECT v.id, v.published_at, {_LATEST_VIEWS} AS views FROM video v "
            "WHERE v.channel_id = ? AND v.kind = ? AND v.published_at <= ?) "
            "WHERE views IS NOT NULL ORDER BY published_at DESC, id DESC LIMIT ?",
            (key[0], key[1], cutoff, BASELINE_SIZE + 1))
        pools[key] = [(r["id"], r["views"]) for r in rows]
    for v in videos:
        if v["kind"] is None or v["views"] is None:
            out[v["id"]] = None
            continue
        base = [views for vid, views in pools[(v["channel_id"], v["kind"])] if vid != v["id"]][:BASELINE_SIZE]
        m = median(base) if len(base) >= MIN_BASELINE else 0
        out[v["id"]] = v["views"] / m if m else None
    for i in ids:
        out.setdefault(i, None)
    return out


def score(store: Store, external_id: str, *, now: datetime | None = None) -> float | None:
    """Outlier score of one YouTube Reference by video id; None for an unknown video."""
    row = store.one("SELECT id FROM video WHERE platform = 'youtube' AND external_id = ?", (external_id,))
    return None if row is None else scores(store, [row["id"]], now=now)[row["id"]]
