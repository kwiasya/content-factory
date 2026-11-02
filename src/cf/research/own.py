"""The Author's own Instagram account: her reels with Graph API insights over time, and a report.

``sync`` reads the account (``INSTAGRAM_USER_ID``) and pages its media, newest
first, 50 a call, with lifetime insights nested in the same call (reach, views,
saves, shares, interactions, average and total watch time). Every reel becomes
an own Reference (``video.own``) of the own channel with a ``snapshot``
(views, likes, comments) and an ``insight`` row at the sync time, so repeated
syncs build each reel's curve. A page whose nested insights fail is read again
without them and the reels' insights are asked one by one (core metrics when
the watch-time pair is refused). A reel posted before the account became a
business one has no insights at all (Meta's subcode 2108006); media come newest
first, so from the first such reel on no more insights are asked. Views of
those reels come from Business Discovery of the account itself, the only place
the Graph API gives ``view_count`` (``discovery_pages`` pages at most): their
reach, saves and shares stay unknown.

``report`` ranks the reels by views from their latest insight and gives the
medians; each reel's ``vs_median`` is its views over the median of the other
reels. ``mark`` puts the Author's labels on reels (``closeup_emotion``: opens on
her, close up, with an emotion) so the report can compare marked reels against
the rest: the hypothesis test of ``author/who-i-am.md``.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from statistics import median

from cf.research import env, ingest, instagram, quota
from cf.research.store import Store, dumps, now_iso

MARK_RE = re.compile(r"[a-z0-9_]{1,40}")
DEFAULT_PAGES = 10  # 500 media: the whole account for most; one call each
PRE_BUSINESS_SUBCODE = 2108006  # "media posted before the account became a business account"


class OwnError(Exception):
    """An own-account request that cannot be carried out; the message says why."""


@dataclass(frozen=True)
class SyncResult:
    handle: str | None
    followers: int | None
    taken_at: str
    pages: int
    reels: int
    with_insights: int
    views_from_discovery: int = 0  # reels without insights whose views came from Business Discovery
    calls: dict[str, int] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    stopped: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def _own_channel(store: Store) -> dict | None:
    uid = env.ig_user_id()
    if not uid:
        return None
    return store.one("SELECT * FROM channel WHERE platform = 'instagram' AND external_id = ?", (uid,))


def sync(store: Store, *, pages: int = DEFAULT_PAGES, discovery_pages: int = DEFAULT_PAGES,
         transport: instagram.Transport | None = None, now: datetime | None = None) -> SyncResult:
    """Read the own account and up to ``pages`` pages of its media with insights (see the module docstring).

    Raises ``QuotaExceeded`` before any call when two calls do not fit the last hour;
    a refusal midway stops the run with ``stopped`` set and what was read kept."""
    uid = env.ig_user_id()
    if not uid or (transport is None and not env.ig_token()):
        raise instagram.InstagramError(env.IG_HELP)
    now = now or datetime.now(timezone.utc)
    ts = now_iso(now)
    quota.check(store, {"ig.account": 1, "ig.media": 1})
    calls: dict[str, int] = {}

    def call(method, fn, *args, **kw):
        calls[method] = calls.get(method, 0) + 1
        return fn(store, *args, transport=transport, **kw)

    acct = call("ig.account", instagram.account, uid)
    cid = ingest.ingest_ig_account(store, acct, own=True, fetched_at=ts)
    n_pages = reels = with_ins = from_bd = 0
    errors: list[str] = []
    stopped = None
    after = None
    state = {"pre_business": False}
    no_views: set[str] = set()
    try:
        while n_pages < pages:
            try:
                page = call("ig.media", instagram.own_media, uid, after=after)
                fallback = False
            except instagram.InstagramError as exc:
                if exc.subcode != PRE_BUSINESS_SUBCODE:
                    errors.append(f"page {n_pages + 1} with insights: {exc}; read again without them")
                page = call("ig.media", instagram.own_media, uid, after=after, metrics=None)
                fallback = True
            n_pages += 1
            items = [i for i in page.get("data") or [] if i.get("media_product_type") == "REELS"]
            for item in items:
                values = ingest.insight_values(item)
                if fallback:
                    values = _insights_one(store, item["id"], call, errors, state)
                ids = ingest.ingest_ig_media(store, cid, [{**item, "view_count": values.get("views")}],
                                             fetched_at=ts, taken_at=ts)
                if not ids:
                    continue
                reels += 1
                if values.get("views") is None:
                    no_views.add(ingest.instagram_shortcode(item.get("permalink") or "") or "")
                if values:
                    with_ins += 1
                    ingest.ingest_insights(store, ids[0], values, likes=ingest._int(item.get("like_count")),
                                           comments=ingest._int(item.get("comments_count")), taken_at=ts)
            after = ((page.get("paging") or {}).get("cursors") or {}).get("after")
            if not (page.get("paging") or {}).get("next") or not after:
                break
        no_views.discard("")
        if no_views and acct.get("username"):
            from_bd = _views_from_discovery(store, uid, acct["username"], cid, no_views, discovery_pages, call, ts)
    except quota.QuotaExceeded as exc:
        stopped = str(exc)
    if state["pre_business"]:
        errors.append("older reels were posted before the account became a business account: no insights "
                      "(reach, saves, shares) for them; views from Business Discovery")
    return SyncResult(acct.get("username"), ingest._int(acct.get("followers_count")), ts, n_pages, reels,
                      with_ins, from_bd, calls, errors, stopped)


def _views_from_discovery(store: Store, uid: str, username: str, cid: int, wanted: set[str], pages: int, call,
                          ts: str) -> int:
    """Business Discovery of the own account until every reel of ``wanted`` (shortcodes) has views."""
    got, after = 0, None
    for _ in range(pages):
        p = call("ig.business_discovery", instagram.business_discovery, uid, username, after=after)
        media = (p.get("business_discovery") or {}).get("media") or {}
        items = [i for i in media.get("data") or [] if ingest.instagram_shortcode(i.get("permalink") or "") in wanted
                 and i.get("view_count") is not None]
        ingest.ingest_ig_media(store, cid, items, fetched_at=ts, taken_at=ts)
        for i in items:
            wanted.discard(ingest.instagram_shortcode(i["permalink"]))
            got += 1
        after = ((media.get("paging") or {}).get("cursors") or {}).get("after")
        if not wanted or not after or len(media.get("data") or []) < instagram.MEDIA_PAGE:
            break
    return got


def _insights_one(store: Store, media_id: str, call, errors: list[str], state: dict) -> dict[str, int]:
    """Insights of one reel: every metric, else the core set, else nothing (the error is kept). Once a
    reel answers "posted before the business account", none is asked any more (``state``)."""
    if state["pre_business"]:
        return {}
    last = ""
    for metrics in (instagram.INSIGHT_METRICS + instagram.REEL_METRICS, instagram.INSIGHT_METRICS):
        try:
            return ingest.insight_values(call("ig.insights", instagram.media_insights, media_id, metrics))
        except instagram.InstagramError as exc:
            if exc.subcode == PRE_BUSINESS_SUBCODE:
                state["pre_business"] = True
                return {}
            last = str(exc)
    errors.append(f"insights of {media_id}: {last}")
    return {}


# --- report -----------------------------------------------------------------------

@dataclass(frozen=True)
class OwnReel:
    external_id: str
    url: str | None
    date: str | None
    title: str | None
    views: int | None
    reach: int | None
    likes: int | None
    comments: int | None
    shares: int | None
    saved: int | None
    interactions: int | None
    avg_watch_s: float | None
    taken_at: str | None
    vs_median: float | None  # views over the median views of the other reels
    marks: list[str] = field(default_factory=list)
    rank: int | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class MarkGroup:
    """Reels with one mark against the rest: count and median views, reach, shares and saves."""
    mark: str
    reels: int
    others: int
    median_views: float | None
    others_median_views: float | None
    median_reach: float | None
    others_median_reach: float | None
    median_shares: float | None
    others_median_shares: float | None
    median_saved: float | None
    others_median_saved: float | None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class OwnReport:
    handle: str | None
    followers: int | None
    synced_at: str | None
    reels: list[OwnReel]
    median_views: float | None
    median_reach: float | None
    median_shares: float | None
    median_saved: float | None
    marks: list[MarkGroup] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def _med(xs: list) -> float | None:
    xs = [x for x in xs if x is not None]
    return median(xs) if xs else None


def report(store: Store, *, days: float | None = None, now: datetime | None = None) -> OwnReport:
    """The own reels ranked by views (latest insight; latest snapshot when the reel has no insight),
    with medians and the mark groups. ``days`` keeps reels published in the last N days."""
    ch = _own_channel(store) or store.one("SELECT * FROM channel WHERE platform = 'instagram' AND own = 1 "
                                          "ORDER BY fetched_at DESC LIMIT 1")
    if ch is None:
        raise OwnError("the own Instagram account is not in the store yet; run `python -m cf.research own sync`")
    params: dict = {"cid": ch["id"]}
    where = ""
    if days is not None:
        cutoff = (now or datetime.now(timezone.utc)).timestamp() - days * 86400
        params["since"] = now_iso(datetime.fromtimestamp(cutoff, timezone.utc))
        where = " AND v.published_at >= :since"
    rows = store.query(
        "SELECT v.id, v.external_id, v.url, v.published_at, v.title, v.marks, i.taken_at, "
        "COALESCE(i.views, s.views) AS views, i.reach, COALESCE(i.likes, s.likes) AS likes, "
        "COALESCE(i.comments, s.comments) AS comments, i.shares, i.saved, i.interactions, i.avg_watch_ms "
        "FROM video v "
        "LEFT JOIN insight i ON i.id = (SELECT id FROM insight WHERE video_id = v.id ORDER BY taken_at DESC LIMIT 1) "
        "LEFT JOIN snapshot s ON s.id = (SELECT id FROM snapshot WHERE video_id = v.id "
        "                                ORDER BY views IS NULL, taken_at DESC LIMIT 1) "
        f"WHERE v.platform = 'instagram' AND v.channel_id = :cid AND v.kind = 'short'{where}", params)
    rows.sort(key=lambda r: (r["views"] is None, -(r["views"] or 0), r["published_at"] or ""))
    reels = []
    for rank, r in enumerate(rows, 1):
        others = [o["views"] for o in rows if o is not r and o["views"] is not None]
        m = _med(others)
        reels.append(OwnReel(r["external_id"], r["url"], (r["published_at"] or "")[:10] or None, r["title"],
                             r["views"], r["reach"], r["likes"], r["comments"], r["shares"], r["saved"],
                             r["interactions"], None if r["avg_watch_ms"] is None else round(r["avg_watch_ms"] / 1000, 1),
                             r["taken_at"], round(r["views"] / m, 2) if m and r["views"] is not None else None,
                             json.loads(r["marks"] or "[]"), rank if r["views"] is not None else None))
    groups = []
    for mark in sorted({m for r in reels for m in r.marks}):
        a = [r for r in reels if mark in r.marks]
        b = [r for r in reels if mark not in r.marks]
        pair = [_med([getattr(r, col) for r in g]) for col in ("views", "reach", "shares", "saved") for g in (a, b)]
        groups.append(MarkGroup(mark, len(a), len(b), *pair))
    return OwnReport(ch["handle"], ch["subscriber_count"], ch["fetched_at"], reels,
                     _med([r.views for r in reels]), _med([r.reach for r in reels]),
                     _med([r.shares for r in reels]), _med([r.saved for r in reels]), groups)


def _own_video(store: Store, ref: str) -> dict:
    code = ingest.instagram_shortcode(ref) or ref.strip()
    row = store.one("SELECT v.id, v.external_id, v.marks FROM video v WHERE v.platform = 'instagram' "
                    "AND v.own = 1 AND v.external_id = ?", (code,))
    if row is None:
        raise OwnError(f"{ref!r} is not an own reel in the store (give its link or shortcode; run own sync first)")
    return row


def mark(store: Store, ref: str, label: str, *, remove: bool = False) -> list[str]:
    """Add (or with ``remove`` take off) the Author's label on one own reel; return its labels."""
    if not MARK_RE.fullmatch(label or ""):
        raise OwnError(f"mark {label!r}: use a-z, 0-9 and _, e.g. closeup_emotion")
    v = _own_video(store, ref)
    marks = [m for m in json.loads(v["marks"] or "[]") if m != label]
    if not remove:
        marks.append(label)
    with store.transaction() as c:
        c.execute("UPDATE video SET marks = ? WHERE id = ?", (dumps(sorted(marks)), v["id"]))
    return sorted(marks)
