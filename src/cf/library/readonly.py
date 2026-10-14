"""A read-only store for callers outside Desk (the validator, the build): never creates, migrates or writes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cf.library.errors import LibraryError
from cf.research.store import Store

LIBRARY_TABLES = ("pack", "asset_author", "asset_alias")


def open_readonly(db_path: str | Path) -> Store | None:
    """The store at ``db_path`` opened ``mode=ro``; None when the file is missing; ``LibraryError`` when the
    schema has no Library tables (a store older than version 6)."""
    p = Path(db_path).expanduser()
    if not p.is_file():
        return None
    conn = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    s = Store(conn, p)
    try:
        have = set(s.tables())
        missing = [t for t in LIBRARY_TABLES if t not in have]
        if missing:
            raise LibraryError(f"the store {p} is schema version {s.schema_version()} and has no Library tables "
                               f"({', '.join(missing)}); any python -m cf.research or cf.library command migrates it",
                               path=str(p), version=s.schema_version())
    except BaseException:
        s.close()
        raise
    return s
