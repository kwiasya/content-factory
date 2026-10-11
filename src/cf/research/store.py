"""The research store: one SQLite file at the footage root.

Path: ``--db`` on the CLI, else ``CF_FACTORY_DB``, else
``<footage root>/factory.db`` where the footage root is ``CF_FOOTAGE_ROOT`` or
``~/Movies/content-factory``. Every table of the research spec is created up
front (schema version in ``PRAGMA user_version``); later versions append to
``MIGRATIONS``. Opening also loads the taxonomy seed from the repo (idempotent).

JSON columns hold text; ``Store.query`` returns plain dicts.
"""

from __future__ import annotations

import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_FOOTAGE_ROOT = Path.home() / "Movies" / "content-factory"
REPO_ROOT = Path(__file__).resolve().parents[3]  # the repo checkout (taxonomy seed, templates, formats/)


class StoreError(Exception):
    """The database cannot be opened or a write breaks a store rule."""


def footage_root() -> Path:
    """``CF_FOOTAGE_ROOT`` or ``~/Movies/content-factory``."""
    env = os.environ.get("CF_FOOTAGE_ROOT")
    return Path(env).expanduser() if env else DEFAULT_FOOTAGE_ROOT


def default_db_path() -> Path:
    """``CF_FACTORY_DB`` or ``<footage root>/factory.db``."""
    env = os.environ.get("CF_FACTORY_DB")
    return Path(env).expanduser() if env else footage_root() / "factory.db"


