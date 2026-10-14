"""The feed of a Watchlist: its Reference with Outlier score, filtered and ordered.

Views, likes and comments come from each video's latest snapshot that has views (the latest one
when none has); the Outlier score is computed at query time by ``outlier`` and never stored.

A Watchlist's Reference are its channels' videos, its search hits and the
References the Author picked by hand (``watchlist_pick``: shown whatever their
age, also when their owner is unknown). Each row carries its ``platform``; an
Instagram row's title is its caption's first line and its link the permalink.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone

from cf.research import outlier
from cf.research.kinds import KINDS
from cf.research import watchlist as watchlists
from cf.research.store import PLATFORMS, Store, now_iso
from cf.research.watchlist import WatchlistError

DEFAULT_LOOKBACK_DAYS = 30
DEFAULT_LIMIT = 50


@dataclass(frozen=True)
class FeedRow:
    """One Reference as the feed shows it."""
    external_id: str
    date: str | None
    outlier: float | None
    views: int | None
    title: str | None
    handle: str | None
    url: str | None
    analyzed: bool  # its card has the analysis section; a measured-only card still needs analysis
    kind: str | None
    duration_s: float | None
    published_at: str | None
    channel_title: str | None
    likes: int | None = None
    comments: int | None = None
    own: bool = False
    candidate: bool = False  # found by a search query; its channel is not a Reference channel of the Watchlist
    platform: str = "youtube"
    pick: bool = False  # the Author picked it into the Watchlist by hand
    outlier_basis: str | None = None  # views, or likes for an Instagram reel without views

    def to_dict(self) -> dict:
        return asdict(self)


_SELECT = """
SELECT v.id, v.external_id, v.platform, v.title, v.url, v.kind, v.duration_s, v.published_at, v.own,
       c.handle, c.title AS channel_title,
       EXISTS (SELECT 1 FROM card WHERE card.video_id = v.id AND card.analysis IS NOT NULL) AS analyzed,
       s.views, s.likes, s.comments
FROM video v
LEFT JOIN channel c ON c.id = v.channel_id
LEFT JOIN snapshot s ON s.id = (SELECT id FROM snapshot WHERE video_id = v.id
                                ORDER BY views IS NULL, taken_at DESC LIMIT 1)
