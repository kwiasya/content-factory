"""The Format shelf: each `formats/<id>/FORMAT.md` with its Hook library, the research rules it names and its Videos."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

from cf.desk import videos_api
from cf.desk.research_api import RESEARCH_DIR

FORMATS_DIR = "formats"
FORMAT_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
RULES_LINE_RE = re.compile(r"^\W*Research rules that apply:\s*(.*)$", re.MULTILINE)
RULE_ROW_RE = re.compile(r"^\|\s*R\d{2}-\d+\s*\|")
RULE_FIELDS = ("id", "rule", "scope", "tag", "source", "confidence")
HEADER_ALIASES = {"applies to": "scope", "platform": "scope", "conf": "confidence"}


def format_title(text: str, fallback: str) -> str:
    for line in text.splitlines():
        if line.startswith("# "):
            return re.sub(r"^Format:\s*", "", line[2:].strip()) or fallback
    return fallback


def list_formats(repo: Path) -> list[dict]:
    found = []
    for path in sorted((repo / FORMATS_DIR).glob("*/FORMAT.md")):
        fid = path.parent.name
        found.append({
            "id": fid,
            "title": format_title(path.read_text(encoding="utf-8"), fid),
            "path": path.relative_to(repo).as_posix(),
            "has_hook_library": (path.parent / "hook-library.md").is_file(),
        })
    return found


def read_doc(repo: Path, path: Path) -> dict | None:
    if not path.is_file():
        return None
    return {"path": path.relative_to(repo).as_posix(), "text": path.read_text(encoding="utf-8")}


def rule_topics(format_text: str) -> list[str]:
    match = RULES_LINE_RE.search(format_text)
    if not match:
        return []
    named = re.sub(r"\([^)]*\)", "", match.group(1))
    return list(dict.fromkeys(re.findall(r"\b\d{2}\b", named)))


def rules_path(repo: Path, topic: str) -> Path | None:
    for folder in sorted((repo / RESEARCH_DIR).glob(f"{topic}-*")):
        if (folder / "rules.md").is_file():
            return folder / "rules.md"
    return None


def cells(line: str) -> list[str]:
    return [c.strip() for c in re.split(r"(?<!\\)\|", line.strip().strip("|"))]


def parse_rules(text: str, topic: str) -> list[dict]:
    rules = []
    header: list[str] = []
    previous = ""
    for line in text.splitlines():
        if not line.startswith("|"):
            header, previous = [], ""
            continue
        if re.fullmatch(r"\|[\s|:-]+\|?", line.strip()):
            header = [HEADER_ALIASES.get(h.lower(), h.lower()) for h in cells(previous)]
        elif RULE_ROW_RE.match(line) and header:
            row = dict(zip(header, cells(line)))
            rules.append({"topic": topic, **{f: row.get(f, "") for f in RULE_FIELDS}})
        previous = line
    return rules


def format_videos(footage_root: Path, fid: str) -> list[dict]:
    footage = Path(footage_root)
    videos = []
    for folder in videos_api.list_folders(footage):
        item = videos_api.summary(folder)
        if item["format"] == fid:
            videos.append({"slug": item["slug"], "title": item["title"], "status": item["status"],
                           "channel": item["channel"], "path": str(folder.path)})
    return videos


def format_page(repo: Path, footage_root: Path, fid: str) -> dict | None:
    folder = repo / FORMATS_DIR / fid
    if not FORMAT_ID_RE.fullmatch(fid) or not (folder / "FORMAT.md").is_file():
        return None
    doc = read_doc(repo, folder / "FORMAT.md")
    topics, rules = [], []
    for topic in rule_topics(doc["text"]):
        path = rules_path(repo, topic)
        topics.append({"topic": topic, "path": path.relative_to(repo).as_posix() if path else None})
        if path:
            rules.extend(parse_rules(path.read_text(encoding="utf-8"), topic))
    return {
        "id": fid,
        "title": format_title(doc["text"], fid),
        "format": doc,
        "hook_library": read_doc(repo, folder / "hook-library.md"),
        "topics": topics,
        "rules": rules,
        "videos": format_videos(footage_root, fid),
    }


def router(repo: Path, footage_root: Path) -> APIRouter:
    r = APIRouter()

    @r.get("/api/formats")
    def get_formats() -> dict:
        return {"formats": list_formats(repo)}

    @r.get("/api/formats/{fid}")
    def get_format(fid: str) -> dict:
        page = format_page(repo, footage_root, fid)
        if page is None:
            raise HTTPException(404, "no such Format")
        return page

    return r
