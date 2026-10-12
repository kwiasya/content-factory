"""Desk research contour: Watchlists, feed, Reference cards, summaries, Ideas, Briefs, taxonomy and quota.

Every endpoint calls `cf.research` modules directly (no subprocess, nothing on the network) and opens a
Store per request: sqlite connections stay on the thread that made them. Unknown Watchlists, References
and Ideas are 404; any other error the CLI reports as a user error is 422.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, HTTPException

from cf.desk import media
from cf.research import card, feed, outlier, summary, taxonomy, watchlist
from cf.research.cli import USER_ERRORS
from cf.research.store import Store, open_store

FEED_LIMIT = 20
SUMMARY_LIMIT = 10


def _rounded(row: feed.FeedRow) -> dict:
    return {**row.to_dict(), "outlier": None if row.outlier is None else round(row.outlier, 2)}


def _pending(store: Store, analysis: dict | None) -> list[dict]:
    out: list[dict] = []
    for path, kind in card.category_paths():
        raw = card.field(analysis or {}, path)
        if not isinstance(raw, str):
            continue
        value = card.split_proposed(raw)[0]
        t = taxonomy.get(store, kind, value)
        if t is not None and t.status == "proposed" and {"kind": kind, "value": value} not in out:
            out.append({"kind": kind, "value": value})
    return out


def _proxy(footage: Path, external_id: str) -> str | None:
    for d in card.reference_dirs(external_id, footage):
        rel = (d / "proxy.mp4").relative_to(footage).as_posix()
        if media.resolve(footage, rel):
            return rel
    return None


def _detail(e: Exception) -> str:
    violations = getattr(e, "violations", None) or []
    return str(e) + "".join(f"\n- {v}" for v in violations)


def router(db_path: Path, footage_root: Path) -> APIRouter:
    footage = Path(footage_root)
    api = APIRouter(prefix="/api/contour")

    @contextmanager
    def store() -> Iterator[Store]:
        with open_store(db_path) as s:
            try:
                yield s
            except (*USER_ERRORS, ValueError) as e:
                raise HTTPException(422, _detail(e)) from None

    def watchlist_of(s: Store, name: str) -> watchlist.Watchlist:
        try:
            return watchlist.get(s, name)
        except watchlist.WatchlistError as e:
            raise HTTPException(404, str(e)) from None

    @api.get("/watchlists")
    def get_watchlists() -> dict:
        with store() as s:
            return {"watchlists": [w.to_dict() for w in watchlist.list_watchlists(s)]}

    @api.get("/watchlists/{name}")
    def get_watchlist(name: str) -> dict:
        with store() as s:
            w = watchlist_of(s, name)
            return {"watchlist": w.to_dict(), "channels": [c.to_dict() for c in watchlist.channels(s, name)]}

    @api.get("/watchlists/{name}/feed")
    def get_feed(name: str, days: float = feed.DEFAULT_LOOKBACK_DAYS, min_outlier: float | None = None,
                 min_views: int | None = None, kind: str | None = None, max_duration: float | None = None,
                 limit: int = FEED_LIMIT) -> dict:
        with store() as s:
            watchlist_of(s, name)
            rows = feed.feed(s, name, lookback_days=days, min_outlier=min_outlier, min_views=min_views,
                             kind=kind or None, max_duration_s=max_duration, limit=limit)
            return {"watchlist": name, "days": days, "limit": limit, "rows": [_rounded(r) for r in rows]}

    @api.get("/cards/{video_id}")
    def get_card(video_id: str) -> dict:
        with store() as s:
            try:
                v = card.video(s, video_id)
            except card.CardError as e:
                raise HTTPException(404, str(e)) from None
            c = card.load(s, v["id"])
            if c is None:
                raise HTTPException(404, f"Reference {v['external_id']} has no card yet; run "
                                         f"python -m cf.research fetch {v['external_id']} (skill /analyze-reference)")
            ref = feed.reference(s, v["external_id"])
            row = {**ref.to_dict(), "outlier": outlier.score(s, v["external_id"])} if ref else None
            if row and row["outlier"] is not None:
                row["outlier"] = round(row["outlier"], 2)
            return {"external_id": v["external_id"], "reference": row, "card": c,
                    "sections": c["measured"].get("sections") or [], "proposed": _pending(s, c["analysis"]),
                    "media": _proxy(footage, v["external_id"])}

    @api.get("/watchlists/{name}/summary/{what}")
    def get_summary(name: str, what: str, days: float = summary.DEFAULT_DAYS) -> dict:
        with store() as s:
            watchlist_of(s, name)
            return summary.summarize(s, name, what, days=days, limit=SUMMARY_LIMIT).to_dict()

    return api
