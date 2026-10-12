"""Desk: the Author's window over the Editor's repo files (ADR 0005). FastAPI app factory."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI

from cf.desk import catalog, gitread

WEB_DIST = Path(__file__).resolve().parents[3] / "web" / "dist"


def create_app(repo: Path, *, footage_root: Path, db_path: Path, web_dist: Path = WEB_DIST,
               token: str | None = None) -> FastAPI:
    repo = Path(repo).resolve()
    app = FastAPI(title="Desk", docs_url=None, redoc_url=None, openapi_url=None)

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

    return app
