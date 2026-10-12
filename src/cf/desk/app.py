"""Desk: the Author's window over the Editor's repo files (ADR 0005). FastAPI app factory."""

from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cf.desk import catalog, gitread

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

    return app


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
