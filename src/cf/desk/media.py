"""Desk media streaming: renders, overlays, sources and proxies served with HTTP Range, raw camera files never.

Paths are relative to the footage root. Only these subtrees are served; everything else, `raw/` included, is 404:
`videos/<slug>/{renders,overlays,sources}/**`, `<walk>/proxy/*`, `<walk>/reels/<reel>/**`,
`references/<watchlist>/<id>/proxy.mp4`, the Library cache `library/<pack>/{previews,keyed,converted,png,sheets}/*`
and, from a registered Pack's own folder, `packs/<pack id>/<path in the Pack>` (media suffixes only, ADR 0007).
"""

from __future__ import annotations

import mimetypes
from collections.abc import Callable, Mapping
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import FileResponse

from cf.desk import paths
from cf.desk.problems import Problem
from cf.desk.videofolders import NOT_WALKS
from cf.library.scan import AUDIO, FONT, IMAGE, VIDEO

VIDEO_SUBTREES = {"renders", "overlays", "sources"}
CACHE_SUBTREES = {"previews", "keyed", "converted", "png", "sheets"}
MEDIA_SUFFIXES = frozenset("." + e for e in AUDIO | VIDEO | IMAGE | FONT)
CONTENT_TYPES = {".jfif": "image/jpeg", ".ttf": "font/ttf", ".otf": "font/otf", ".webm": "video/webm",
                 ".avif": "image/avif", ".m4a": "audio/mp4", ".webp": "image/webp", ".mkv": "video/x-matroska",
                 ".flac": "audio/flac", ".aif": "audio/aiff", ".aiff": "audio/aiff", ".m4v": "video/mp4"}


def _allowlisted(parts: tuple[str, ...]) -> bool:
    if "raw" in parts:
        return False
    if len(parts) >= 4 and parts[0] == "videos" and parts[2] in VIDEO_SUBTREES:
        return True
    if len(parts) == 4 and parts[0] == "references" and parts[3] == "proxy.mp4":
        return True
    if len(parts) == 4 and parts[0] == "library" and parts[2] in CACHE_SUBTREES:
        return Path(parts[3]).suffix.lower() in MEDIA_SUFFIXES
    if parts[0] in NOT_WALKS:
        return False
    if len(parts) == 3 and parts[1] == "proxy":
        return True
    return len(parts) >= 4 and parts[1] == "reels"


def _pack_file(parts: tuple[str, ...], pack_roots: Mapping[str, Path]) -> Path | None:
    if len(parts) < 3 or Path(parts[-1]).suffix.lower() not in MEDIA_SUFFIXES:
        return None
    root = pack_roots.get(parts[1])
    if root is None:
        return None
    target = paths.contained(root, "/".join(parts[2:]))
    return target if target is not None and target.is_file() else None


def resolve(footage: Path, rel: str, pack_roots: Mapping[str, Path] | None = None) -> Path | None:
    """The file a media path names, or None when it is outside the allowlist, missing or escapes its root."""
    parts = paths.plain_parts(rel)
    if parts is None:
        return None
    if parts[0] == "packs":
        return _pack_file(parts, pack_roots or {})
    if not _allowlisted(parts):
        return None
    target = paths.contained(footage, rel)
    return target if target is not None and target.is_file() else None


def content_type(path: Path) -> str | None:
    return CONTENT_TYPES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0]


def router(footage_root: Path, pack_roots: Callable[[], Mapping[str, Path]] = dict) -> APIRouter:
    footage = Path(footage_root)
    api = APIRouter()

    @api.get("/api/media")
    def get_media(path: str) -> FileResponse:
        roots = pack_roots() if path.startswith("packs/") else {}
        target = resolve(footage, path, roots)
        if target is None:
            raise Problem(404, "media_not_found", "not a served media file", path=path)
        return FileResponse(target, media_type=content_type(target))

    return api
