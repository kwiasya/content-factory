"""Desk Videos API: the list, a Video's files, status and texts, and creating a Video.

Which folders are Videos and how they read lives in `cf.desk.videofolders`. Everything is computed per request;
nothing is cached.
"""

from __future__ import annotations

import json
import re
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cf import script_schema
from cf.desk import channels, contour_api, formats_api, media, paths, storeuse
from cf.desk.hashed import atomic_write, digest, stale
from cf.desk.problems import Problem, body as problem_body
from cf.desk.videofolders import (NAME, NOT_WALKS, SCHEMA, STAGES, STATUSES, VIDEO_SUFFIXES, Folder, find_folder,
                                  iso, last_change, list_folders, not_an_object, read_video, summary, unreadable,
                                  videos_dir, walk_files)
from cf.research import watchlist as watchlists

SUBTITLE_SUFFIXES = {".srt", ".vtt"}
TOP_TEXTS = {"brief.md": "brief", "voiceover.md": "voiceover", "notes.md": "notes", "references.md": "references"}
MEDIA_FOLDERS = {"renders": "render", "out": "render", "overlays": "overlay", "sources": "source"}
EDITABLE = {"script", "brief", "voiceover", "notes", "references", "subtitle"}
CREATABLE = {"brief.md", "voiceover.md", "notes.md"}
TITLE_MAX = 200
SLUG_MAX = 60
CYRILLIC = dict(zip("абвгдеёжзийклмнопрстуфхцчшщъыьэюя",
                    ["a", "b", "v", "g", "d", "e", "e", "zh", "z", "i", "y", "k", "l", "m", "n", "o", "p", "r",
                     "s", "t", "u", "f", "kh", "ts", "ch", "sh", "shch", "", "y", "", "e", "yu", "ya"]))
CYRILLIC.update({"і": "i", "ї": "yi", "є": "ye", "ґ": "g"})
CHANNEL_MAX = 64


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
    missing = Problem(404, "video_text_not_found", "not an editable text of this Video", path=rel)
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


def slug_for(title: str) -> str:
    """An ASCII folder name for a Video title: Cyrillic transliterated, Latin accents dropped, lower-case words
    joined by `-`."""
    s = "".join(CYRILLIC.get(c, c) for c in title.lower())
    s = "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower()
    s = re.sub(r"[^a-z0-9]+", "-", s).strip("-")
    if len(s) > SLUG_MAX:
        cut = s[:SLUG_MAX + 1]
        s = cut.rsplit("-", 1)[0] if "-" in cut else s[:SLUG_MAX]
    return s.strip("-") or "video"


def claim_folder(footage: Path, base: str) -> Path:
    """Create and return the first free `videos/<base>`, `videos/<base>-2`, …; the mkdir is the claim."""
    if not footage.is_dir():
        raise Problem(409, "footage_missing", f"the footage root {footage} does not exist; nothing was created",
                      path=str(footage))
    root = videos_dir(footage)
    root.mkdir(exist_ok=True)
    n = 1
    while True:
        name = base if n == 1 else f"{base}-{n}"
        try:
            (root / name).mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            n += 1
            continue
        return root / name


class VideoCreate(BaseModel):
    title: str
    format: str
    channel: str
    new_channel: bool = False
    idea_id: int | None = None


def checked_title(raw: str) -> str:
    title = raw.strip()
    if not title:
        raise Problem(422, "title_empty", "a Video needs a title")
    if len(title) > TITLE_MAX:
        raise Problem(422, "title_too_long", f"a Video title is at most {TITLE_MAX} characters", max=TITLE_MAX)
    return title


def checked_format(repo: Path, fid: str) -> None:
    known = sorted(f["id"] for f in formats_api.list_formats(repo))
    if fid not in known:
        raise Problem(422, "format_unknown", f"no Format {fid!r}; known: {', '.join(known) or 'none'}",
                      format=fid, formats=known)


def checked_channel(footage: Path, db_path: Path, name: str, new: bool) -> str:
    """The Channel a Video is created for: a known one, or with `new` a lower-case folder name of at most
    `CHANNEL_MAX` characters, which becomes the known Channel it equals ignoring case."""
    known = [c["id"] for c in channels.list_channels(footage, db_path)]
    if new:
        wanted = name.strip().lower()
        if len(wanted) > CHANNEL_MAX or not channels.valid_name(wanted):
            raise Problem(422, "channel_invalid", f"Channel {name!r} is not a folder name of at most {CHANNEL_MAX} "
                                                  "characters (letters, digits, `.`, `_`, `-`; not starting with `.`)",
                          channel=name, max=CHANNEL_MAX)
        return next((k for k in known if k.lower() == wanted), wanted)
    if name not in known:
        raise Problem(422, "channel_unknown", f"no Channel {name!r}; known: {', '.join(known) or 'none'}",
                      channel=name, channels=known)
    return name


