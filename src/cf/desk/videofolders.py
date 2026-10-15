"""The reading side of Desk Videos: which folders are Videos, their `video.json` and their list summary.

Video folders follow ADR 0006 (`videos/<slug>/video.json`); a legacy Reel `<walk>/reels/<reel>/` is addressed as
`<walk>~<reel>`, has format `walk-reel` and a status derived from what exists in its folder.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from cf.assets import is_script_file
from cf.desk.problems import Problem

SCHEMA = "cf-video/1"
STATUSES = ("idea", "brief", "script", "recording", "edit", "review", "published")
LEGACY_SEP = "~"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
NOT_WALKS = {"videos", "references", "channels", "library", "packs"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
STAGES = ("idea", "script", "edit", "done")
STAGE_OF = {"idea": "idea", "brief": "idea", "script": "script", "recording": "script", "edit": "edit",
            "review": "edit", "published": "done"}


@dataclass(frozen=True)
class Folder:
    slug: str
    path: Path
    legacy: bool
    walk: str | None = None


def videos_dir(root: Path) -> Path:
    return root / "videos"


def list_folders(root: Path) -> list[Folder]:
    folders = []
    vdir = videos_dir(root)
    if vdir.is_dir():
        for d in sorted(vdir.iterdir()):
            if NAME.match(d.name) and (d / "video.json").is_file():
                folders.append(Folder(d.name, d, False))
    if root.is_dir():
        for walk in sorted(root.iterdir()):
            if not NAME.match(walk.name) or walk.name in NOT_WALKS or not (walk / "reels").is_dir():
                continue
            for reel in sorted((walk / "reels").iterdir()):
                if reel.is_dir() and NAME.match(reel.name):
                    folders.append(Folder(f"{walk.name}{LEGACY_SEP}{reel.name}", reel, True, walk.name))
    return folders


def find_folder(root: Path, slug: str) -> Folder:
    for folder in list_folders(root):
        if folder.slug == slug:
            return folder
    raise Problem(404, "video_not_found", "no such Video", slug=slug)


def walk_files(folder: Path) -> list[Path]:
    top = folder.resolve()
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and not any(part.startswith(".") for part in p.relative_to(folder).parts)
                  and p.resolve().is_relative_to(top))


def last_change(folder: Path) -> float:
    return max((p.stat().st_mtime for p in walk_files(folder)), default=folder.stat().st_mtime)


def iso(ts: float) -> str:
    return datetime.fromtimestamp(ts, timezone.utc).isoformat(timespec="seconds")


def legacy_status(reel: Path) -> str:
    out = reel / "out"
    if out.is_dir() and any(p.suffix.lower() in VIDEO_SUFFIXES for p in out.iterdir() if p.is_file()):
        return "review"
    overlays = reel / "overlays"
    if (reel / "cuts.json").is_file() or (overlays.is_dir() and any(overlays.iterdir())):
        return "edit"
    if any(is_script_file(p.name) and p.suffix.lower() == ".json" for p in reel.iterdir()):
        return "script"
    return "idea"


def unreadable(e: Exception) -> Problem:
    return Problem(422, "video_json_unreadable", f"video.json is unreadable: {e}")


def not_an_object() -> Problem:
    return Problem(422, "video_json_not_object", "video.json is not an object")


def read_video(folder: Folder) -> dict:
    if folder.legacy:
        return {"schema": SCHEMA, "slug": folder.slug, "title_working": f"{folder.walk} / {folder.path.name}",
                "format": "walk-reel", "channel": None, "language": None, "walks": [folder.walk],
                "status": legacy_status(folder.path), "history": [], "references": [], "ideas": [],
                "published_url": None, "legacy": True}
    try:
        data = json.loads((folder.path / "video.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise unreadable(e) from None
    if not isinstance(data, dict):
        raise not_an_object()
    return {**data, "slug": folder.slug, "legacy": False}


def stage_of(status: object) -> str | None:
    return STAGE_OF.get(status) if isinstance(status, str) else None


def summary(folder: Folder) -> dict:
    try:
        video, error, code = read_video(folder), None, None
    except Problem as e:
        video, error, code = {}, e.detail, e.code
    return {"slug": folder.slug, "title": video.get("title_working") or folder.slug,
            "format": video.get("format"), "channel": video.get("channel"), "status": video.get("status"),
            "stage": stage_of(video.get("status")), "legacy": folder.legacy,
            "updated": iso(last_change(folder.path)), "error": error, "error_code": code}
