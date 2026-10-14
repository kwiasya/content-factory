"""API quota accounting: the YouTube Data API's daily buckets and the Instagram Graph API's hourly one.

Every Data API call is charged here *before* it is made: ``charge`` adds the
method's units to today's row in ``quota`` or raises ``QuotaExceeded`` when the
call would take its bucket past the daily limit. Google's buckets (2026,
developers.google.com/youtube/v3/determine_quota_cost): ``search.list`` has its
own bucket of 100 calls a day at 1 unit each; all other methods share 10 000
units a day. Limits can be raised for a project with more quota through
``CF_QUOTA_DEFAULT`` / ``CF_QUOTA_SEARCH``. The quota day follows Google's reset
at midnight Pacific time. ``check`` tests a run's whole plan up front.

Hourly buckets (``HOURLY_LIMITS``) count calls over a rolling 60 minutes, one
``rate`` row per minute and method: the Instagram Graph API allows about 200
calls an hour per user (ADR 0010), but Meta's header reported 51 % after 62
calls on the live account (2026-10-12), so the default limit is 100;
``CF_QUOTA_INSTAGRAM`` overrides it. Meta also
reports its own count in the ``X-Business-Use-Case-Usage`` / ``X-App-Usage``
headers: ``record_pressure`` keeps the last share seen, and from ``STOP_PCT`` on
every call of the bucket is refused until the cool-down (Meta's
``estimated_time_to_regain_access``, at least ``PAUSE_MINUTES``) has passed.
"""

from __future__ import annotations

import os
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from cf.research.store import Store, now_iso

DEFAULT_LIMITS = {"default": 10_000, "search": 100}
HOURLY_LIMITS = {"instagram": 100}  # calls in any 60 minutes
STOP_PCT = 90       # Meta's reported usage share (percent) from which the bucket pauses
PAUSE_MINUTES = 15  # the least pause after such a report
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
    # Instagram Graph API (cf.research.instagram): every call is one call of the hourly bucket
    "ig.account": ("instagram", 1),
    "ig.business_discovery": ("instagram", 1),
    "ig.media": ("instagram", 1),
    "ig.insights": ("instagram", 1),
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
    window: str = "day"  # day: the Pacific quota day; hour: the last 60 minutes


@dataclass(frozen=True)
class Pressure:
    """The last usage share Meta reported for a bucket, and until when the bucket pauses (None: it does not)."""
    bucket: str
    seen_at: str
    pct: int
    regain_minutes: int
    paused_until: str | None


@dataclass(frozen=True)
class Usage:
    day: str
    buckets: list[BucketUsage] = field(default_factory=list)
    by_method: list[MethodUsage] = field(default_factory=list)
    hourly_by_method: list[MethodUsage] = field(default_factory=list)  # hourly buckets, last 60 minutes
    pressure: list[Pressure] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def cost(method: str) -> tuple[str, int]:
    """``(bucket, units)`` one call of ``method`` (e.g. ``videos.list``) costs."""
    return COSTS.get(method, ("default", 1))


def limits() -> dict[str, int]:
    """Limit per bucket (daily, then hourly), with ``CF_QUOTA_<BUCKET>`` overrides."""
    out = {}
    for bucket, default in {**DEFAULT_LIMITS, **HOURLY_LIMITS}.items():
        env = os.environ.get(f"CF_QUOTA_{bucket.upper()}")
        out[bucket] = int(env) if env else default
    return out


def window(bucket: str) -> str:
    """``hour`` for a bucket counted over the last 60 minutes, else ``day``."""
    return "hour" if bucket in HOURLY_LIMITS else "day"


def minute_key(now: datetime | None = None) -> str:
    """The UTC minute ``now`` falls in, as ``rate.minute`` stores it: ``2026-10-12T14:37Z``."""
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def _hour_start(now: datetime | None) -> str:
    """The oldest minute key inside the rolling hour that ends at ``now``."""
    return minute_key((now or datetime.now(timezone.utc)) - timedelta(minutes=59))


def quota_day(now: datetime | None = None) -> str:
    """The quota day (Pacific date, ISO) that ``now`` (default: the current time) falls in."""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(RESET_TZ).date().isoformat()


def _used(store: Store, day: str, now: datetime | None = None) -> dict[str, int]:
    """Units used per bucket: daily buckets on ``day``, hourly ones in the 60 minutes up to ``now``."""
    rows = store.query("SELECT bucket, SUM(units) AS u FROM quota WHERE day = ? GROUP BY bucket", (day,))
    out = {r["bucket"]: int(r["u"]) for r in rows}
    rows = store.query("SELECT bucket, SUM(calls) AS u FROM rate WHERE minute >= ? GROUP BY bucket",
                       (_hour_start(now),))
    out.update({r["bucket"]: int(r["u"]) for r in rows})
    return out


