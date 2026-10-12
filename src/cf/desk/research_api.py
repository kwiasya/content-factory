"""Research documents: topics parsed from docs/research/NN-slug/ folders, with the README table's theme and status."""

from __future__ import annotations

import re
from pathlib import Path

from fastapi import APIRouter

RESEARCH = "docs/research"
TOPIC_RE = re.compile(r"^(\d{2})-(.+)$")
ROW_RE = re.compile(r"^\|\s*(\d{2})\s*\|[^|]*\|([^|]*)\|([^|]*)\|")
FILES = {"chatgpt": "chatgpt.md", "result_a": "result-a.md", "rules": "rules.md", "verification": "verification.md"}


def readme_rows(readme: Path) -> dict[str, tuple[str, str]]:
    if not readme.is_file():
        return {}
    rows = {}
    for line in readme.read_text(encoding="utf-8").splitlines():
        match = ROW_RE.match(line.strip())
        if match:
            rows[match.group(1)] = (match.group(2).strip(), match.group(3).strip())
    return rows


def topics(repo: Path) -> dict:
    root = repo / RESEARCH
    if not root.is_dir():
        return {"topics": [], "synthesis": [], "readme": None}
    rows = readme_rows(root / "README.md")
    found = []
    for folder in sorted(p for p in root.iterdir() if p.is_dir()):
        match = TOPIC_RE.match(folder.name)
        if not match:
            continue
        number, slug = match.groups()
        title, status = rows.get(number, (slug, ""))
        rel = f"{RESEARCH}/{folder.name}"
        notes = sorted(f"{rel}/notes/{p.name}" for p in (folder / "notes").glob("*.md") if p.is_file())
        docs = sorted(f"{rel}/{p.name}" for p in folder.glob("*.md") if p.is_file())
        found.append({"id": folder.name, "number": number, "slug": slug, "title": title, "status": status,
                      **{key: (folder / name).is_file() for key, name in FILES.items()},
                      "notes": notes, "docs": docs})
    synthesis = sorted(f"{RESEARCH}/{p.name}" for p in root.glob("SYNTHESIS*.md") if p.is_file())
    readme = f"{RESEARCH}/README.md" if (root / "README.md").is_file() else None
    return {"topics": found, "synthesis": synthesis, "readme": readme}


def router(repo: Path) -> APIRouter:
    r = APIRouter()

    @r.get("/api/research")
    def get_research() -> dict:
        return topics(repo)

    return r