"""


def _row(r: dict, outlier: float | None, candidate: bool = False, pick: bool = False,
         basis: str | None = None) -> FeedRow:
    return FeedRow(
        external_id=r["external_id"], date=(r["published_at"] or "")[:10] or None, outlier=outlier,
        views=r["views"], title=r["title"], handle=r["handle"], url=r["url"], analyzed=bool(r["analyzed"]),
        kind=r["kind"], duration_s=r["duration_s"], published_at=r["published_at"],
        channel_title=r["channel_title"], likes=r["likes"], comments=r["comments"], own=bool(r["own"]),
        candidate=candidate, platform=r["platform"], pick=pick, outlier_basis=basis)


def reference(store: Store, external_id: str, platform: str | None = None) -> FeedRow | None:
    """One Reference by YouTube video id or Instagram shortcode (``platform`` narrows it; YouTube wins
    a tie), as a feed row; None when the store does not have it."""
    r = store.one(_SELECT + " WHERE v.external_id = :ext AND (:pf IS NULL OR v.platform = :pf) "
                  "ORDER BY v.platform = 'youtube' DESC LIMIT 1", {"ext": external_id, "pf": platform})
    return None if r is None else _row(r, None)


_MEMBER = "v.channel_id IN (SELECT channel_id FROM watchlist_channel WHERE watchlist_id = :wid)"
_PICK = "v.id IN (SELECT video_id FROM watchlist_pick WHERE watchlist_id = :wid)"
# Videos of a Watchlist: those of its Reference channels, those its search queries found, the Author's picks.
_IN_WATCHLIST = (f"({_MEMBER} OR v.id IN (SELECT video_id FROM search_hit WHERE watchlist_id = :wid) "
                 f"OR {_PICK})")


def feed(store: Store, name: str, *, lookback_days: float = DEFAULT_LOOKBACK_DAYS,
         min_outlier: float | None = None, min_views: int | None = None, kind: str | None = None,
         max_duration_s: float | None = None, limit: int | None = DEFAULT_LIMIT, platform: str | None = None,
         now: datetime | None = None) -> list[FeedRow]:
    """The Watchlist's Reference published in the last ``lookback_days``, best first.

    Order: Outlier score descending, then views descending; Reference without a
    score come after every scored one. ``min_outlier`` drops unscored rows,
    ``min_views`` rows without views, ``max_duration_s`` rows of unknown length (Instagram reels
    have no length from the API: their limit is Instagram's own). ``platform`` keeps one Platform.
    The Author's picks show whatever their publish date.
    """
    w = watchlists.row(store, name)
    if kind is not None and kind not in KINDS:
        raise WatchlistError(f"kind must be one of {', '.join(KINDS)}, got {kind!r}")
    if platform is not None and platform not in PLATFORMS:
        raise WatchlistError(f"platform must be one of {', '.join(PLATFORMS)}, got {platform!r}")
    now = now or datetime.now(timezone.utc)
    since = now_iso(now - timedelta(days=lookback_days))
    where = [_IN_WATCHLIST, f"(v.published_at >= :since OR {_PICK})"]
    params: dict = {"wid": w["id"], "since": since}
    if platform is not None:
        where.append("v.platform = :platform")
        params["platform"] = platform
    if kind is not None:
        where.append("v.kind = :kind")
        params["kind"] = kind
    if max_duration_s is not None:
        where.append("v.duration_s <= :maxdur")
        params["maxdur"] = max_duration_s
    rows = store.query(_SELECT.replace("SELECT ", f"SELECT {_MEMBER} AS member, {_PICK} AS pick, ", 1)
                       + " WHERE " + " AND ".join(where), params)
    if min_views is not None:
        rows = [r for r in rows if r["views"] is not None and r["views"] >= min_views]
    scored = outlier.detailed(store, [r["id"] for r in rows], now=now)
    out = [_row(r, scored[r["id"]].value, candidate=not r["member"] and not r["pick"], pick=bool(r["pick"]),
                basis=scored[r["id"]].basis) for r in rows]
    if min_outlier is not None:
        out = [r for r in out if r.outlier is not None and r.outlier >= min_outlier]
    out.sort(key=lambda r: (r.published_at or "", r.external_id), reverse=True)  # newest first on ties
    out.sort(key=lambda r: (r.outlier is None, -(r.outlier or 0), r.views is None, -(r.views or 0)))
    return out[:limit] if limit is not None else out


# --- report -----------------------------------------------------------------

def _plural(n: int, one: str, few: str, many: str) -> str:
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _decimal(x: float) -> str:
    s = f"{x:.1f}".replace(".", ",")
    return s[:-2] if s.endswith(",0") else s


def views_text(views: int | None) -> str:
    """``1,2 млн просмотров``, ``18,4 тыс. просмотров``, ``3 просмотра``; ``— просмотров`` when unknown."""
    if views is None:
        return "— просмотров"
    if views >= 1_000_000:
        return f"{_decimal(views / 1_000_000)} млн просмотров"
    if views >= 1_000:
        return f"{_decimal(views / 1_000)} тыс. просмотров"
    return f"{views} {_plural(views, 'просмотр', 'просмотра', 'просмотров')}"


def outlier_text(score: float | None) -> str:
    """``5,0x`` (one decimal, decimal comma); ``—`` without a score."""
    return "—" if score is None else f"{score:.1f}".replace(".", ",") + "x"


PLATFORM_MARKS = {"instagram": "Instagram"}


def report_line(n: int, row: FeedRow) -> str:
    """One feed row in the Sandcastles report shape: number, outlier, views, date, title, handle, link,
    then ``по лайкам`` (an Instagram score from likes), ``без разбора`` (no analysis yet, measured or
    not), ``кандидат``, ``от автора`` (picked by the Author) and the Platform when it is not YouTube."""
    title = " ".join((row.title or "без названия").split())
    who = row.handle or row.channel_title or ("владелец неизвестен" if row.platform == "instagram" else "без хэндла")
    views = views_text(row.views)
    if row.views is None and row.likes is not None and row.platform == "instagram":
        views += f" ({row.likes:,} лайков)".replace(",", " ")
    parts = [f"{n}. **{outlier_text(row.outlier)}**", views, row.date or "—", f"«{title}»", who, row.url or "—"]
    if row.outlier is not None and row.outlier_basis == "likes":
        parts.append("по лайкам")
    if not row.analyzed:
        parts.append("без разбора")
    if row.candidate:
        parts.append("кандидат")
    if row.pick:
        parts.append("от автора")
    if row.platform in PLATFORM_MARKS:
        parts.append(PLATFORM_MARKS[row.platform])
    return " · ".join(parts)


def report(name: str, rows: list[FeedRow], *, lookback_days: float, filters: str = "") -> str:
    """The feed as a Russian Markdown block: a heading line and one numbered report line per row."""
    days = _decimal(lookback_days)
    head = f"Лента {name} за {days} дн." + (f" ({filters})" if filters else "")
    if not rows:
        return head + ": ничего не нашлось."
    pending = sum(1 for r in rows if not r.analyzed)
    lines = [f"{head}: {len(rows)} Reference, без разбора {pending}.", ""]
    lines += [report_line(i, r) for i, r in enumerate(rows, 1)]
    return "\n".join(lines)
