"""Traits of a Watchlist's outliers against all its scored References (ADR 0015).

Pornhub cards have no transcript, so what can be compared is packaging and
timing: duration buckets, title features, tags and categories, publish weekday
and hour (UTC and local), and the median rating. Each trait is a ``Share``: how
many of all scored References and of the outliers (Outlier score at least
``min_outlier``) carry it, their shares and the lift (outlier share over overall
share; None where nobody carries it). Tags and categories need ``MIN_SUPPORT``
References. Works on every Platform; ``platform`` narrows it. Deterministic:
ties are ordered by key.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, tzinfo
from statistics import median

from cf.research import feed, measure
from cf.research.store import Store

MIN_SUPPORT = 3
DURATION_BUCKETS = (("<5", 0, 300), ("5-10", 300, 600), ("10-20", 600, 1200), ("20+", 1200, None))
TITLE_FLAGS = ("pov", "digits", "brackets", "emoji", "caps")
CAPS_SHARE = 0.5


@dataclass(frozen=True)
class Share:
    key: str
    all: int
    outliers: int
    share_all: float
    share_outliers: float
    lift: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class TraitsReport:
    watchlist: str
    platform: str | None
    days: float
    min_outlier: float
    references: int
    outliers: int
    duration: list[Share] = field(default_factory=list)
    title: list[Share] = field(default_factory=list)
    title_length: dict = field(default_factory=dict)
    tags: list[Share] = field(default_factory=list)
    categories: list[Share] = field(default_factory=list)
    weekday_utc: list[Share] = field(default_factory=list)
    hour_utc: list[Share] = field(default_factory=list)
    weekday_local: list[Share] = field(default_factory=list)
    hour_local: list[Share] = field(default_factory=list)
    rating: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


def _share(key: str, n_all: int, n_out: int, total: int, outliers: int) -> Share:
    sa = round(n_all / total, 3) if total else 0.0
    so = round(n_out / outliers, 3) if outliers else 0.0
    lift = round(so / sa, 3) if sa and outliers else None
    return Share(key, n_all, n_out, sa, so, lift)


def _shares(items: list[tuple[set[str], bool]], keys: list[str], total: int, outliers: int) -> list[Share]:
    return [_share(k, sum(k in s for s, _ in items), sum(k in s for s, o in items if o), total, outliers)
            for k in keys]


def _ranked(items: list[tuple[set[str], bool]], total: int, outliers: int) -> list[Share]:
    keys = sorted({k for s, _ in items for k in s})
    got = [s for s in _shares(items, keys, total, outliers) if s.all >= MIN_SUPPORT]
    return sorted(got, key=lambda s: (-(s.lift or 0), -s.outliers, -s.all, s.key))


def _seen(items: list[tuple[set[str], bool]], order: list[str], total: int, outliers: int) -> list[Share]:
    keys = [k for k in order if any(k in s for s, _ in items)]
    return _shares(items, keys, total, outliers)


def _bucket(duration_s: float | None) -> str | None:
    if duration_s is None:
        return None
    for name, lo, hi in DURATION_BUCKETS:
        if duration_s >= lo and (hi is None or duration_s < hi):
            return name
    return None


def _median(xs: list[float]) -> float | None:
    return float(median(xs)) if xs else None


def traits(store: Store, watchlist: str, *, platform: str | None = None, days: float = 90,
           min_outlier: float = 2.0, tz: tzinfo | None = None, now: datetime | None = None) -> TraitsReport:
    """Traits of the Watchlist's outliers published in the last ``days`` against all its scored
    References of that window (``tz``: the local zone, default this Mac's)."""
    rows = [r for r in feed.feed(store, watchlist, lookback_days=days, platform=platform, limit=None, now=now)
            if r.outlier is not None]
    total = len(rows)
    out_flags = [r.outlier >= min_outlier for r in rows]
    outliers = sum(out_flags)
    extra = {}
    for r in rows:
        v = store.one("SELECT tags, raw FROM video WHERE platform = ? AND external_id = ?",
                      (r.platform, r.external_id))
        raw = json.loads(v["raw"]) if r.platform == "pornhub" and v["raw"] else {}
        extra[(r.platform, r.external_id)] = (json.loads(v["tags"] or "[]"), raw.get("categories") or [])

    def items(fn) -> list[tuple[set[str], bool]]:
        return [(fn(r), o) for r, o in zip(rows, out_flags)]

    def flags(r) -> set[str]:
        f = measure.title_features(r.title)
        on = {"pov": f["pov"], "digits": f["digits"] > 0, "brackets": f["brackets"], "emoji": f["emoji"] > 0,
              "caps": (f["caps_share"] or 0) >= CAPS_SHARE}
        return {k for k, v in on.items() if v}

    def when(r, key: str) -> set[str]:
        got = measure.published(r.published_at, tz).get(key)
        return set() if got is None else {str(got)}

    def lengths(key: str) -> dict:
        vals = [(measure.title_features(r.title)[key], o) for r, o in zip(rows, out_flags) if r.title]
        return {"all": _median([v for v, _ in vals]), "outliers": _median([v for v, o in vals if o])}

    ratings = [(r.rating, o) for r, o in zip(rows, out_flags) if r.rating is not None]
    hours = [str(h) for h in range(24)]
    return TraitsReport(
        watchlist, platform, days, min_outlier, total, outliers,
        duration=_shares(items(lambda r: {b} if (b := _bucket(r.duration_s)) else set()),
                         [b[0] for b in DURATION_BUCKETS], total, outliers),
        title=_shares(items(flags), list(TITLE_FLAGS), total, outliers),
        title_length={"chars": lengths("title_chars"), "words": lengths("title_words")},
        tags=_ranked(items(lambda r: set(extra[(r.platform, r.external_id)][0])), total, outliers),
        categories=_ranked(items(lambda r: set(extra[(r.platform, r.external_id)][1])), total, outliers),
        weekday_utc=_seen(items(lambda r: when(r, "weekday")), list(measure.WEEKDAYS), total, outliers),
        hour_utc=_seen(items(lambda r: when(r, "hour_utc")), hours, total, outliers),
        weekday_local=_seen(items(lambda r: when(r, "weekday_local")), list(measure.WEEKDAYS), total, outliers),
        hour_local=_seen(items(lambda r: when(r, "hour_local")), hours, total, outliers),
        rating={"all": _median([x for x, _ in ratings]), "outliers": _median([x for x, o in ratings if o])})
