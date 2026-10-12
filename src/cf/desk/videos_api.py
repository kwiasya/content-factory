"""Desk Videos: every `videos/<slug>/` plus every legacy `<walk>/reels/<reel>/`, their files, status and texts.

Video folders follow ADR 0006. A legacy Reel is addressed as `<walk>~<reel>`, has format `walk-reel` and a
status derived from what exists in its folder. Everything is computed per request; nothing is cached.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cf import script_schema
from cf.desk import media, paths
from cf.desk.hashed import atomic_write, digest, stale

SCHEMA = "cf-video/1"
STATUSES = ("idea", "brief", "script", "recording", "edit", "review", "published")
LEGACY_SEP = "~"
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
NOT_WALKS = {"videos", "references", "channels"}
VIDEO_SUFFIXES = {".mp4", ".mov", ".m4v", ".webm"}
SUBTITLE_SUFFIXES = {".srt", ".vtt"}
TOP_TEXTS = {"brief.md": "brief", "voiceover.md": "voiceover", "notes.md": "notes", "references.md": "references"}
MEDIA_FOLDERS = {"renders": "render", "out": "render", "overlays": "overlay", "sources": "source"}
EDITABLE = {"script", "brief", "voiceover", "notes", "references", "subtitle"}
CREATABLE = {"brief.md", "voiceover.md", "notes.md"}


@dataclass(frozen=True)
class Folder:
    slug: str
    path: Path
    legacy: bool
    walk: str | None = None


def videos_dir(footage: Path) -> Path:
    return footage / "videos"


def list_folders(footage: Path) -> list[Folder]:
    folders = []
    root = videos_dir(footage)
    if root.is_dir():
        for d in sorted(root.iterdir()):
            if NAME.match(d.name) and (d / "video.json").is_file():
                folders.append(Folder(d.name, d, False))
    if footage.is_dir():
        for walk in sorted(footage.iterdir()):
            if not NAME.match(walk.name) or walk.name in NOT_WALKS or not (walk / "reels").is_dir():
                continue
            for reel in sorted((walk / "reels").iterdir()):
                if reel.is_dir() and NAME.match(reel.name):
                    folders.append(Folder(f"{walk.name}{LEGACY_SEP}{reel.name}", reel, True, walk.name))
    return folders


def find_folder(footage: Path, slug: str) -> Folder:
    for folder in list_folders(footage):
        if folder.slug == slug:
            return folder
    raise HTTPException(404, "no such Video")


def walk_files(folder: Path) -> list[Path]:
    root = folder.resolve()
    return sorted(p for p in folder.rglob("*")
                  if p.is_file() and not any(part.startswith(".") for part in p.relative_to(folder).parts)
                  and p.resolve().is_relative_to(root))


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
    if any(reel.glob("script*.json")):
        return "script"
    return "idea"


def read_video(folder: Folder) -> dict:
    if folder.legacy:
        return {"schema": SCHEMA, "slug": folder.slug, "title_working": f"{folder.walk} / {folder.path.name}",
                "format": "walk-reel", "channel": None, "language": None, "walks": [folder.walk],
                "status": legacy_status(folder.path), "history": [], "references": [], "ideas": [],
                "published_url": None, "legacy": True}
    try:
        data = json.loads((folder.path / "video.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as e:
        raise HTTPException(422, f"video.json is unreadable: {e}") from None
    if not isinstance(data, dict):
        raise HTTPException(422, "video.json is not an object")
    return {**data, "slug": folder.slug, "legacy": False}


def summary(folder: Folder) -> dict:
    try:
        video, error = read_video(folder), None
    except HTTPException as e:
        video, error = {}, e.detail
    return {"slug": folder.slug, "title": video.get("title_working") or folder.slug,
            "format": video.get("format"), "channel": video.get("channel"), "status": video.get("status"),
            "legacy": folder.legacy, "updated": iso(last_change(folder.path)), "error": error}


def kind_of(rel: str) -> str:
    parts = rel.split("/")
    name = parts[-1]
    suffix = Path(name).suffix.lower()
    if rel == "video.json":
        return "video"
    if len(parts) == 1 and name.startswith("script") and suffix in (".md", ".json"):
        return "script"
    if len(parts) == 1 and name in TOP_TEXTS:
        return TOP_TEXTS[name]
    if suffix in SUBTITLE_SUFFIXES:
        return "subtitle"
    if suffix in VIDEO_SUFFIXES and len(parts) > 1 and parts[0] in MEDIA_FOLDERS:
        return MEDIA_FOLDERS[parts[0]]
    return "other"


def media_path(footage: Path, path: Path) -> str | None:
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        return None
    try:
        rel = path.relative_to(footage).as_posix()
    except ValueError:
        return None
    return rel if media.resolve(footage, rel) else None


def file_entry(footage: Path, folder: Path, path: Path) -> dict:
    rel = path.relative_to(folder).as_posix()
    kind = kind_of(rel)
    st = path.stat()
    return {"path": rel, "kind": kind, "size": st.st_size, "mtime": iso(st.st_mtime),
            "editable": kind in EDITABLE, "media": media_path(footage, path)}


def proxies(footage: Path, walks: list) -> list[dict]:
    found = []
    for walk in walks:
        if not isinstance(walk, str) or not NAME.match(walk) or walk in NOT_WALKS:
            continue
        folder = footage / walk / "proxy"
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir()):
            rel = media_path(footage, p)
            if rel:
                found.append({"walk": walk, "name": p.name, "size": p.stat().st_size, "media": rel})
    return found


def detail(footage: Path, folder: Folder) -> dict:
    video = read_video(folder)
    meta = folder.path / "video.json"
    return {"slug": folder.slug, "legacy": folder.legacy, "folder": str(folder.path), "video": video,
            "hash": None if folder.legacy else digest(meta.read_bytes()),
            "statuses": list(STATUSES), "updated": iso(last_change(folder.path)),
            "files": [file_entry(footage, folder.path, p) for p in walk_files(folder.path)],
            "proxies": proxies(footage, video.get("walks") or [])}


def text_format(rel: str) -> str:
    suffix = Path(rel).suffix.lower()
    return "markdown" if suffix == ".md" else "json" if suffix == ".json" else "text"


def text_target(folder: Folder, rel: str, *, creating: bool = False) -> Path:
    missing = HTTPException(404, "not an editable text of this Video")
    target = paths.contained(folder.path, rel)
    if target is None or kind_of(rel) not in EDITABLE:
        raise missing
    if target.is_file() or (creating and rel in CREATABLE and not target.exists()):
        return target
    raise missing


def script_violations(footage: Path, repo: Path, text: str, *, script: bool) -> list[str]:
    """Violations of a JSON text; a `script*.json` (`script` true) must be a cf-script/1 document."""
    try:
        data = json.loads(text)
    except json.JSONDecodeError as e:
        return [f"invalid JSON: {e}"]
    if not isinstance(data, dict) or data.get("schema") != script_schema.SCHEMA:
        if not script:
            return []
        found = data.get("schema") if isinstance(data, dict) else None
        return [f"schema must be {script_schema.SCHEMA}, got {json.dumps(found)}"]
    try:
        script = script_schema.from_dict(data)
    except script_schema.ScriptError as e:
        return [str(e)]
    walk = data.get("walk")
    manifest = None
    if isinstance(walk, str) and NAME.match(walk):
        manifest = optional_json(footage / walk / "clip_manifest.json")
    return script_schema.validate(script, manifest, optional_json(repo / "style.json"))


def optional_json(path: Path) -> dict | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


class TextWrite(BaseModel):
    path: str
    text: str
    hash: str


class StatusChange(BaseModel):
    status: str
    note: str = ""
    hash: str


def router(footage_root: Path, repo: Path) -> APIRouter:
    footage = Path(footage_root)
    api = APIRouter()

    @api.get("/api/videos")
    def get_videos() -> dict:
        items = [summary(f) for f in list_folders(footage)]
        items.sort(key=lambda v: v["updated"], reverse=True)
        return {"videos": items, "statuses": list(STATUSES)}

    @api.get("/api/videos/{slug}")
    def get_video(slug: str) -> dict:
        return detail(footage, find_folder(footage, slug))

    @api.get("/api/videos/{slug}/file")
    def get_file(slug: str, path: str) -> dict:
        target = text_target(find_folder(footage, slug), path)
        data = target.read_bytes()
        return {"path": path, "kind": kind_of(path), "format": text_format(path),
                "text": data.decode("utf-8", errors="replace"), "hash": digest(data)}

    @api.put("/api/videos/{slug}/file", response_model=None)
    def put_file(slug: str, body: TextWrite) -> dict | JSONResponse:
        target = text_target(find_folder(footage, slug), body.path, creating=True)
        current = target.read_bytes() if target.exists() else None
        conflict = stale(current, body.hash) if current is not None else None
        if conflict:
            return conflict
        if current is None and body.hash:
            raise HTTPException(409, "the file was deleted since it was read")
        if text_format(body.path) == "json":
            violations = script_violations(footage, repo, body.text, script=kind_of(body.path) == "script")
            if violations:
                return JSONResponse(status_code=422, content={
                    "detail": "the Script did not pass cf-script/1 validation; nothing was written",
                    "violations": violations})
        data = body.text.encode("utf-8")
        atomic_write(target, data)
        return {"path": body.path, "hash": digest(data)}

    @api.post("/api/videos/{slug}/status", response_model=None)
    def set_status(slug: str, body: StatusChange) -> dict | JSONResponse:
        folder = find_folder(footage, slug)
        if folder.legacy:
            raise HTTPException(409, "a legacy Reel's status is derived from its folder; migrate it to videos/ first")
        if body.status not in STATUSES:
            raise HTTPException(422, f"status must be one of {', '.join(STATUSES)}")
        target = folder.path / "video.json"
        current = target.read_bytes()
        conflict = stale(current, body.hash)
        if conflict:
            return conflict
        try:
            video = json.loads(current)
        except json.JSONDecodeError as e:
            raise HTTPException(422, f"video.json is unreadable: {e}") from None
        if not isinstance(video, dict):
            raise HTTPException(422, "video.json is not an object")
        video["status"] = body.status
        today = datetime.now(timezone.utc).date().isoformat()
        video["history"] = [*(video.get("history") or []), {"status": body.status, "at": today, "note": body.note}]
        atomic_write(target, (json.dumps(video, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return detail(footage, folder)

    return api
