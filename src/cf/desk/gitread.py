"""Read-only git for Desk: status, diff against HEAD, log and branch. Desk never commits, checks out or stashes."""

from __future__ import annotations

import subprocess
from pathlib import Path

CODES = {"M": "modified", "A": "added", "D": "deleted", "R": "renamed", "C": "copied", "T": "modified",
         "U": "conflicted"}


def _git(repo: Path, *args: str, ok: tuple[int, ...] = (0,)) -> str | None:
    try:
        done = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    except FileNotFoundError:
        return None
    return done.stdout if done.returncode in ok else None


def status(repo: Path) -> dict[str, str]:
    """Repo-relative path → modified/added/deleted/untracked/ignored/...; clean paths are absent."""
    out = _git(repo, "status", "--porcelain=v1", "-z", "--untracked-files=all", "--ignored=traditional")
    if out is None:
        return {}
    result: dict[str, str] = {}
    items = out.split("\0")
    i = 0
    while i < len(items):
        item = items[i]
        i += 1
        if len(item) < 4:
            continue
        xy, path = item[:2], item[3:]
        if xy[0] in "RC":
            i += 1
        if xy == "??":
            result[path] = "untracked"
        elif xy == "!!":
            result[path] = "ignored"
        else:
            code = xy[1] if xy[1] != " " else xy[0]
            result[path] = CODES.get(code, "modified")
    return result


def status_of(statuses: dict[str, str], rel: str) -> str:
    if rel in statuses:
        return statuses[rel]
    for path, state in statuses.items():
        if path.endswith("/") and rel.startswith(path):
            return state
    return "clean"


def diff(repo: Path, rel: str, state: str) -> str:
    if state in ("untracked", "ignored"):
        return _git(repo, "diff", "--no-color", "--no-index", "--", "/dev/null", rel, ok=(0, 1)) or ""
    return _git(repo, "diff", "--no-color", "HEAD", "--", rel) or ""


def log(repo: Path, rel: str, limit: int = 50) -> list[dict]:
    out = _git(repo, "log", f"-n{limit}", "--follow", "--format=%H%x1f%aI%x1f%an%x1f%s", "--", rel)
    entries = []
    for line in (out or "").splitlines():
        sha, date, author, subject = line.split("\x1f", 3)
        entries.append({"hash": sha, "date": date, "author": author, "subject": subject})
    return entries


def branch(repo: Path) -> str | None:
    out = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    if out is None:
        out = _git(repo, "symbolic-ref", "--short", "HEAD")
    return out.strip() if out else None
