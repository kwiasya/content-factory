"""Broken references in own skills: repo paths and `/skill-name` mentions that point at nothing."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

from cf.desk import skills
from cf.desk.skills import SKILLS_DIR, own_skills
from cf.desk.problems import Problem

TOKEN_RE = re.compile(r"[^\s`'\"()\[\],;|]+")
PLACEHOLDER_CHARS = set("<>{}*$~:")
PATH_SUFFIXES = (".md", ".json", ".py")


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
    known = skills.all_names(repo)
    for md in sorted(skill_dir.rglob("*.md")):
        rel = md.relative_to(repo).as_posix()
        bases = [repo, skill_dir, md.parent]
        for number, line in enumerate(md.read_text(encoding="utf-8", errors="replace").splitlines(), start=1):
            for token in TOKEN_RE.findall(line):
                ref = path_candidate(token)
                if ref and (ref, rel) not in seen and is_missing(ref, bases):
                    seen.add((ref, rel))
                    missing_paths.append({"ref": ref, "file": rel, "line": number})
            for skill in skills.mentions(line, known):
                ref = "/" + skill
                if skill in known or (ref, rel) in seen:
                    continue
                seen.add((ref, rel))
                missing_skills.append({"ref": ref, "file": rel, "line": number})
    return {"name": name, "missing_paths": missing_paths, "missing_skills": missing_skills}


def router(repo: Path) -> APIRouter:
    r = APIRouter()

    @r.get("/api/skills/lint")
    def lint_counts() -> dict:
        counts = {}
        for name in own_skills(repo):
            lint = lint_skill(repo, name)
            counts[name] = len(lint["missing_paths"]) + len(lint["missing_skills"])
        return {"skills": counts}

    @r.get("/api/skills/{name}/lint")
    def get_lint(name: str) -> dict:
        if name not in own_skills(repo):
            raise Problem(404, "skill_not_found", "no such own skill", name=name)
        return lint_skill(repo, name)

    return r
