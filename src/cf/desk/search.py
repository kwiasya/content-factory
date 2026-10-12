"""Case-insensitive substring search over every catalogued document; no index, each file read once per request."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException

from cf.desk import catalog

MAX_HITS = 200
MAX_SNIPPETS = 3
CONTEXT = 70


def snippet(line: str, at: int, size: int) -> str:
    text = line.strip()
    if len(text) <= 2 * CONTEXT + size:
        return text
    at = max(at - (len(line) - len(line.lstrip())), 0)
    start = max(at - CONTEXT, 0)
    end = min(at + size + CONTEXT, len(text))
    return ("…" if start else "") + text[start:end].strip() + ("…" if end < len(text) else "")


def match(text: str, needle: str) -> tuple[int, list[dict]]:
    count = 0
    snippets = []
    for number, line in enumerate(text.splitlines(), 1):
        at = line.lower().find(needle)
        if at < 0:
            continue
        count += 1
        if len(snippets) < MAX_SNIPPETS:
            snippets.append({"line": number, "text": snippet(line, at, len(needle))})
    return count, snippets


def search(repo: Path, q: str, *, include_hidden: bool = False) -> dict:
    needle = q.strip().lower()
    groups = []
    total = 0
    truncated = False
    for listing in catalog.list_groups(repo, include_hidden=include_hidden):
        hits = []
        for entry in listing.entries:
            try:
                text = (repo / entry.path).read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            count, snippets = match(text, needle)
            if not count:
                continue
            if total == MAX_HITS:
                truncated = True
                break
            hits.append({"path": entry.path, "title": entry.title, "count": count, "snippets": snippets})
            total += 1
        if hits:
            groups.append({"id": listing.group.id, "title": listing.group.title, "hits": hits})
        if truncated:
            break
    return {"q": q, "total": total, "truncated": truncated, "groups": groups}


def router(repo: Path) -> APIRouter:
    r = APIRouter()

    @r.get("/api/search")
    def get_search(q: str, all: int = 0) -> dict:
        if not q.strip():
            raise HTTPException(422, "empty query")
        return search(repo, q, include_hidden=bool(all))

    return r
