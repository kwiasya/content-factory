"""Desk media streaming: renders, overlays, sources and proxies served with HTTP Range, raw camera files never.

Paths are relative to the footage root. Only these subtrees are served; everything else, `raw/` included, is 404:
`videos/<slug>/{renders,overlays,sources}/**`, `<walk>/proxy/*`, `<walk>/reels/<reel>/**`,
`references/<watchlist>/<id>/proxy.mp4`.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from cf.desk import paths

VIDEO_SUBTREES = {"renders", "overlays", "sources"}
NOT_WALKS = {"videos", "references", "channels"}


def _allowlisted(parts: tuple[str, ...]) -> bool:
    if "raw" in parts:
        return False
    if len(parts) >= 4 and parts[0] == "videos" and parts[2] in VIDEO_SUBTREES:
        return True
    if len(parts) == 4 and parts[0] == "references" and parts[3] == "proxy.mp4":
        return True
    if parts[0] in NOT_WALKS:
        return False
    if len(parts) == 3 and parts[1] == "proxy":
        return True
    return len(parts) >= 4 and parts[1] == "reels"


def resolve(footage: Path, rel: str) -> Path | None:
    """The file a media path names, or None when it is outside the allowlist, missing or escapes the root."""
    parts = paths.plain_parts(rel)
    if parts is None or not _allowlisted(parts):
        return None
    target = paths.contained(footage, rel)
    return target if target is not None and target.is_file() else None


def router(footage_root: Path) -> APIRouter:
    footage = Path(footage_root)
    api = APIRouter()

    @api.get("/api/media")
    def get_media(path: str) -> FileResponse:
        target = resolve(footage, path)
        if target is None:
            raise HTTPException(404, "not a served media file")
        return FileResponse(target)

    return api
