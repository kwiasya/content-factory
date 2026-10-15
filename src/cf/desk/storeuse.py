"""How Desk opens factory.db: one Store per request, never seeded; Desk never creates nor migrates the file.

sqlite connections stay on the thread that made them, so every request opens and closes its own Store, with
the store's busy timeout. Reads are ``mode=ro``; writes open the existing file without migrating it and answer
503 ``db_busy`` when another process or Mac holds the lock past the timeout. `ABSENT` holds the Problem codes
that mean there is no store to use (missing, the shared root not mounted, or another schema version); a caller
that can do without the store catches those and goes on.
"""

from __future__ import annotations

import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from cf.desk.problems import Problem
from cf.research.store import (BUSY_MESSAGE, SCHEMA_VERSION, SchemaMismatch, Store, StoreBusy, StoreMissing, connect,
                               is_busy, mount_hint, open_store, shared_root)

CREATE_COMMAND = "python -m cf.research db init"
MIGRATE_COMMAND = "python -m cf.research db migrate"
ABSENT = frozenset({"db_missing", "shared_unavailable", "db_schema", "db_schema_newer"})


def exists(db_path: Path) -> bool:
    return Path(db_path).is_file()


def _missing(p: Path) -> Problem:
    root = shared_root()
    if not root.is_dir() and (p.parent == root or root in p.parents):
        return Problem(404, "shared_unavailable", f"no research store at {p}: {mount_hint(root)}",
                       path=str(p), root=str(root))
    return Problem(404, "db_missing", f"no research store at {p} (factory.db); `{CREATE_COMMAND}` creates it",
                   path=str(p), command=CREATE_COMMAND)


def _schema(p: Path, version: int) -> Problem:
    return Problem(409, "db_schema", f"the research store {p} is schema version {version}, this code reads "
                                     f"{SCHEMA_VERSION}; `{MIGRATE_COMMAND}` migrates it",
                   path=str(p), version=version, expected=SCHEMA_VERSION, command=MIGRATE_COMMAND)


def _busy() -> Problem:
    return Problem(503, "db_busy", BUSY_MESSAGE)


@contextmanager
def reading(db_path: Path) -> Iterator[Store]:
    """A read-only Store; 404 when the file is missing, 409 when its schema is not the one this code reads."""
    p = Path(db_path)
    if not p.is_file():
        raise _missing(p)
    with Store(connect(p, readonly=True), p) as s:
        version = s.schema_version()
        if version > SCHEMA_VERSION:
            raise Problem(409, "db_schema_newer", f"the research store {p} is schema version {version}, newer than "
                                                  f"the {SCHEMA_VERSION} this Desk process reads; restart Desk",
                          path=str(p), version=version, expected=SCHEMA_VERSION)
        if version != SCHEMA_VERSION:
            raise _schema(p, version)
        try:
            yield s
        except sqlite3.OperationalError as exc:
            if is_busy(exc):
                raise _busy() from exc
            raise


@contextmanager
def writing(db_path: Path) -> Iterator[Store]:
    """A Store opened for a write: the existing file at this code's schema version, never created, migrated
    or seeded; 404 when it is missing, 409 on another version, 503 when the lock stays taken."""
    p = Path(db_path)
    try:
        s = open_store(p, seed=False, create=False, migrate=False)
    except StoreMissing:
        raise _missing(p) from None
    except SchemaMismatch as exc:
        if exc.version > SCHEMA_VERSION:
            raise Problem(409, "db_schema_newer", f"the research store {p} is schema version {exc.version}, newer "
                                                  f"than the {SCHEMA_VERSION} this Desk process reads; restart Desk",
                          path=str(p), version=exc.version, expected=SCHEMA_VERSION) from None
        raise _schema(p, exc.version) from None
    except StoreBusy:
        raise _busy() from None
    with s:
        try:
            yield s
        except sqlite3.OperationalError as exc:
            if is_busy(exc):
                raise _busy() from exc
            raise