def pressure(store: Store, bucket: str, *, now: datetime | None = None) -> Pressure | None:
    """The last usage share Meta reported for ``bucket`` (None: never), with its pause."""
    r = store.one("SELECT * FROM rate_pressure WHERE bucket = ?", (bucket,))
    if r is None:
        return None
    seen = datetime.strptime(r["seen_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    until = None
    if r["pct"] >= STOP_PCT:
        end = seen + timedelta(minutes=max(int(r["regain_minutes"]), PAUSE_MINUTES))
        if end > (now or datetime.now(timezone.utc)):
            until = now_iso(end)
    return Pressure(bucket, r["seen_at"], int(r["pct"]), int(r["regain_minutes"]), until)


def record_pressure(store: Store, bucket: str, pct: int, regain_minutes: int = 0, *,
                    now: datetime | None = None) -> None:
    """Keep the usage share (0-100) Meta just reported for ``bucket`` and its time to regain access.

    Meta counts some calls apart (Business Discovery and the own account's media report different
    shares), so a lower share within ``PAUSE_MINUTES`` of a higher one does not replace it."""
    now = now or datetime.now(timezone.utc)
    old = store.one("SELECT seen_at, pct, regain_minutes FROM rate_pressure WHERE bucket = ?", (bucket,))
    if old is not None and old["pct"] > pct:
        seen = datetime.strptime(old["seen_at"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        if now - seen < timedelta(minutes=PAUSE_MINUTES):
            return
    with store.transaction() as c:
        c.execute("INSERT INTO rate_pressure (bucket, seen_at, pct, regain_minutes) VALUES (?, ?, ?, ?) "
                  "ON CONFLICT (bucket) DO UPDATE SET seen_at = excluded.seen_at, pct = excluded.pct, "
                  "regain_minutes = excluded.regain_minutes",
                  (bucket, now_iso(now), int(pct), int(regain_minutes)))


def _n(x: int) -> str:
    return f"{x:,}".replace(",", " ")


def _over(store: Store, need: dict[str, int], day: str, what: str,
          now: datetime | None = None) -> QuotaExceeded | None:
    used, lim = _used(store, day, now), limits()
    for bucket, units in need.items():
        limit = lim.get(bucket, DEFAULT_LIMITS["default"])
        u = used.get(bucket, 0)
        if window(bucket) == "hour":
            p = pressure(store, bucket, now=now) if units else None
            if p is not None and p.paused_until:
                return QuotaExceeded(
                    f"quota: Meta reported {p.pct}% of the {bucket} rate limit used at {p.seen_at}; {what} "
                    f"waits until {p.paused_until} (UTC). Stopped before calling the API.")
            if u + units > limit:
                return QuotaExceeded(
                    f"quota: {what} needs {_n(units)} calls of the {bucket} bucket, {_n(u)} of {_n(limit)} "
                    f"already made in the last 60 minutes; stopped before calling the API. "
                    f"Calls leave the window one hour after they were made.")
            continue
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
    err = _over(store, _need(plan), quota_day(now), "this run", now)
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
        err = _over(store, {bucket: units}, day, f"{calls} × {method}" if calls > 1 else method, now)
        if err:
            raise err
        if window(bucket) == "hour":
            c.execute("INSERT INTO rate (minute, bucket, method, calls) VALUES (?, ?, ?, ?) "
                      "ON CONFLICT (minute, method) DO UPDATE SET calls = calls + excluded.calls",
                      (minute_key(now), bucket, method, units))
        else:
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
    """Usage for ``day`` (ISO date) or the current quota day: every bucket, and every method called.
    Hourly buckets always report the 60 minutes up to ``now``."""
    d = day or quota_day(now)
    used = _used(store, d, now)
    buckets = [BucketUsage(b, lim, used.get(b, 0), max(lim - used.get(b, 0), 0), window(b))
               for b, lim in limits().items()]
    rows = store.query("SELECT method, calls, units FROM quota WHERE day = ? ORDER BY units DESC, method",
                       (d,))
    hourly = store.query("SELECT method, SUM(calls) AS calls, SUM(calls) AS units FROM rate WHERE minute >= ? "
                         "GROUP BY method ORDER BY calls DESC, method", (_hour_start(now),))
    press = [p for p in (pressure(store, b, now=now) for b in HOURLY_LIMITS) if p is not None]
    return Usage(d, buckets, [MethodUsage(**r) for r in rows], [MethodUsage(**r) for r in hourly], press)
