"""Skill link map: what each own skill mentions (repo paths, cf.research commands, store tables, skills) and who mentions it."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

from cf.desk import catalog, skills
from cf.desk.skills import SKILLS_DIR
from cf.desk.problems import Problem

STORE = "src/cf/research/store.py"
PATH_RE = re.compile(r"(?<![\w./~-])((?:[\w.-]+/)+[\w.-]*|[\w-]+\.(?:md|json|py|ts|tsx|toml|yaml|yml|cube))")
COMMAND_RE = re.compile(r"\bcf\.research[ \t]+([a-z][a-z0-9_-]*)(?:[ \t]+([a-z][a-z0-9_-]*))?")
TABLE_RE = re.compile(r"CREATE TABLE (?:IF NOT EXISTS )?(\w+)")
SKIPPED_SEGMENTS = {".git", ".venv", "node_modules", "__pycache__", ".."}


def own_skill_texts(repo: Path) -> dict[str, str]:
    own = set(skills.own_skills(repo))
    texts: dict[str, list[str]] = {}
    for listing in catalog.list_groups(repo):
        for entry in listing.entries:
            name = skills.name_of(entry.path)
            if name in own:
                texts.setdefault(name, []).append((repo / entry.path).read_text(encoding="utf-8"))
    return {name: "\n".join(parts) for name, parts in sorted(texts.items())}


def store_tables(repo: Path) -> list[str]:
    store = repo / STORE
    return sorted(set(TABLE_RE.findall(store.read_text(encoding="utf-8")))) if store.is_file() else []


def mentioned_paths(repo: Path, name: str, text: str) -> list[str]:
    own = f"{SKILLS_DIR}/{name}"
    found = set()
    for token in PATH_RE.findall(text):
        rel = token.rstrip(".,:;").removeprefix("./").rstrip("/")
        if not rel or set(rel.split("/")) & SKIPPED_SEGMENTS:
            continue
        if rel == own or rel.startswith(own + "/"):
            continue
        target = repo / rel
        if target.exists() and target.resolve().is_relative_to(repo):
            found.add(rel)
    return sorted(found)


def mentioned_commands(text: str) -> list[str]:
    return sorted({" ".join(["cf.research", *(p for p in m if p)]) for m in COMMAND_RE.findall(text)})


def mentioned_tables(text: str, tables: list[str]) -> list[str]:
    found = []
    for table in tables:
        t = re.escape(table)
        pattern = (rf"`{t}`|(?<![\w-]){t}[ \t]+(?:table|rows?)\b"
                   rf"|\b(?:from|join|into|update|table)[ \t]+{t}(?![\w-])")
        if re.search(pattern, text, re.IGNORECASE):
            found.append(table)
    return found


def mentioned_skills(name: str, text: str, names: list[str]) -> list[str]:
    found = set(skills.mentions(text, names))
    return [other for other in names if other != name and other in found]


def link_map(repo: Path) -> list[dict]:
    texts = own_skill_texts(repo)
    names = skills.all_names(repo)
    tables = store_tables(repo)
    catalogued = {e.path for listing in catalog.list_groups(repo, include_hidden=True) for e in listing.entries}
    entries = []
    for name, text in texts.items():
        paths = mentioned_paths(repo, name, text)
        entries.append({
            "name": name,
            "path": f"{SKILLS_DIR}/{name}/SKILL.md",
            "paths": paths,
            "catalogued": [p for p in paths if p in catalogued],
            "commands": mentioned_commands(text),
            "tables": mentioned_tables(text, tables),
            "skills": mentioned_skills(name, text, names),
        })
    for entry in entries:
        entry["mentioned_by"] = [e["name"] for e in entries if entry["name"] in e["skills"]]
    return entries


def router(repo: Path) -> APIRouter:
    r = APIRouter()

    @r.get("/api/skills/links")
    def get_links() -> dict:
        return {"skills": link_map(repo)}

    @r.get("/api/skills/{name}/links")
    def get_skill_links(name: str) -> dict:
        for entry in link_map(repo):
            if entry["name"] == name:
                return entry
        raise Problem(404, "skill_not_found", "no such own skill", name=name)

    return r
