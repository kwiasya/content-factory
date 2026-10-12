"""Broken references in own skills: repo paths and `/skill-name` mentions that point at nothing."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter, HTTPException

SKILLS_DIR = ".claude/skills"
SKILL_NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
TOKEN_RE = re.compile(r"[^\s`'\"()\[\],;|]+")
PLACEHOLDER_CHARS = set("<>{}*$~:")
PATH_SUFFIXES = (".md", ".json", ".py")
MENTION_RE = re.compile(r"(?<![\w/.~-])/([a-z0-9][a-z0-9-]*)(?![\w/-]|\.\w)")
BUILTIN_COMMANDS = frozenset({
    "add-dir", "agents", "clear", "compact", "config", "context", "cost", "doctor", "exit", "help", "hooks",
    "ide", "init", "login", "logout", "mcp", "memory", "model", "permissions", "plugin", "resume", "review",
    "status", "vim",
})


def path_candidate(token: str) -> str | None:
    token = token.rstrip(".:!?")
    if not token or token.startswith(("/", "-")) or ".." in token or PLACEHOLDER_CHARS & set(token):
        return None
    if "/" not in token and not token.endswith(PATH_SUFFIXES):
        return None
    return token


def is_missing(ref: str, bases: list[Path]) -> bool:
    first = ref.split("/", 1)[0]
    anchored = [b for b in bases if (b / first).exists()]
    return bool(anchored) and not any((b / ref).exists() for b in anchored)


def lint_skill(repo: Path, name: str) -> dict:
    skill_dir = repo / SKILLS_DIR / name
    missing_paths: list[dict] = []
    missing_skills: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for md in sorted(skill_dir.rglob("*.md")):
        rel = md.relative_to(repo).as_posix()
        bases = [repo, skill_dir, md.parent]
        for number, line in enumerate(md.read_text(encoding="utf-8").splitlines(), start=1):
            for token in TOKEN_RE.findall(line):
                ref = path_candidate(token)
                if ref and (ref, rel) not in seen and is_missing(ref, bases):
                    seen.add((ref, rel))
                    missing_paths.append({"ref": ref, "file": rel, "line": number})
            for skill in MENTION_RE.findall(line):
                ref = "/" + skill
                if skill in BUILTIN_COMMANDS or (ref, rel) in seen or (repo / SKILLS_DIR / skill).is_dir():
                    continue
                seen.add((ref, rel))
                missing_skills.append({"ref": ref, "file": rel, "line": number})
    return {"name": name, "missing_paths": missing_paths, "missing_skills": missing_skills}


def router(repo: Path) -> APIRouter:
    r = APIRouter()

    @r.get("/api/skills/{name}/lint")
    def get_lint(name: str) -> dict:
        if not SKILL_NAME_RE.fullmatch(name) or name.startswith("remotion-") \
                or not (repo / SKILLS_DIR / name / "SKILL.md").is_file():
            raise HTTPException(404, "no such own skill")
        return lint_skill(repo, name)

    return r
