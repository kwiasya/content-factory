"""Desk research contour: Watchlists, feed, Reference cards, summaries, Ideas, Briefs, taxonomy and quota.

Every endpoint calls `cf.research` modules directly (no subprocess, nothing on the network) and opens a
Store per request through `cf.desk.storeuse`: reads never create, migrate or seed factory.db. Unknown
Watchlists, References and Ideas are 404; any other error the CLI reports as a user error is 422.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cf.desk import media, storeuse
from cf.desk.hashed import atomic_write, digest
from cf.research import card, feed, ideas, outlier, quota, summary, taxonomy
from cf.research import watchlist as watchlists
from cf.research.cli import USER_ERRORS
from cf.research.store import Store

FEED_LIMIT = 20
SUMMARY_LIMIT = 10
IDEA_MOVES = {"shortlist": ideas.shortlist, "discard": ideas.discard, "restore": ideas.restore}


class NoteIn(BaseModel):
    text: str


class BriefWrite(BaseModel):
    text: str
    hash: str


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
    def store(write: bool = False) -> Iterator[Store]:
        with (storeuse.writing if write else storeuse.reading)(db_path) as s:
            try:
                yield s
            except (*USER_ERRORS, ValueError) as e:
                raise HTTPException(422, _detail(e)) from None

    def watchlist_of(s: Store, name: str) -> watchlists.Watchlist:
        try:
            return watchlists.get(s, name)
        except watchlists.WatchlistError as e:
            raise HTTPException(404, str(e)) from None

    @api.get("/watchlists")
    def get_watchlists() -> dict:
        with store() as s:
            return {"watchlists": [w.to_dict() for w in watchlists.list_watchlists(s)]}

    @api.get("/watchlists/{name}")
    def get_watchlist(name: str) -> dict:
        with store() as s:
            w = watchlist_of(s, name)
            return {"watchlist": w.to_dict(), "channels": [c.to_dict() for c in watchlists.channels(s, name)]}

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

    def idea_of(s: Store, idea_id: int) -> ideas.Idea:
        try:
            return ideas.get(s, idea_id)
        except ideas.IdeaError as e:
            raise HTTPException(404, str(e)) from None

    def brief_file(idea: ideas.Idea) -> Path:
        if not idea.brief_path:
            raise HTTPException(404, f"Idea {idea.id} has no Brief yet; shortlist it, then run "
                                     f"python -m cf.research ideas brief {idea.id} (skill /suggest-ideas)")
        path = Path(idea.brief_path)
        root = footage.resolve()
        if not path.resolve().is_relative_to(root) or path.suffix != ".md":
            raise HTTPException(404, f"the Brief of Idea {idea.id} is not a .md file under the footage root")
        if not path.is_file():
            raise HTTPException(404, f"the Brief of Idea {idea.id} is missing on disk: {path}")
        return path

    @api.get("/ideas")
    def get_ideas(watchlist: str | None = None, status: str | None = None) -> dict:
        with store() as s:
            names = [watchlist_of(s, watchlist).name] if watchlist else \
                [w.name for w in watchlists.list_watchlists(s)]
            found = [i for n in names for i in ideas.list(s, n, status=status or None)]
            return {"ideas": [i.to_dict() for i in found], "statuses": list(ideas.STATUSES)}

    @api.post("/ideas/{idea_id}/{action}")
    def move_idea(idea_id: int, action: str) -> dict:
        move = IDEA_MOVES.get(action)
        if move is None:
            raise HTTPException(404, f"action must be one of {', '.join(IDEA_MOVES)}")
        with store(write=True) as s:
            idea_of(s, idea_id)
            return move(s, idea_id).to_dict()

    @api.put("/ideas/{idea_id}/notes")
    def add_idea_note(idea_id: int, body: NoteIn) -> dict:
        with store(write=True) as s:
            idea_of(s, idea_id)
            return ideas.note(s, idea_id, body.text).to_dict()

    @api.get("/ideas/{idea_id}/brief")
    def get_brief(idea_id: int) -> dict:
        with store() as s:
            path = brief_file(idea_of(s, idea_id))
        data = path.read_bytes()
        return {"idea": idea_id, "path": str(path), "text": data.decode("utf-8"), "hash": digest(data)}

    @api.put("/ideas/{idea_id}/brief", response_model=None)
    def put_brief(idea_id: int, body: BriefWrite) -> dict | JSONResponse:
        with store() as s:
            path = brief_file(idea_of(s, idea_id))
        current = path.read_bytes()
        if digest(current) != body.hash:
            return JSONResponse(status_code=409, content={
                "detail": "the Brief changed on disk since it was read",
                "text": current.decode("utf-8"), "hash": digest(current)})
        data = body.text.encode("utf-8")
        atomic_write(path, data)
        return {"idea": idea_id, "path": str(path), "hash": digest(data)}

    @api.get("/taxonomy")
    def get_taxonomy(kind: str | None = None, status: str | None = None) -> dict:
        with store() as s:
            vals = taxonomy.values(s, kind=kind or None, status=status or None)
            return {"values": [v.to_dict() for v in vals], "kinds": list(taxonomy.KINDS),
                    "statuses": list(taxonomy.STATUSES)}

    @api.post("/taxonomy/{kind}/{value}/{action}")
    def judge_taxonomy(kind: str, value: str, action: str) -> dict:
        if action not in ("approve", "reject"):
            raise HTTPException(404, "action must be approve or reject")
        with store(write=True) as s:
            if action == "approve":
                return taxonomy.approve(s, kind, value, root=footage).to_dict()
            return taxonomy.reject(s, kind, value).to_dict()

    @api.get("/quota")
    def get_quota() -> dict:
        with store() as s:
            return {**quota.usage(s).to_dict(), "limits": quota.limits()}

    return api
