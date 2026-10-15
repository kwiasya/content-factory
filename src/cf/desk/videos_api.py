"""Desk Videos API: the list, a Video's files, status and texts, and creating a Video.

Which folders are Videos and how they read lives in `cf.desk.videofolders`. Everything is computed per request;
nothing is cached.
"""

from __future__ import annotations

import json
import re
from dataclasses import replace
import shutil
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from cf import assets, library, script_schema
from cf.desk import channels, contour_api, formats_api, media, paths, storeuse
from cf.desk.hashed import atomic_write, digest, stale
from cf.desk.problems import Problem, body as problem_body
from cf.desk.videofolders import (NAME, NOT_FOOTAGE, SCHEMA, STAGES, STATUSES, VIDEO_SUFFIXES, Folder, find_folder,
                                  footage_ids, iso, last_change, list_folders, normalised, not_an_object, read_video,
                                  summary, unreadable, videos_dir, walk_files)
from cf.research import ideas as research_ideas
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
    if len(parts) == 1 and assets.is_script_file(name):
        return "script"
    if len(parts) == 1 and name in TOP_TEXTS:
        return TOP_TEXTS[name]
    if suffix in SUBTITLE_SUFFIXES:
        return "subtitle"
    if suffix in VIDEO_SUFFIXES and len(parts) > 1 and parts[0] in MEDIA_FOLDERS:
        return MEDIA_FOLDERS[parts[0]]
    return "other"


def media_path(root: Path, path: Path) -> str | None:
    if path.suffix.lower() not in VIDEO_SUFFIXES:
        return None
    try:
        rel = path.relative_to(root).as_posix()
    except ValueError:
        return None
    return rel if media.resolve(root, root, rel) else None


def file_entry(root: Path, folder: Path, path: Path) -> dict:
    rel = path.relative_to(folder).as_posix()
    kind = kind_of(rel)
    st = path.stat()
    return {"path": rel, "kind": kind, "size": st.st_size, "mtime": iso(st.st_mtime),
            "editable": kind in EDITABLE, "media": media_path(root, path)}


def proxies(root: Path, ids: list) -> list[dict]:
    found = []
    for footage in ids:
        if not isinstance(footage, str) or not NAME.match(footage) or footage in NOT_FOOTAGE:
            continue
        folder = root / footage / "proxy"
        if not folder.is_dir():
            continue
        for p in sorted(folder.iterdir()):
            rel = media_path(root, p)
            if rel:
                found.append({"footage": footage, "name": p.name, "size": p.stat().st_size, "media": rel})
    return found


def detail(root: Path, folder: Folder) -> dict:
    video = read_video(folder)
    meta = folder.path / "video.json"
    return {"slug": folder.slug, "legacy": folder.legacy, "folder": str(folder.path), "video": video,
            "hash": None if folder.legacy else digest(meta.read_bytes()),
            "statuses": list(STATUSES), "updated": iso(last_change(folder.path)),
            "files": [file_entry(root, folder.path, p) for p in walk_files(folder.path)],
            "proxies": proxies(root, footage_ids(video))}


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


def asset_context(root: Path, folder: Path | None, db_path: Path | None,
                  shared: Path | None = None) -> "assets.AssetContext":
    """The Library (read-only) and the Video folder's md refs, for a Script with Asset cues."""
    video = None
    if folder is not None:
        video = assets.video_folder(folder) or assets.VideoFolder(folder, folder.name, root, False, None)
    lib, problem = None, None
    if db_path is None:
        problem = "no factory.db configured"
    else:
        try:
            with storeuse.reading(db_path) as s:
                lib = library.load(assets.library_root(shared), s)
        except Problem as exc:
            if exc.code not in storeuse.ABSENT:
                raise
            problem = exc.detail
    if lib is None:
        return assets.AssetContext(None, problem, video, assets.md_refs(video.path) if video else {}, cli=False)
    return replace(assets.context(None, library=lib, video=video), cli=False)


def script_violations(root: Path, repo: Path, text: str, *, script: bool, folder: Path | None = None,
                      db_path: Path | None = None, shared: Path | None = None) -> list[str]:
    """Violations of a JSON text; a `script*.json` (`script` true) must be a cf-script/1 document. Asset cues are
    checked against the Library and the md files of `folder` (the Video); a Script without cues opens no store."""
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
    manifest = None
    if NAME.match(script.footage):
        manifest = optional_json(root / script.footage / "clip_manifest.json")
    ctx = asset_context(root, folder, db_path, shared) if script_schema.has_cues(script) else None
    return script_schema.validate(script, manifest, optional_json(repo / "style.json"), assets=ctx)


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


def claim_folder(root: Path, base: str) -> Path:
    """Create and return the first free `videos/<base>`, `videos/<base>-2`, …; the mkdir is the claim."""
    if not root.is_dir():
        raise Problem(409, "local_root_missing", f"the local root {root} does not exist; nothing was created",
                      path=str(root))
    vdir = videos_dir(root)
    vdir.mkdir(exist_ok=True)
    n = 1
    while True:
        name = base if n == 1 else f"{base}-{n}"
        try:
            (vdir / name).mkdir(parents=False, exist_ok=False)
        except FileExistsError:
            n += 1
            continue
        return vdir / name


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


