"""The research store: one SQLite file at the shared root.

Path: ``--db`` on the CLI, else ``CF_FACTORY_DB``, else
``<shared root>/factory.db`` where the shared root is ``CF_SHARED_ROOT`` or
``~/Movies/content-factory``. The two roots: the local root (``CF_LOCAL_ROOT``: Footage,
videos, channels) and the shared root (``CF_SHARED_ROOT``: factory.db, references, library);
``CF_FOOTAGE_ROOT`` is a deprecated fallback for both. Every table of the research spec is created up
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

DEFAULT_ROOT = Path.home() / "Movies" / "content-factory"
REPO_ROOT = Path(__file__).resolve().parents[3]  # the repo checkout (taxonomy seed, templates, formats/)


class StoreError(Exception):
    """The database cannot be opened or a write breaks a store rule."""


class RootsError(StoreError):
    """The local and shared roots differ where only one root is supported yet."""


def _root(var: str) -> Path:
    env = os.environ.get(var) or os.environ.get("CF_FOOTAGE_ROOT")
    return Path(env).expanduser() if env else DEFAULT_ROOT


def local_root() -> Path:
    """``CF_LOCAL_ROOT``, else ``CF_FOOTAGE_ROOT`` (deprecated), else ``~/Movies/content-factory``."""
    return _root("CF_LOCAL_ROOT")


def shared_root() -> Path:
    """``CF_SHARED_ROOT``, else ``CF_FOOTAGE_ROOT`` (deprecated), else ``~/Movies/content-factory``."""
    return _root("CF_SHARED_ROOT")


def single_root() -> Path:
    """The local root when both roots are the same folder; ``RootsError`` otherwise."""
    local, shared = local_root(), shared_root()
    if local.resolve() != shared.resolve():
        raise RootsError(f"CF_LOCAL_ROOT {local} and CF_SHARED_ROOT {shared} differ; "
                         "separate roots are not supported yet (one root for now)")
    return local


def default_db_path(root: Path | None = None) -> Path:
    """``CF_FACTORY_DB`` or ``<root>/factory.db`` (``root`` defaults to the shared root)."""
    env = os.environ.get("CF_FACTORY_DB")
    return Path(env).expanduser() if env else Path(root or shared_root()) / "factory.db"


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

V5 = """
CREATE TABLE note (
    id          INTEGER PRIMARY KEY,
    kind        TEXT NOT NULL,
    key         TEXT NOT NULL,
    text        TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    resolved_at TEXT
);
CREATE INDEX note_open ON note (kind, key) WHERE resolved_at IS NULL;
"""

# Version 6 (Instagram, ADR 0010). ``channel.platform`` and ``video.platform`` exist since V1 with
# 'youtube' as the default; this version makes sure no row is left without one, then adds:
# - ``insight``: the Author's own reels' Graph API insights (reach, saves, shares, watch time) over time;
# - ``video.marks``: the Author's labels on a Reference (own reels: hypothesis tests such as ``closeup_emotion``);
# - ``watchlist_pick``: References the Author picked by hand into a Watchlist (a reel link, any owner or none);
# - ``rate`` and ``rate_pressure``: per-minute call counts of the hourly buckets (Instagram: about 200 calls an
#   hour per user) and the last usage share Meta reported in its headers.
V6 = """
UPDATE channel SET platform = 'youtube' WHERE platform IS NULL OR platform = '';
UPDATE video SET platform = 'youtube' WHERE platform IS NULL OR platform = '';
CREATE INDEX video_platform ON video (platform, channel_id);
ALTER TABLE video ADD COLUMN marks TEXT NOT NULL DEFAULT '[]';
CREATE TABLE insight (
    id             INTEGER PRIMARY KEY,
    video_id       INTEGER NOT NULL REFERENCES video (id) ON DELETE CASCADE,
    taken_at       TEXT NOT NULL,
    views          INTEGER,
    reach          INTEGER,
    likes          INTEGER,
    comments       INTEGER,
    saved          INTEGER,
    shares         INTEGER,
    interactions   INTEGER,
    avg_watch_ms   INTEGER,
    total_watch_ms INTEGER,
    UNIQUE (video_id, taken_at)
);
CREATE TABLE watchlist_pick (
    watchlist_id INTEGER NOT NULL REFERENCES watchlist (id) ON DELETE CASCADE,
    video_id     INTEGER NOT NULL REFERENCES video (id) ON DELETE CASCADE,
    added_at     TEXT NOT NULL,
    PRIMARY KEY (watchlist_id, video_id)
);
CREATE TABLE rate (
    minute TEXT NOT NULL,
    bucket TEXT NOT NULL,
    method TEXT NOT NULL,
    calls  INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (minute, method)
);
CREATE TABLE rate_pressure (
    bucket         TEXT PRIMARY KEY,
    seen_at        TEXT NOT NULL,
    pct            INTEGER NOT NULL,
    regain_minutes INTEGER NOT NULL DEFAULT 0
);
"""
# Version 7: the Library (ADR 0007, Packs read in place): Packs, the Author's side of each Asset, aliases.
V7 = """
CREATE TABLE pack (
    id          TEXT PRIMARY KEY,
    root        TEXT NOT NULL,
    config      TEXT NOT NULL,
    created_at  TEXT NOT NULL,
    indexed_at  TEXT
);
CREATE TABLE asset_author (
    asset_id    TEXT PRIMARY KEY,
    pack_id     TEXT NOT NULL,
    name        TEXT,
    caption     TEXT,
    tags        TEXT NOT NULL DEFAULT '[]',
    rights      TEXT,
    updated_at  TEXT NOT NULL
);
CREATE TABLE asset_alias (
    ref         TEXT PRIMARY KEY,
    asset_id    TEXT NOT NULL,
    source      TEXT NOT NULL,
    created_at  TEXT NOT NULL
);
CREATE INDEX asset_alias_asset ON asset_alias (asset_id);
"""

# Version 8: the Idea side of the Idea <-> Video link (ADR 0006); video.json "ideas" is the Video side;
# the agent tags the Author hid on an Asset.
V8 = """
CREATE TABLE idea_video (
    idea_id     INTEGER NOT NULL REFERENCES idea (id) ON DELETE CASCADE,
    video_slug  TEXT NOT NULL,
    linked_at   TEXT NOT NULL,
    PRIMARY KEY (idea_id, video_slug)
);
CREATE INDEX idea_video_slug ON idea_video (video_slug);
ALTER TABLE asset_author ADD COLUMN hidden_agent_tags TEXT NOT NULL DEFAULT '[]';
"""

# Version 9: the Walk is now Footage (ADR 0012); Notes keyed by the renamed skill ingest-footage follow it.
V9 = """
UPDATE note SET key = 'ingest-footage' WHERE kind = 'skill' AND key = 'ingest-walk';
UPDATE note SET key = '.claude/skills/ingest-footage/' || substr(key, 28)
 WHERE kind = 'document' AND substr(key, 1, 27) = '.claude/skills/ingest-walk/';
