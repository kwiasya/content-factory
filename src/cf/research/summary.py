"""Hooks, formats and topics summaries of a Watchlist over a lookback window.

Each summary takes the Watchlist's Reference published in the last ``days``
(the feed's membership: its Reference channels and its search hits), keeps the
carded ones (a card with an analysis section), groups them by one category of
the analysis and ranks the groups. The rest are reported as uncarded outliers
so the Author can analyze them before trusting the summary (spec #1,
"Summaries"; Sandcastles ``/hooks-watchlist``, ``/formats-watchlist``, ``/topic``).

Weight of a group: the sum of its References' Outlier scores, an unscored
Reference counting as 1 (its channel's norm). A group of three 1x videos thus
weighs as much as one 3x video: count and overperformance both lift a group.
Groups are sorted by weight, then count, then value.

Category values carrying a leftover ``proposed:`` prefix are grouped under the
bare value; the group is flagged ``proposed``. Topics and hook formulas are free
text: they are grouped after folding case and whitespace, exact matches only.
The hooks summary has two sections: hook categories, then hook formulas.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone

from cf.research import card, feed, taxonomy
from cf.research.store import Store, now_iso
from cf.research.watchlist import get as get_watchlist

# sections whose values are free text, grouped by ``topic_key`` rather than the taxonomy
FREE_TEXT = ("topic", "hook_formula")

DEFAULT_DAYS = 14
DEFAULT_MIN_OUTLIER = 2.0
DEFAULT_EXAMPLES = 3
UNSCORED_WEIGHT = 1.0

# section kind -> path of the analysis field it groups by
SECTIONS = {
    "hooks": [("hook_category", "hook.category"), ("hook_formula", "hook.formula")],
    "formats": [("storytelling_format", "storytelling_format.category"),
                ("visual_layout", "visual_layout.category")],
    "topics": [("topic", "idea_analysis.topic")],
}


@dataclass(frozen=True)
class Example:
    """One carded Reference of a group."""
    external_id: str
    title: str | None
    outlier: float | None
    views: int | None
    url: str | None
    handle: str | None
    date: str | None
    spoken_hook: str | None
    formula: str | None
    proposed: bool = False  # this card carries the value with the proposed: prefix

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class Group:
    """References sharing one category value (or one normalized topic)."""
    value: str
    label: str | None
    proposed: bool
    count: int
    weight: float
    best_outlier: float | None
    examples: list[Example] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {**asdict(self), "weight": round(self.weight, 2),
                "best_outlier": None if self.best_outlier is None else round(self.best_outlier, 2),
                "examples": [_rounded(e.to_dict()) for e in self.examples]}


@dataclass(frozen=True)
class Section:
    kind: str  # taxonomy kind, or a free-text kind (FREE_TEXT)
    groups: list[Group]

    def to_dict(self) -> dict:
        return {"kind": self.kind, "groups": [g.to_dict() for g in self.groups]}


@dataclass(frozen=True)
class Uncarded:
    """A Reference above the threshold with no analysis yet."""
    external_id: str
    title: str | None
    outlier: float | None
    views: int | None
    url: str | None
    handle: str | None
    date: str | None
    measured: bool  # a measured card exists (fetched), only the analysis is missing

    def to_dict(self) -> dict:
        return _rounded(asdict(self))


@dataclass(frozen=True)
class Summary:
    summary: str  # hooks | formats | topics
    watchlist: str
    format_id: str
    days: float
    since: str
    references: int  # in the window
    carded: int  # with an analysis
    min_outlier: float
    sections: list[Section]
    uncarded: list[Uncarded]

    def to_dict(self) -> dict:
        return {"summary": self.summary, "watchlist": self.watchlist, "format_id": self.format_id,
                "days": self.days, "since": self.since, "references": self.references, "carded": self.carded,
                "min_outlier": self.min_outlier, "weight": "sum of Outlier scores, unscored counted as 1",
                "sections": [s.to_dict() for s in self.sections],
                "uncarded": [u.to_dict() for u in self.uncarded]}


def _rounded(d: dict) -> dict:
    return {**d, "outlier": None if d["outlier"] is None else round(d["outlier"], 2)}


def topic_key(text: str) -> str:
    """A topic or hook formula folded for grouping: lower case, whitespace collapsed."""
    return " ".join(text.split()).casefold()


def _by_outlier(r) -> tuple:
    return (r.outlier is None, -(r.outlier or 0), r.views is None, -(r.views or 0), r.external_id)


def _analyses(store: Store, external_ids: list[str]) -> dict[str, dict]:
    """``external_id -> {"analysis", "measured"}`` of the cards among ``external_ids``."""
    if not external_ids:
        return {}
    marks = ",".join("?" * len(external_ids))
    rows = store.query(f"SELECT v.external_id, c.measured, c.analysis FROM card c JOIN video v ON v.id = c.video_id "
                       f"WHERE v.external_id IN ({marks})", tuple(external_ids))
    return {r["external_id"]: {"measured": json.loads(r["measured"] or "{}"),
                               "analysis": None if r["analysis"] is None else json.loads(r["analysis"])}
            for r in rows}


def _label(store: Store, kind: str, value: str) -> str | None:
    t = taxonomy.get(store, kind, value) if kind in taxonomy.KINDS else None
    return None if t is None else t.label


def _group(store: Store, kind: str, path: str, carded: list[tuple], examples: int,
           limit: int | None) -> Section:
    buckets: dict[str, list[tuple]] = {}
    for row, c in carded:
        raw = card.field(c["analysis"], path)
        if not isinstance(raw, str) or not raw.strip():
            continue
        if kind in FREE_TEXT:
            key, proposed = topic_key(raw), False
        else:
            key, proposed = card.split_proposed(raw.strip())
        buckets.setdefault(key, []).append((row, c, proposed, raw))
    groups = []
    for key, members in buckets.items():
        members.sort(key=lambda m: _by_outlier(m[0]))
        weight = sum(UNSCORED_WEIGHT if m[0].outlier is None else m[0].outlier for m in members)
        scored = [m[0].outlier for m in members if m[0].outlier is not None]
        label = " ".join(members[0][3].split()) if kind in FREE_TEXT else _label(store, kind, key)
        exs = [Example(external_id=r.external_id, title=r.title, outlier=r.outlier, views=r.views, url=r.url,
                       handle=r.handle, date=r.date,
                       spoken_hook=card.field(c["analysis"], "hook.spoken_hook") or c["measured"].get("spoken_hook"),
                       formula=card.field(c["analysis"], "hook.formula"), proposed=p)
               for r, c, p, _ in members[:examples]]
        groups.append(Group(value=key, label=label, proposed=any(m[2] for m in members), count=len(members),
                            weight=weight, best_outlier=max(scored) if scored else None, examples=exs))
    groups.sort(key=lambda g: (-g.weight, -g.count, g.value))
    return Section(kind=kind, groups=groups[:limit] if limit is not None else groups)


def summarize(store: Store, name: str, what: str, *, days: float = DEFAULT_DAYS,
              min_outlier: float = DEFAULT_MIN_OUTLIER, limit: int | None = None,
              examples: int = DEFAULT_EXAMPLES, now: datetime | None = None) -> Summary:
    """The ``what`` summary (hooks, formats, topics) of Watchlist ``name``.

    ``limit`` caps the groups per section and the uncarded list; ``examples`` the
    examples per group (best Outlier score first, then views).
    """
    if what not in SECTIONS:
        raise ValueError(f"summary must be one of {', '.join(SECTIONS)}, got {what!r}")
    w = get_watchlist(store, name)
    now = now or datetime.now(timezone.utc)
    rows = feed.feed(store, name, lookback_days=days, limit=None, now=now)
    cards = _analyses(store, [r.external_id for r in rows])
    carded = [(r, cards[r.external_id]) for r in rows
              if r.external_id in cards and cards[r.external_id]["analysis"] is not None]
    sections = [_group(store, kind, path, carded, examples, limit) for kind, path in SECTIONS[what]]
    uncarded = [Uncarded(external_id=r.external_id, title=r.title, outlier=r.outlier, views=r.views, url=r.url,
                         handle=r.handle, date=r.date, measured=r.external_id in cards)
                for r in sorted(rows, key=_by_outlier)
                if r.outlier is not None and r.outlier >= min_outlier
                and (r.external_id not in cards or cards[r.external_id]["analysis"] is None)]
    since = now_iso(now - timedelta(days=days))
    return Summary(summary=what, watchlist=w.name, format_id=w.format_id, days=days, since=since,
                   references=len(rows), carded=len(carded), min_outlier=min_outlier, sections=sections,
                   uncarded=uncarded[:limit] if limit is not None else uncarded)


def hooks(store: Store, name: str, days: float = DEFAULT_DAYS, **kw) -> Summary:
    """Hook categories, then hook formulas, of the Watchlist's carded References; examples carry
    spoken hook and formula."""
    return summarize(store, name, "hooks", days=days, **kw)


def formats(store: Store, name: str, days: float = DEFAULT_DAYS, **kw) -> Summary:
    """Storytelling formats and visual layouts, one section each."""
    return summarize(store, name, "formats", days=days, **kw)


def topics(store: Store, name: str, days: float = DEFAULT_DAYS, **kw) -> Summary:
    """Topics (``idea_analysis.topic``), grouped after folding case and whitespace."""
    return summarize(store, name, "topics", days=days, **kw)
