"""Format ids: the one rule every research module applies to them.

A Format id names a folder under ``formats/`` in the repo (the Hook library
lives in ``formats/<format_id>/hook-library.md``) and is stored on every
Watchlist of that Format, so both places accept the same ids.
"""

from __future__ import annotations

import re

FORMAT_ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]*")
RULE = "lower case letters, digits, - or _, starting with a letter or digit (e.g. walk-reel)"


def problem(format_id: object) -> str | None:
    """Why ``format_id`` cannot be a Format id, or None when it can."""
    if not isinstance(format_id, str) or not FORMAT_ID_RE.fullmatch(format_id):
        return f"Format id {format_id!r} must be {RULE}"
    return None
