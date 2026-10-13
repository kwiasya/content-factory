"""Desk Library API: Packs, Asset cards, the Author's fields, refs for the editor, and "Show in Finder".

The Library is loaded per request from the index files and the store (read-only; writes go through
`storeuse.writing`). With no factory.db, or one at another schema version, there are no Packs and every Asset
route is 404. "Show in Finder" runs `/usr/bin/open -R`, the only process Desk launches (ADR 0007).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from cf import library
from cf.desk import storeuse
from cf.desk.problems import Problem, body as problem_body
from cf.library import CATEGORIES, RIGHTS, LibraryError, RefError, card
from cf.library.index import index_path, read_index

STORE_ABSENT = ("db_missing", "db_schema")
STATUS = {"asset_not_found": 404, "ref_not_found": 404, "pack_not_found": 404, "ref_name_taken": 409}
AUTHOR_FIELDS = ("caption", "tags", "rights", "name")
MAX_LIMIT = 1000


_indexed: dict[Path, tuple[int, frozenset[str]]] = {}


def _indexed_paths(footage: Path, pack_id: str) -> frozenset[str]:
    p = index_path(footage, pack_id)
    try:
        mtime = p.stat().st_mtime_ns
    except OSError:
        return frozenset()
    hit = _indexed.get(p)
    if hit is None or hit[0] != mtime:
        data = read_index(footage, pack_id) or {}
        hit = (mtime, frozenset(v["path"] for a in data.get("assets", []) for v in a.get("variants", [])))
        _indexed[p] = hit
    return hit[1]


def pack_files(db_path: Path, footage: Path) -> dict[str, tuple[Path, frozenset[str]]]:
    """Each registered Pack's root and the Pack-relative paths its index lists (what `/api/media` may serve)."""
    try:
        with storeuse.reading(db_path) as s:
            packs = library.list_packs(s)
    except Problem as exc:
        if exc.code in STORE_ABSENT:
            return {}
        raise
    return {p.id: (p.root, _indexed_paths(footage, p.id)) for p in packs}


def load(db_path: Path, footage: Path) -> library.Library:
    try:
        with storeuse.reading(db_path) as s:
            return library.load(footage, s)
    except Problem as exc:
        if exc.code in STORE_ABSENT:
            return library.load(footage, None)
        raise


def problem(exc: LibraryError) -> Problem:
    return Problem(STATUS.get(exc.code, 422), exc.code, str(exc), **exc.params)


class RefCheck(BaseModel):
    refs: list[str] = Field(max_length=200)


def router(db_path: Path, footage_root: Path) -> APIRouter:
    db = Path(db_path)
    footage = Path(footage_root)
    api = APIRouter()

    def asset_or_404(lib: library.Library, asset_id: str) -> library.Asset:
        a = lib.get(asset_id)
        if a is None:
            raise Problem(404, "asset_not_found", f"no Asset {asset_id!r}", id=asset_id)
        return a

    @api.get("/api/library")
    def get_library() -> dict:
        lib = load(db, footage)
        packs = []
        for view in lib.packs():
            mine = [a for a in lib.assets if a.pack == view.info.id]
            by_cat: dict[str, int] = {}
            for a in mine:
                by_cat[a.category] = by_cat.get(a.category, 0) + 1
            packs.append({"id": view.info.id, "root": str(view.info.root), "indexed_at": view.indexed_at,
                          "index_missing": view.index_missing, "assets": len(mine),
                          "by_category": {c: by_cat[c] for c in CATEGORIES if c in by_cat},
                          "fallback": len(view.report.get("fallback") or {})})
        return {"packs": packs, "categories": list(CATEGORIES), "rights": list(RIGHTS)}

    @api.get("/api/library/assets")
    def get_assets(pack: str | None = None, category: str | None = None, tags: str = "", q: str = "",
                   rights: str | None = None, limit: int = 200, offset: int = 0) -> dict:
        lib = load(db, footage)
        for param, value, ok in (("category", category, category is None or category in CATEGORIES),
                                 ("rights", rights, rights is None or rights in RIGHTS),
                                 ("pack", pack, pack is None or lib.pack(pack) is not None)):
            if not ok:
                raise Problem(422, "library_query_invalid", f"unknown {param} {value!r}", param=param, value=value)
        wanted = [t.strip() for t in tags.split(",") if t.strip()]
        found = lib.query(pack=pack, category=category, tags=wanted, text=q, rights=rights)
        limit = max(1, min(limit, MAX_LIMIT))
        offset = max(0, offset)
        facets = lib.tag_counts(found)
        active = {t.lower() for t in wanted}
        facets.sort(key=lambda r: r["tag"].lower() not in active)
        return {"assets": [card(a, full=False) for a in found[offset:offset + limit]], "total": len(found),
                "tags": facets[:50]}

    @api.get("/api/library/assets/{asset_id}")
    def get_asset(asset_id: str) -> dict:
        return {"asset": card(asset_or_404(load(db, footage), asset_id))}

    @api.put("/api/library/assets/{asset_id}/author")
    def put_author(asset_id: str, payload: dict[str, Any] = Body(...)) -> dict:
        asset_or_404(load(db, footage), asset_id)
        unknown = sorted(set(payload) - set(AUTHOR_FIELDS))
        if unknown:
            raise Problem(422, "request_invalid", f"unknown fields: {', '.join(unknown)}", fields=", ".join(unknown))
        fields = {k: payload[k] for k in AUTHOR_FIELDS if k in payload}
        try:
            with storeuse.writing(db) as s:
                fresh = library.set_author(s, library.load(footage, s), asset_id, **fields)
        except LibraryError as exc:
            raise problem(exc) from None
        return {"asset": card(fresh)}

    @api.get("/api/library/refs/resolve", response_model=None)
    def resolve_ref(ref: str) -> dict | JSONResponse:
        lib = load(db, footage)
        try:
            hit = lib.lookup(ref)
        except RefError as exc:
            raise problem(exc) from None
        if hit is None:
            return JSONResponse(status_code=404, content=problem_body(
                "ref_not_found", f"no Asset {ref}", {"ref": ref},
                suggestions=[card(a, full=False) for a in lib.nearest(ref)]))
        a, alias = hit
        return {"ref": ref, "canonical": a.ref, "alias": alias, "asset": card(a)}

    @api.post("/api/library/refs/check")
    def check_refs(body: RefCheck) -> dict:
        lib = load(db, footage)
        out: dict[str, dict] = {}
        for ref, hit in lib.check(body.refs).items():
            if isinstance(hit, library.Asset):
                out[ref] = {"ok": True, "id": hit.id, "canonical": hit.ref}
            else:
                out[ref] = {"ok": False, "suggestions": [a.ref for a in hit]}
        return {"refs": out}

    @api.get("/api/library/refs/suggest")
    def suggest_refs(q: str = "", limit: int = 20) -> dict:
        lib = load(db, footage)
        return {"suggestions": [card(a, full=False) for a in lib.suggest(q, max(1, min(limit, 100)))]}

    @api.get("/api/library/tags")
    def get_tags(q: str = "", limit: int = 20) -> dict:
        q = q.strip().lower()
        rows = [r for r in load(db, footage).tag_counts() if r["tag"].lower().startswith(q)]
        return {"tags": rows[:max(1, min(limit, 200))]}

    @api.post("/api/library/assets/{asset_id}/reveal")
    def reveal(asset_id: str) -> dict:
        a = asset_or_404(load(db, footage), asset_id)
        if not a.path.exists():
            raise Problem(404, "asset_not_found", f"the file of {a.ref} is not in its Pack", id=asset_id)
        if sys.platform != "darwin":
            raise Problem(409, "reveal_unavailable", "Show in Finder works on macOS only", path=str(a.path))
        subprocess.run(["/usr/bin/open", "-R", str(a.path)], check=False, timeout=10)
        return {"path": str(a.path)}

    return api
