"""Desk: the Author's window over the Editor's repo files (ADR 0005). FastAPI app factory."""

from __future__ import annotations

import hashlib
import json
import os
import secrets
import stat
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from cf.desk import catalog, gitread
from cf.desk import research_api
from cf.desk import search

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"


def digest(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def create_app(repo: Path, *, footage_root: Path, db_path: Path, web_dist: Path = WEB_DIST,
               token: str | None = None) -> FastAPI:
    repo = Path(repo).resolve()
    app = FastAPI(title="Desk", docs_url=None, redoc_url=None, openapi_url=None)

    def entry_of(path: str) -> catalog.Entry:
        entry = catalog.find(repo, path)
        if entry is None:
            raise HTTPException(404, "not in the Desk catalogue")
        return entry

    def git_state(rel: str) -> str:
        return gitread.status_of(gitread.status(repo), rel)

    @app.get("/api/catalog")
    def get_catalog(all: int = 0) -> dict:
        statuses = gitread.status(repo)
        groups = []
        for listing in catalog.list_groups(repo, include_hidden=bool(all)):
            groups.append({
                "id": listing.group.id,
                "title": listing.group.title,
                "hidden": listing.group.hidden,
                "empty": listing.empty,
                "docs": [{**e.as_dict(), "git": gitread.status_of(statuses, e.path)} for e in listing.entries],
            })
        return {"groups": groups}

    @app.get("/api/doc")
    def get_doc(path: str) -> dict:
        entry = entry_of(path)
        data = (repo / entry.path).read_bytes()
        return {**entry.as_dict(), "git": git_state(entry.path), "text": data.decode("utf-8"),
                "hash": digest(data)}

    @app.get("/api/doc/diff")
    def get_diff(path: str) -> dict:
        entry = entry_of(path)
        state = git_state(entry.path)
        return {"path": entry.path, "git": state, "diff": gitread.diff(repo, entry.path, state)}

    @app.get("/api/doc/log")
    def get_log(path: str) -> dict:
        entry = entry_of(path)
        return {"path": entry.path, "entries": gitread.log(repo, entry.path)}

    @app.get("/api/meta")
    def get_meta() -> dict:
        return {"repo": str(repo), "branch": gitread.branch(repo), "footage_root": str(footage_root),
                "db_path": str(db_path)}

    @app.put("/api/doc")
    def put_doc(body: DocWrite) -> dict:
        entry = entry_of(body.path)
        if not entry.editable:
            raise HTTPException(403, "this document is read-only in Desk")
        if entry.kind == "json":
            try:
                json.loads(body.text)
            except json.JSONDecodeError as e:
                raise HTTPException(422, f"invalid JSON: {e}") from None
        target = repo / entry.path
        data = body.text.encode("utf-8")
        current = target.read_bytes()
        if digest(current) != body.hash:
            return JSONResponse(status_code=409, content={
                "detail": "the file changed on disk since it was read",
                "text": current.decode("utf-8"), "hash": digest(current)})
        atomic_write(target, data)
        return {"path": entry.path, "hash": digest(data), "git": git_state(entry.path)}

    app.include_router(research_api.router(repo))
    app.include_router(search.router(repo))

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def api_not_found(rest: str) -> None:
        raise HTTPException(404, "no such API endpoint")

    @app.get("/{rest:path}")
    def frontend(rest: str) -> Response:
        index = web_dist / "index.html"
        if not index.is_file():
            return HTMLResponse(NO_BUILD)
        root = web_dist.resolve()
        candidate = (root / rest).resolve()
        if rest and candidate.is_relative_to(root) and candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(index)

    if token:
        install_token_guard(app, token)

    return app


NO_BUILD = """<!doctype html>
<meta charset="utf-8">
<title>Desk</title>
<body style="font: 16px/1.5 system-ui, sans-serif; max-width: 40rem; margin: 4rem auto; padding: 0 1rem">
<h1>Desk API is running</h1>
<p>The web frontend is not built yet. Build it once, then reload this page:</p>
<pre>npm --prefix web install
npm --prefix web run build</pre>
<p>The API answers under <code>/api/</code>, for example <a href="/api/meta">/api/meta</a>.</p>
</body>
"""

COOKIE = "desk_token"


def install_token_guard(app: FastAPI, token: str) -> None:
    def matches(value: str | None) -> bool:
        return value is not None and secrets.compare_digest(value.encode(), token.encode())

    @app.middleware("http")
    async def guard(request: Request, call_next):
        header = request.headers.get("authorization", "")
        bearer = header[7:] if header.lower().startswith("bearer ") else None
        query = request.query_params.get("token")
        if not (matches(bearer) or matches(request.cookies.get(COOKIE)) or matches(query)):
            return JSONResponse(status_code=401, content={"detail": "Desk token required"})
        response = await call_next(request)
        if matches(query):
            response.set_cookie(COOKIE, token, httponly=True, samesite="strict")
        return response


class DocWrite(BaseModel):
    path: str
    text: str
    hash: str


def atomic_write(target: Path, data: bytes) -> None:
    mode = stat.S_IMODE(target.stat().st_mode)
    fd, tmp = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".desk", dir=target.parent)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise
