"""How Desk opens factory.db: one Store per request, never seeded; reads never create or migrate the file.

sqlite connections stay on the thread that made them, so every request opens and closes its own Store.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from fastapi import HTTPException

from cf.research.store import SCHEMA_VERSION, Store, open_store

CREATE_HINT = "any python -m cf.research command (for example: watchlist list) creates and migrates it"


def exists(db_path: Path) -> bool:
    return Path(db_path).is_file()


@contextmanager
def reading(db_path: Path) -> Iterator[Store]:
    """A read-only Store; 404 when the file is missing, 409 when its schema is not the one this code reads."""
    p = Path(db_path)
    if not p.is_file():
        raise HTTPException(404, f"no research store yet at {p} (factory.db); {CREATE_HINT}")
    conn = sqlite3.connect(f"{p.resolve().as_uri()}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    with Store(conn, p) as s:
        version = s.schema_version()
        if version != SCHEMA_VERSION:
            raise HTTPException(409, f"the research store {p} is schema version {version}, this code reads "
                                     f"{SCHEMA_VERSION}; {CREATE_HINT}")
        yield s


@contextmanager
def writing(db_path: Path) -> Iterator[Store]:
    """A Store opened for a write: created and migrated when needed, never seeded."""
    with open_store(db_path, seed=False) as s:
        yield s
