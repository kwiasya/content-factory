"""Desk: the Author's window over the Editor's repo files (ADR 0005). FastAPI app factory."""

from __future__ import annotations

import json
import secrets
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from pydantic import BaseModel

from cf.desk import (catalog, channels, contour_api, formats_api, gitread, library_api, media, notes_api, problems,
                     research_api, search, skill_lint, skill_links, videos_api)
from cf.desk.hashed import atomic_write, digest, stale
from cf.desk.problems import Problem
from cf.research.store import person

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"


def create_app(repo: Path, *, local_root: Path, db_path: Path, shared_root: Path | None = None,
               web_dist: Path = WEB_DIST, token: str | None = None) -> FastAPI:
    repo = Path(repo).resolve()
    local_root = Path(local_root)
    shared_root = local_root if shared_root is None else Path(shared_root)
    app = FastAPI(title="Desk", docs_url=None, redoc_url=None, openapi_url=None)
    problems.install(app)

    def entry_of(path: str) -> catalog.Entry:
        entry = catalog.find(repo, path)
        if entry is None:
            raise Problem(404, "not_in_catalogue", "not in the Desk catalogue", path=path)
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
        return {"repo": str(repo), "branch": gitread.branch(repo), "local_root": str(local_root),
                "shared_root": str(shared_root), "shared_available": shared_root.is_dir(), "db_path": str(db_path),
                "person": person()}

    @app.put("/api/doc")
    def put_doc(body: DocWrite) -> dict:
        entry = entry_of(body.path)
        if not entry.editable:
            raise Problem(403, "read_only", "this document is read-only in Desk", path=entry.path)
        if entry.kind == "json":
            try:
                json.loads(body.text)
            except json.JSONDecodeError as e:
                raise Problem(422, "invalid_json", f"invalid JSON: {e}", line=e.lineno, column=e.colno) from None
        target = repo / entry.path
        data = body.text.encode("utf-8")
        conflict = stale(target.read_bytes(), body.hash)
        if conflict:
            return conflict
        atomic_write(target, data)
        return {"path": entry.path, "hash": digest(data), "git": git_state(entry.path)}

    app.include_router(research_api.router(repo))
    app.include_router(search.router(repo))
    app.include_router(skill_links.router(repo))
    app.include_router(formats_api.router(repo, local_root))
    app.include_router(skill_lint.router(repo))
    app.include_router(notes_api.router(db_path))
    app.include_router(videos_api.router(local_root, repo, db_path, shared_root))
    app.include_router(channels.router(local_root, db_path))
    app.include_router(media.router(local_root, shared_root, lambda: library_api.pack_files(db_path, shared_root)))
    app.include_router(library_api.router(db_path, shared_root))
    app.include_router(contour_api.router(db_path, shared_root, local_root))

    @app.api_route("/api/{rest:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    def api_not_found(rest: str) -> None:
        raise Problem(404, "no_endpoint", "no such API endpoint", path=rest)

    @app.get("/{rest:path}")
    def frontend(rest: str) -> Response:
        index = web_dist / "index.html"
        if not index.is_file():
            return HTMLResponse(NO_BUILD)
        dist = web_dist.resolve()
        candidate = (dist / rest).resolve()
        if rest and candidate.is_relative_to(dist) and candidate.is_file():
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
            return JSONResponse(status_code=401, content=problems.body("token_required", "Desk token required"))
        response = await call_next(request)
        if matches(query):
            response.set_cookie(COOKIE, token, httponly=True, samesite="strict")
        return response


class DocWrite(BaseModel):
    path: str
    text: str
    hash: str

