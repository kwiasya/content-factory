"""Claude Code hook: show the Author's open Notes when a skill starts (docs/desk.md, ADR 0005).

PreToolUse on the Skill tool reads ``tool_input.skill``; UserPromptExpansion (a typed
``/skill``) reads ``command_name``. Prints, as ``additionalContext``, the open Notes of kind
``skill`` for that name, of kind ``document`` under ``.claude/skills/<name>/`` and the
``general`` ones. Reads factory.db read-only with the stdlib, never migrates it; prints nothing
and exits 0 when the db, the table or matching Notes are missing, or on any error. The store is
``CF_FACTORY_DB``, else ``<CF_SHARED_ROOT>/factory.db``, else ``/Users/Shared/content-factory/factory.db``;
the variables come from the environment, else from the personal ``<repo>/.env`` (``CF_ENV_FILE``).
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[2]
DEFAULT_SHARED_ROOT = Path("/Users/Shared/content-factory")


def dotenv() -> dict[str, str]:
    path = Path(os.environ.get("CF_ENV_FILE") or REPO / ".env")
    out: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return out
    for raw in lines:
        line = raw.strip()
        if line.startswith("export "):
            line = line[len("export "):]
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = (x.strip() for x in line.split("=", 1))
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        out[key] = value
    return out


def db_path() -> Path:
    file = dotenv()

    def var(name: str) -> str | None:
        return os.environ.get(name) or file.get(name) or None
    if var("CF_FACTORY_DB"):
        return Path(var("CF_FACTORY_DB")).expanduser()
    root = var("CF_SHARED_ROOT")
    return (Path(root).expanduser() if root else DEFAULT_SHARED_ROOT) / "factory.db"


def skill_of(event: dict) -> str:
    if event.get("hook_event_name") == "UserPromptExpansion":
        name = event.get("command_name")
    else:
        name = (event.get("tool_input") or {}).get("skill")
    return name.strip().lstrip("/") if isinstance(name, str) else ""


def open_notes(path: Path, skill: str) -> list[sqlite3.Row]:
    conn = sqlite3.connect(f"{path.resolve().as_uri()}?mode=ro", uri=True, timeout=10)
    try:
        conn.row_factory = sqlite3.Row
        if conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'note'").fetchone() is None:
            return []
        folder = f".claude/skills/{skill}/"
        return conn.execute(
            "SELECT id, kind, key, text FROM note WHERE resolved_at IS NULL AND ("
            " (kind = 'skill' AND key = ?) OR (kind = 'document' AND substr(key, 1, ?) = ?)"
            " OR kind = 'general') ORDER BY kind = 'general', id",
            (skill, len(folder), folder)).fetchall()
    finally:
        conn.close()


def context(skill: str, rows: list[sqlite3.Row]) -> str:
    lines = [f"Open Notes from the Author for skill `{skill}`. Act on them in this run; after acting on one,"
             " close it with `.venv/bin/python -m cf.research notes resolve <id>`."]
    for r in rows:
        where = "general" if r["kind"] == "general" else f"{r['kind']} {r['key']}"
        lines.append(f"- #{r['id']} [{where}] {r['text']}")
    return "\n".join(lines)


def main() -> None:
    try:
        event = json.loads(sys.stdin.read())
        skill = skill_of(event) if isinstance(event, dict) else ""
        path = db_path()
        if not skill or not path.is_file():
            return
        rows = open_notes(path, skill)
        if rows:
            print(json.dumps({"hookSpecificOutput": {"hookEventName": event.get("hook_event_name", "PreToolUse"),
                                                     "additionalContext": context(skill, rows)}},
                             ensure_ascii=False))
    except Exception:
        return


if __name__ == "__main__":
    main()
