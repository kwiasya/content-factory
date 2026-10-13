"""Known Channels: the union of the Watchlists' `author_channel` in factory.db, the Brief folders
`<footage>/channels/<name>/` and the `channel` of every `videos/*/video.json`. There is no Channel registry."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from cf.desk import storeuse, videos_api
from cf.desk.problems import Problem
from cf.research import watchlist as watchlists
from cf.research.brief import UNASSIGNED

STORE_PROBLEMS = {"db_missing", "db_schema"}


def valid_name(name: object) -> bool:
    return isinstance(name, str) and name != UNASSIGNED and bool(videos_api.NAME.match(name))


def store_watchlists(db_path: Path) -> list[watchlists.Watchlist]:
    try:
        with storeuse.reading(db_path) as s:
            return watchlists.list_watchlists(s)
    except Problem as e:
        if e.code in STORE_PROBLEMS:
            return []
        raise


def list_channels(footage: Path, db_path: Path) -> list[dict]:
    found: dict[str, dict] = {}

    def entry(name: str) -> dict:
        return found.setdefault(name, {"id": name, "formats": set(), "languages": set(), "watchlists": set(),
                                       "videos": 0})

    for w in store_watchlists(db_path):
        if valid_name(w.author_channel):
            e = entry(w.author_channel)
            e["formats"].add(w.format_id)
            e["languages"].add(w.language)
            e["watchlists"].add(w.name)
    folders = Path(footage) / "channels"
    if folders.is_dir():
        for d in folders.iterdir():
            if d.is_dir() and valid_name(d.name):
                entry(d.name)
    for folder in videos_api.list_folders(Path(footage)):
        if folder.legacy:
            continue
        try:
            video = videos_api.read_video(folder)
        except Problem:
            continue
        if valid_name(video.get("channel")):
            e = entry(video["channel"])
            e["videos"] += 1
            if isinstance(video.get("format"), str):
                e["formats"].add(video["format"])
    return [{**e, "formats": sorted(e["formats"]), "languages": sorted(e["languages"]),
             "watchlists": sorted(e["watchlists"])} for _, e in sorted(found.items())]


def router(footage_root: Path, db_path: Path) -> APIRouter:
    api = APIRouter()

    @api.get("/api/channels")
    def get_channels() -> dict:
        return {"channels": list_channels(Path(footage_root), db_path)}

    return api