def checked_channel(root: Path, db_path: Path, name: str, new: bool) -> str:
    """The Channel a Video is created for: a known one, or with `new` a lower-case folder name of at most
    `CHANNEL_MAX` characters, which becomes the known Channel it equals ignoring case."""
    known = [c["id"] for c in channels.list_channels(root, db_path)]
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


def linked_brief(root: Path, db_path: Path, idea_id: int) -> tuple[Path, dict, str | None]:
    """The Brief file of Idea `idea_id`, the Idea, and its Watchlist's language."""
    with storeuse.reading(db_path) as s:
        idea = contour_api.idea_of(s, idea_id)
        path = contour_api.brief_file(root, idea)
        language = watchlists.get(s, idea.watchlist).language
    return path, idea.to_dict(), language


def channel_language(root: Path, db_path: Path, channel: str) -> str | None:
    for c in channels.list_channels(root, db_path):
        if c["id"] == channel and len(c["languages"]) == 1:
            return c["languages"][0]
    return None


def create_video(root: Path, repo: Path, db_path: Path, body: VideoCreate) -> Folder:
    title = checked_title(body.title)
    checked_format(repo, body.format)
    channel = checked_channel(root, db_path, body.channel, body.new_channel)
    brief, idea, language = None, None, None
    if body.idea_id is not None:
        brief, idea, language = linked_brief(root, db_path, body.idea_id)
    if language is None:
        language = channel_language(root, db_path, channel)
    folder = claim_folder(root, slug_for(title))
    try:
        if brief is not None:
            (folder / "brief.md").write_bytes(brief.read_bytes())
        video = {"schema": SCHEMA, "slug": folder.name, "title_working": title, "format": body.format,
                 "channel": channel, "language": language, "footage": [], "status": "idea",
                 "history": [{"status": "idea", "at": datetime.now(timezone.utc).date().isoformat(), "note": ""}],
                 "references": [src["external_id"] for src in idea["sources"]] if idea else [],
                 "ideas": [idea["id"]] if idea else [], "published_url": None}
        atomic_write(folder / "video.json", (json.dumps(video, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        if idea is not None:
            try:
                with storeuse.writing(db_path) as s:
                    research_ideas.link_video(s, idea["id"], folder.name)
            except Exception as exc:
                raise Problem(500, "idea_link_failed", f"could not link Idea {idea['id']} to the new Video: {exc}; "
                                                       "nothing was created", id=idea["id"], detail=str(exc)) from exc
    except BaseException:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    return Folder(folder.name, folder, False)


def router(root: Path, repo: Path, db_path: Path, shared: Path | None = None) -> APIRouter:
    root = Path(root)
    shared = root if shared is None else Path(shared)
    api = APIRouter()

    @api.get("/api/videos")
    def get_videos(format: str = "", channel: str = "") -> dict:
        items = [summary(f) for f in list_folders(root)]
        items = [v for v in items if (not format or v["format"] == format) and (not channel or v["channel"] == channel)]
        items.sort(key=lambda v: v["updated"], reverse=True)
        return {"videos": items, "statuses": list(STATUSES), "stages": list(STAGES)}

    @api.post("/api/videos", status_code=201)
    def post_video(body: VideoCreate) -> dict:
        return detail(root, create_video(root, repo, db_path, body))

    @api.get("/api/videos/{slug}")
    def get_video(slug: str) -> dict:
        return detail(root, find_folder(root, slug))

    @api.get("/api/videos/{slug}/file")
    def get_file(slug: str, path: str) -> dict:
        target = text_target(find_folder(root, slug), path)
        data = target.read_bytes()
        return {"path": path, "kind": kind_of(path), "format": text_format(path),
                "text": data.decode("utf-8", errors="replace"), "hash": digest(data)}

    @api.put("/api/videos/{slug}/file", response_model=None)
    def put_file(slug: str, body: TextWrite) -> dict | JSONResponse:
        folder = find_folder(root, slug)
        target = text_target(folder, body.path, creating=True)
        current = target.read_bytes() if target.exists() else None
        conflict = stale(current, body.hash) if current is not None else None
        if conflict:
            return conflict
        if current is None and body.hash:
            raise Problem(409, "file_deleted", "the file was deleted since it was read", path=body.path)
        if text_format(body.path) == "json":
            violations = script_violations(root, repo, body.text, script=kind_of(body.path) == "script",
                                           folder=target.parent, db_path=db_path, shared=shared)
            if violations:
                return JSONResponse(status_code=422, content=problem_body(
                    "script_invalid", "the Script did not pass cf-script/1 validation; nothing was written",
                    violations=violations))
        data = body.text.encode("utf-8")
        atomic_write(target, data)
        return {"path": body.path, "hash": digest(data)}

    @api.post("/api/videos/{slug}/status", response_model=None)
    def set_status(slug: str, body: StatusChange) -> dict | JSONResponse:
        folder = find_folder(root, slug)
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
        video = normalised(video)
        video["status"] = body.status
        today = datetime.now(timezone.utc).date().isoformat()
        video["history"] = [*(video.get("history") or []), {"status": body.status, "at": today, "note": body.note}]
        atomic_write(target, (json.dumps(video, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        return detail(root, folder)

    return api