def now_iso(now: datetime | None = None) -> str:
    """``now`` (default: the current time) as a UTC timestamp, seconds, ISO 8601 with ``Z``."""
    return (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Version 1: every table of the research spec (#1). Booleans are 0/1, JSON is text,
# timestamps are ISO 8601 UTC text.
V1 = """
CREATE TABLE watchlist (
    id          INTEGER PRIMARY KEY,
    name        TEXT NOT NULL UNIQUE,
    format_id   TEXT NOT NULL,
    channel_id  TEXT,
    language    TEXT NOT NULL DEFAULT 'en',
    region      TEXT,
    queries     TEXT NOT NULL DEFAULT '[]',
    created_at  TEXT NOT NULL
);
CREATE TABLE channel (
    id                  INTEGER PRIMARY KEY,
    platform            TEXT NOT NULL DEFAULT 'youtube',
    external_id         TEXT NOT NULL,
    handle              TEXT,
    title               TEXT,
    description         TEXT,
    country             TEXT,
    published_at        TEXT,
    subscriber_count    INTEGER,
    video_count         INTEGER,
    view_count          INTEGER,
    uploads_playlist_id TEXT,
    own                 INTEGER NOT NULL DEFAULT 0,
    raw                 TEXT,
    fetched_at          TEXT,
    UNIQUE (platform, external_id)
);
CREATE INDEX channel_handle ON channel (platform, handle);
CREATE TABLE watchlist_channel (
    watchlist_id INTEGER NOT NULL REFERENCES watchlist (id) ON DELETE CASCADE,
    channel_id   INTEGER NOT NULL REFERENCES channel (id) ON DELETE CASCADE,
    added_at     TEXT NOT NULL,
    PRIMARY KEY (watchlist_id, channel_id)
);
CREATE TABLE video (
    id             INTEGER PRIMARY KEY,
    platform       TEXT NOT NULL DEFAULT 'youtube',
    external_id    TEXT NOT NULL,
    channel_id     INTEGER REFERENCES channel (id),
    title          TEXT,
    description    TEXT,
    published_at   TEXT,
    duration_s     REAL,
    kind           TEXT CHECK (kind IN ('short', 'long')),
    tags           TEXT NOT NULL DEFAULT '[]',
    url            TEXT,
    own            INTEGER NOT NULL DEFAULT 0,
    has_media      INTEGER NOT NULL DEFAULT 0,
    has_transcript INTEGER NOT NULL DEFAULT 0,
    raw            TEXT,
    fetched_at     TEXT,
    UNIQUE (platform, external_id)
);
CREATE INDEX video_channel ON video (channel_id, kind, published_at);
CREATE TABLE snapshot (
    id       INTEGER PRIMARY KEY,
    video_id INTEGER NOT NULL REFERENCES video (id) ON DELETE CASCADE,
    taken_at TEXT NOT NULL,
    views    INTEGER,
    likes    INTEGER,
    comments INTEGER,
    UNIQUE (video_id, taken_at)
);
CREATE TABLE card (
    id         INTEGER PRIMARY KEY,
    video_id   INTEGER NOT NULL UNIQUE REFERENCES video (id) ON DELETE CASCADE,
    schema     TEXT NOT NULL,
    measured   TEXT NOT NULL DEFAULT '{}',
    analysis   TEXT,
    written_at TEXT NOT NULL
);
CREATE TABLE idea (
    id               INTEGER PRIMARY KEY,
    watchlist_id     INTEGER NOT NULL REFERENCES watchlist (id) ON DELETE CASCADE,
    source_video_ids TEXT NOT NULL DEFAULT '[]',
    title            TEXT NOT NULL,
    fields           TEXT NOT NULL DEFAULT '{}',
    status           TEXT NOT NULL DEFAULT 'inbox'
                     CHECK (status IN ('inbox', 'shortlisted', 'discarded', 'brief')),
    notes            TEXT,
    brief_path       TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE TABLE hook (
    id              INTEGER PRIMARY KEY,
    format_id       TEXT NOT NULL,
    category        TEXT NOT NULL,
    formula         TEXT,
    text            TEXT NOT NULL,
    source_video_id INTEGER REFERENCES video (id) ON DELETE SET NULL,
    saved_at        TEXT NOT NULL
);
CREATE TABLE taxonomy (
    id         INTEGER PRIMARY KEY,
    kind       TEXT NOT NULL,
    value      TEXT NOT NULL,
    label      TEXT,
    note       TEXT,
    status     TEXT NOT NULL CHECK (status IN ('approved', 'proposed', 'rejected')),
    source     TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (kind, value)
);
CREATE TABLE quota (
    day    TEXT NOT NULL,
    bucket TEXT NOT NULL,
    method TEXT NOT NULL,
    calls  INTEGER NOT NULL DEFAULT 0,
    units  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, method)
);
"""

# Version 2 (#4 scout): a channel remembers when its first uploads backfill finished, and a
# Watchlist remembers which videos its search queries found (their channels are candidates).
V2 = """
ALTER TABLE channel ADD COLUMN backfilled_at TEXT;
CREATE TABLE search_hit (
    watchlist_id INTEGER NOT NULL REFERENCES watchlist (id) ON DELETE CASCADE,
    video_id     INTEGER NOT NULL REFERENCES video (id) ON DELETE CASCADE,
    query        TEXT NOT NULL,
    found_at     TEXT NOT NULL,
    PRIMARY KEY (watchlist_id, video_id, query)
);
"""

# Version 3: the Author's Channel a Watchlist serves gets a name of its own, apart from the
# ``channel_id`` foreign keys to Reference channels (``video``, ``watchlist_channel``).
V3 = """
ALTER TABLE watchlist RENAME COLUMN channel_id TO author_channel;
"""

# Version 4 (scout): how far a channel's uploads are known without a gap. ``uploads_through`` is the
# publish time of the newest upload a scout run saw on a run that then paged down, unbroken, to
# what the store already had from uploads (or to the backfill target, or the end of the list).
V4 = """
ALTER TABLE channel ADD COLUMN uploads_through TEXT;
"""

MIGRATIONS: list[str] = [V1, V2, V3, V4]  # MIGRATIONS[i] takes the store from version i to i + 1
SCHEMA_VERSION = len(MIGRATIONS)


class Store:
    """An open research database. Use as a context manager or call ``close``."""

    def __init__(self, conn: sqlite3.Connection, path: Path | None = None):
        self.conn = conn
        self.path = path

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    def close(self) -> None:
        self.conn.close()

    def schema_version(self) -> int:
        return int(self.conn.execute("PRAGMA user_version").fetchone()[0])

    def tables(self) -> list[str]:
        rows = self.conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name").fetchall()
        return [r[0] for r in rows]

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        """Commit on success, roll back on error."""
        with self.conn:
            yield self.conn

    def query(self, sql: str, params: tuple | dict = ()) -> list[dict]:
        return [dict(r) for r in self.conn.execute(sql, params).fetchall()]

    def one(self, sql: str, params: tuple | dict = ()) -> dict | None:
        row = self.conn.execute(sql, params).fetchone()
        return dict(row) if row is not None else None

    def migrate(self) -> None:
        version = self.schema_version()
        if version > SCHEMA_VERSION:
            raise StoreError(f"database {self.path} is schema version {version}, newer than this "
                             f"code ({SCHEMA_VERSION}); update the repo")
        for v in range(version, SCHEMA_VERSION):
            try:
                self.conn.executescript(
                    f"BEGIN;\n{MIGRATIONS[v]}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
            except sqlite3.Error as exc:
                self.conn.rollback()
                raise StoreError(f"migration to schema version {v + 1} failed: {exc}") from exc


def open_store(path: str | Path | None = None, *, seed: bool = True) -> Store:
    """Open (creating if needed) the store at ``path`` or ``default_db_path()``.

    Migrates to ``SCHEMA_VERSION`` and, unless ``seed`` is false, loads the
    taxonomy seed from the repo (new values only; existing rows keep their status).
    """
    p = Path(path).expanduser() if path is not None else default_db_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(p)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    s = Store(conn, p)
    try:
        s.migrate()
        if seed:
            from cf.research import taxonomy
            taxonomy.load_seed(s)
    except Exception:
        s.close()
        raise
    return s


def dumps(value: Any) -> str:
    """Compact JSON for a JSON column."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