"""

PLATFORMS = ("youtube", "instagram")

MIGRATIONS: list[str] = [V1, V2, V3, V4, V5, V6, V7, V8, V9]  # MIGRATIONS[i] takes the store from version i to i + 1
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
        """Bring the database to ``SCHEMA_VERSION``.

        Runs under ``BEGIN IMMEDIATE`` (the write lock) and re-reads the version
        inside it, so several processes opening a fresh file at once apply each
        migration exactly once; the others wait (up to the connection timeout)
        and find the work done.
        """
        if self.schema_version() == SCHEMA_VERSION:
            return
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            version = self.schema_version()
            if version > SCHEMA_VERSION:
                raise StoreError(f"database {self.path} is schema version {version}, newer than this "
                                 f"code ({SCHEMA_VERSION}); update the repo")
            for v in range(version, SCHEMA_VERSION):
                try:
                    for stmt in _statements(MIGRATIONS[v]):
                        self.conn.execute(stmt)
                    self.conn.execute(f"PRAGMA user_version = {v + 1}")
                except sqlite3.Error as exc:
                    raise StoreError(f"migration to schema version {v + 1} failed: {exc}") from exc
        except BaseException:
            self.conn.rollback()
            raise
        self.conn.commit()


def _statements(script: str) -> list[str]:
    """The SQL statements of a migration script, one by one (``executescript`` would commit first)."""
    out, buf = [], ""
    for line in script.splitlines(keepends=True):
        buf += line
        if sqlite3.complete_statement(buf):
            out.append(buf.strip())
            buf = ""
    if buf.strip():
        raise StoreError(f"incomplete SQL statement in a migration: {buf.strip()[:60]}")
    return out


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
