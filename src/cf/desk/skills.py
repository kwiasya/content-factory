"""What a skill is to Desk: where skills live, which are vendored, which are own, and how a text mentions one."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

SKILLS_DIR = ".claude/skills"
VENDORED_PREFIX = "remotion-"
SKILL_NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
SLASH_RE = re.compile(r"(?<![\w/.~-])/([a-z0-9][a-z0-9-]*)(?![\w/-]|\.\w)")
BUILTIN_COMMANDS = frozenset({
    "add-dir", "agents", "clear", "compact", "config", "context", "cost", "doctor", "exit", "help", "hooks",
    "ide", "init", "login", "logout", "mcp", "memory", "model", "permissions", "plugin", "resume", "review",
    "status", "vim",
})


def is_vendored(name: str) -> bool:
    return name.startswith(VENDORED_PREFIX)


def name_of(rel: str) -> str | None:
    """The skill a repo-relative path belongs to, or None outside the skills folder."""
    prefix = SKILLS_DIR + "/"
    if not rel.startswith(prefix):
        return None
    rest = rel[len(prefix):].split("/")
    return rest[0] if len(rest) > 1 else None


def all_names(repo: Path) -> list[str]:
    root = repo / SKILLS_DIR
    return sorted(p.name for p in root.iterdir() if p.is_dir()) if root.is_dir() else []


def own_skills(repo: Path) -> list[str]:
    """Skill folders with a SKILL.md and a well-formed name that are not vendored."""
    return sorted(p.parent.name for p in (repo / SKILLS_DIR).glob("*/SKILL.md")
                  if SKILL_NAME_RE.fullmatch(p.parent.name) and not is_vendored(p.parent.name))


def mentions(text: str, known: Iterable[str]) -> list[str]:
    """Skill names a text mentions, in order of first mention: every `/name` that is not a built-in command
    (known or not), and each known name right after a backtick or as `.claude/skills/<name>`."""
    known = list(known)
    found: dict[str, int] = {}
    for m in SLASH_RE.finditer(text):
        name = m.group(1)
        if name in known or name not in BUILTIN_COMMANDS:
            found.setdefault(name, m.start())
    for name in known:
        n = re.escape(name)
        m = re.search(rf"(?:`|{re.escape(SKILLS_DIR)}/){n}(?![\w-])", text)
        if m:
            found[name] = min(found.get(name, m.start()), m.start())
    return sorted(found, key=found.__getitem__)
