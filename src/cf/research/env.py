"""Secrets for the research contour: ``.env`` in the repo root, never in git.

``load_env`` reads ``KEY=VALUE`` lines (comments and blank lines skipped,
optional quotes stripped) and sets each key in ``os.environ`` unless it is
already set, so a value exported in the shell always wins. ``api_key`` is the
one place the YouTube key is looked up.
"""

from __future__ import annotations

import os
from pathlib import Path

from cf.research.store import REPO_ROOT

ENV_PATH = REPO_ROOT / ".env"
KEY_VAR = "YOUTUBE_API_KEY"
KEY_HELP = (f"{KEY_VAR} is not set; create an API key for YouTube Data API v3 in Google Cloud Console "
            f"and put `{KEY_VAR}=...` into {ENV_PATH} (gitignored) or export it")


def load_env(path: Path = ENV_PATH) -> dict[str, str]:
    """Load ``path`` into ``os.environ`` (existing variables are kept); return what the file defined."""
    found: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except FileNotFoundError:
        return found
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        if key:
            found[key] = value
            os.environ.setdefault(key, value)
    return found


def api_key(path: Path = ENV_PATH) -> str | None:
    """The YouTube Data API key from the environment, else from ``.env``; None when absent."""
    key = os.environ.get(KEY_VAR)
    if not key:
        load_env(path)
        key = os.environ.get(KEY_VAR)
    return key or None