def linked_brief(footage: Path, db_path: Path, idea_id: int) -> tuple[Path, dict, str | None]:
    """The Brief file of Idea `idea_id`, the Idea, and its Watchlist's language."""
    with storeuse.reading(db_path) as s:
        idea = contour_api.idea_of(s, idea_id)
        path = contour_api.brief_file(footage, idea)
        language = watchlists.get(s, idea.watchlist).language
    return path, idea.to_dict(), language


def channel_language(footage: Path, db_path: Path, channel: str) -> str | None:
    for c in channels.list_channels(footage, db_path):
        if c["id"] == channel and len(c["languages"]) == 1:
            return c["languages"][0]
    return None


def create_video(footage: Path, repo: Path, db_path: Path, body: VideoCreate) -> Folder:
    title = checked_title(body.title)
    checked_format(repo, body.format)
    channel = checked_channel(footage, db_path, body.channel, body.new_channel)
    brief, idea, language = None, None, None
    if body.idea_id is not None:
        brief, idea, language = linked_brief(footage, db_path, body.idea_id)
    if language is None:
        language = channel_language(footage, db_path, channel)
    folder = claim_folder(footage, slug_for(title))
    try:
        if brief is not None:
            (folder / "brief.md").write_bytes(brief.read_bytes())
        video = {"schema": SCHEMA, "slug": folder.name, "title_working": title, "format": body.format,
                 "channel": channel, "language": language, "walks": [], "status": "idea",
                 "history": [{"status": "idea", "at": datetime.now(timezone.utc).date().isoformat(), "note": ""}],
                 "references": [src["external_id"] for src in idea["sources"]] if idea else [],
                 "ideas": [idea["id"]] if idea else [], "published_url": None}
        atomic_write(folder / "video.json", (json.dumps(video, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return Folder(folder.name, folder, False)


def router(footage_root: Path, repo: Path, db_path: Path) -> APIRouter:
    footage = Path(footage_root)
    api = APIRouter()

    @api.get("/api/videos")
    def get_videos(format: str = "", channel: str = "") -> dict:
        items = [summary(f) for f in list_folders(footage)]
        items = [v for v in items if (not format or v["format"] == format) and (not channel or v["channel"] == channel)]
        items.sort(key=lambda v: v["updated"], reverse=True)
        return {"videos": items, "statuses": list(STATUSES), "stages": list(STAGES)}

    @api.post("/api/videos", status_code=201)
    def post_video(body: VideoCreate) -> dict:
        return detail(footage, create_video(footage, repo, db_path, body))

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
            raise Problem(409, "file_deleted", "the file was deleted since it was read", path=body.path)
        if text_format(body.path) == "json":
            violations = script_violations(footage, repo, body.text, script=kind_of(body.path) == "script")
            if violations:
                return JSONResponse(status_code=422, content=problem_body(
                    "script_invalid", "the Script did not pass cf-script/1 validation; nothing was written",
                    violations=violations))
        data = body.text.encode("utf-8")
        atomic_write(target, data)
        return {"path": body.path, "hash": digest(data)}

    @api.post("/api/videos/{slug}/status", response_model=None)
    def set_status(slug: str, body: StatusChange) -> dict | JSONResponse:
        folder = find_folder(footage, slug)
        if folder.legacy:
            raise Problem(409, "legacy_status",
                          "a legacy Reel's status is derived from its folder; migrate it to videos/ first")
        if body.status not in STATUSES:
            raise Problem(422, "status_invalid", f"status must be one of {', '.join(STATUSES)}",
                          status=body.status, statuses=list(STATUSES))
        target = folder.path / "video.json"
        current = target.read_bytes()
        conflict = stale(current, body.hash)
        if conflict:
            return conflict
        try:
            video = json.loads(current)
        except json.JSONDecodeError as e:
            raise unreadable(e) from None
        if not isinstance(video, dict):
            raise not_an_object()
        video["status"] = body.status
        today = datetime.now(timezone.utc).date().isoformat()
        video["history"] = [*(video.get("history") or []), {"status": body.status, "at": today, "note": body.note}]
        atomic_write(target, (json.dumps(video, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return detail(footage, folder)

    return api
