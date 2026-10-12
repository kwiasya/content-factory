"""YouTube Data API v3 quota accounting.

Every Data API call is charged here *before* it is made: ``charge`` adds the
method's units to today's row in ``quota`` or raises ``QuotaExceeded`` when the
call would take its bucket past the daily limit. Google's buckets (2026,
developers.google.com/youtube/v3/determine_quota_cost): ``search.list`` has its
own bucket of 100 calls a day at 1 unit each; all other methods share 10 000
units a day. Limits can be raised for a project with more quota through
``CF_QUOTA_DEFAULT`` / ``CF_QUOTA_SEARCH``. The quota day follows Google's reset
at midnight Pacific time. ``check`` tests a run's whole plan up front.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from cf.research.store import Store

DEFAULT_LIMITS = {"default": 10_000, "search": 100}
RESET_TZ = ZoneInfo("America/Los_Angeles")
# method → (bucket, units per call). Anything unlisted costs 1 unit of "default".
COSTS = {
    "search.list": ("search", 1),
    "channels.list": ("default", 1),
    "playlistItems.list": ("default", 1),
    "playlists.list": ("default", 1),
    "videos.list": ("default", 1),
    "commentThreads.list": ("default", 1),
    "videoCategories.list": ("default", 1),
    "captions.list": ("default", 50),
}


class QuotaExceeded(Exception):
    """The call would take today's usage of a quota bucket past its limit; nothing was called."""


@dataclass(frozen=True)
class MethodUsage:
    method: str
    calls: int
    units: int


@dataclass(frozen=True)
class BucketUsage:
    bucket: str
    limit: int
    used: int
    remaining: int


@dataclass(frozen=True)
class Usage:
    day: str
    buckets: list[BucketUsage] = field(default_factory=list)
    by_method: list[MethodUsage] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def cost(method: str) -> tuple[str, int]:
    """``(bucket, units)`` one call of ``method`` (e.g. ``videos.list``) costs."""
    return COSTS.get(method, ("default", 1))


def limits() -> dict[str, int]:
    """Daily limit per bucket, with ``CF_QUOTA_<BUCKET>`` overrides."""
    out = {}
    for bucket, default in DEFAULT_LIMITS.items():
        env = os.environ.get(f"CF_QUOTA_{bucket.upper()}")
        out[bucket] = int(env) if env else default
    return out


def quota_day(now: datetime | None = None) -> str:
    """The quota day (Pacific date, ISO) that ``now`` (default: the current time) falls in."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(RESET_TZ).date().isoformat()


def _used(store: Store, day: str) -> dict[str, int]:
    rows = store.query("SELECT bucket, SUM(units) AS u FROM quota WHERE day = ? GROUP BY bucket", (day,))
    return {r["bucket"]: int(r["u"]) for r in rows}


def _n(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def _over(store: Store, need: dict[str, int], day: str, what: str) -> QuotaExceeded | None:
    used, lim = _used(store, day), limits()
    for bucket, units in need.items():
        limit = lim.get(bucket, DEFAULT_LIMITS["default"])
        u = used.get(bucket, 0)
        if u + units > limit:
            return QuotaExceeded(
                f"quota: {what} needs {_n(units)} units of the {bucket} bucket, {_n(u)} of {_n(limit)} "
                f"already used on {day} (Pacific); stopped before calling the API. "
                f"The quota resets at midnight Pacific time.")
    return None


def _need(plan: dict[str, int]) -> dict[str, int]:
    need: dict[str, int] = defaultdict(int)
    for method, calls in plan.items():
        bucket, units = cost(method)
        need[bucket] += units * calls
    return dict(need)


def check(store: Store, plan: dict[str, int], *, now: datetime | None = None) -> None:
    """Raise ``QuotaExceeded`` if ``plan`` (method → number of calls) does not fit today. Charges nothing."""
    err = _over(store, _need(plan), quota_day(now), "this run")
    if err:
        raise err


def charge(store: Store, method: str, *, calls: int = 1, now: datetime | None = None) -> int:
    """Record ``calls`` calls of ``method`` for today and return their units.

    Raises ``QuotaExceeded`` (recording nothing) when they would cross the bucket's limit.
    """
    bucket, unit = cost(method)
    units = unit * calls
    day = quota_day(now)
    c = store.conn
    c.execute("BEGIN IMMEDIATE")
    try:
        err = _over(store, {bucket: units}, day, f"{calls} × {method}" if calls > 1 else method)
        if err:
            raise err
        c.execute(
            "INSERT INTO quota (day, bucket, method, calls, units) VALUES (?, ?, ?, ?, ?) "
            "ON CONFLICT (day, method) DO UPDATE SET calls = calls + excluded.calls, "
            "units = units + excluded.units",
            (day, bucket, method, calls, units))
    except BaseException:
        c.rollback()
        raise
    c.commit()
    return units


def usage(store: Store, *, day: str | None = None, now: datetime | None = None) -> Usage:
    """Usage for ``day`` (ISO date) or the current quota day: every bucket, and every method called."""
    d = day or quota_day(now)
    used = _used(store, d)
    buckets = [BucketUsage(b, lim, used.get(b, 0), max(lim - used.get(b, 0), 0))
               for b, lim in limits().items()]
    rows = store.query("SELECT method, calls, units FROM quota WHERE day = ? ORDER BY units DESC, method",
                       (d,))
    return Usage(d, buckets, [MethodUsage(**r) for r in rows])
