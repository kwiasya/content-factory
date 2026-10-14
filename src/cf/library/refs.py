"""Asset refs: ``@<category>/<name>``, the slug rule that makes a name from a file stem, and sticky numbering."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Iterable

from cf.library.errors import RefError

CATEGORIES = ("sfx", "meme", "img", "emoji", "face", "bg", "footage", "fx", "music", "font", "template")
RIGHTS = ("own", "free", "unknown")
MAX_SLUG = 60

_NAME = r"(?:[^\W_]|-)+"
_CATS = "|".join(CATEGORIES)
REF_RE = re.compile(rf"(?<![^\s(\[«\"'])(@({_CATS})/({_NAME}))")
_FULL = re.compile(rf"@({_CATS})/({_NAME})")


def slug(stem: str) -> str:
    s = unicodedata.normalize("NFC", stem).replace("+", "plus-").replace("&", "-and-").lower()
    out: list[str] = []
    for ch in s:
        if ch.isalnum():
            out.append(ch)
        elif not out or out[-1] != "-":
            out.append("-")
    s = "".join(out).strip("-")
    if len(s) > MAX_SLUG:
        cut = s[:MAX_SLUG]
        if s[MAX_SLUG] != "-" and "-" in cut:
            cut = cut[:cut.rindex("-")]
        s = cut.strip("-")
    return s or "item"


def make(category: str, name: str) -> str:
    return f"@{category}/{name}"


def parse(ref: str) -> tuple[str, str]:
    m = _FULL.fullmatch(ref.strip())
    if not m:
        raise RefError(ref)
    return m.group(1), m.group(2)


def find(text: str) -> list[str]:
    return [m.group(1) for m in REF_RE.finditer(text)]


def numbered(base: str, taken: Callable[[str], bool]) -> str:
    if not taken(base):
        return base
    n = 2
    while taken(f"{base}-{n}"):
        n += 1
    return f"{base}-{n}"


def assign(items: Iterable[tuple[str, str, str | None]], owners: dict[str, str]) -> dict[str, str]:
    """Names for ``(key, slug, kept)`` items of one category: a kept name stays, the rest get the bare slug
    or the lowest free number from 2, in the order given. ``owners`` maps names already held elsewhere to
    their holder's key; a name is free for its own holder."""
    items = list(items)
    used = dict(owners)
    out: dict[str, str] = {}

    def free(name: str, key: str) -> bool:
        return used.get(name, key) == key

    for key, _, kept in items:
        if kept is not None and free(kept, key):
            out[key] = kept
            used[kept] = key
    for key, base, _ in items:
        if key in out:
            continue
        name = numbered(base, lambda n: not free(n, key))
        out[key] = name
        used[name] = key
    return out
