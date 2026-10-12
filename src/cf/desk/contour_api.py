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

from cf.research import feed, watchlist
from cf.research.cli import USER_ERRORS
from cf.research.store import Store, open_store

FEED_LIMIT = 20


def _rounded(row: feed.FeedRow) -> dict:
    return {**row.to_dict(), "outlier": None if row.outlier is None else round(row.outlier, 2)}


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

    return api
