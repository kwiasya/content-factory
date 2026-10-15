"""The research store: one SQLite file at the shared root (ADR 0013).

Path: ``--db`` on the CLI, else ``CF_FACTORY_DB``, else ``<shared root>/factory.db``. The two roots:
the local root (``CF_LOCAL_ROOT``, else the deprecated ``CF_FOOTAGE_ROOT``, else
``~/Movies/content-factory``: Footage, videos, channels) and the shared root (``CF_SHARED_ROOT``, else
``/Users/Shared/content-factory``: factory.db, references, library, packs, secrets.env, backups). The
variables come from the shell or the personal ``<repo>/.env``, read on the first lookup. The default
path is never created (only ``db init`` creates it); the journal stays ``delete``; only the CLI
migrates. Every table of the research spec is created up front (schema version in
``PRAGMA user_version``); later versions append to ``MIGRATIONS``. Opening also adds taxonomy seed
values the store lacks.

JSON columns hold text; ``Store.query`` returns plain dicts.
"""

from __future__ import annotations

import getpass
import json
import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

DEFAULT_LOCAL_ROOT = Path.home() / "Movies" / "content-factory"
DEFAULT_SHARED_ROOT = Path("/Users/Shared/content-factory")
BUSY_TIMEOUT_S = 10
REPO_ROOT = Path(__file__).resolve().parents[3]  # the repo checkout (taxonomy seed, templates, formats/)


class StoreError(Exception):
    """The database cannot be opened or a write breaks a store rule."""


class StoreMissing(StoreError):
    """There is no store file at the path and the caller may not create one."""


class SchemaMismatch(StoreError):
    """The store is at another schema version and the caller may not migrate it."""

    def __init__(self, message: str, version: int):
        super().__init__(message)
        self.version = version


class StoreBusy(StoreError):
    """Another process or Mac holds the write lock longer than the busy timeout."""


BUSY_MESSAGE = "the store is busy: another process or Mac is writing or migrating; retry in a moment"


def is_busy(exc: BaseException) -> bool:
    """True for sqlite's "database is locked" / "busy" errors."""
    text = str(exc).lower()
    return isinstance(exc, sqlite3.OperationalError) and ("locked" in text or "busy" in text)


_env_loaded = False


def _env(var: str) -> str | None:
    global _env_loaded
    if not _env_loaded:
        _env_loaded = True
        from cf.research import env
        env.load_env()
    return os.environ.get(var) or None


def local_root() -> Path:
    """``CF_LOCAL_ROOT``, else ``CF_FOOTAGE_ROOT`` (deprecated), else ``~/Movies/content-factory``: Footage,
    videos/, channels/, _models/ of the person on this Mac."""
    env = _env("CF_LOCAL_ROOT") or _env("CF_FOOTAGE_ROOT")
    return Path(env).expanduser() if env else DEFAULT_LOCAL_ROOT


def shared_root() -> Path:
    """``CF_SHARED_ROOT``, else ``/Users/Shared/content-factory``: factory.db, references/, library/, packs/,
    secrets.env and backups/, one folder for both people (ADR 0013)."""
    env = _env("CF_SHARED_ROOT")
    return Path(env).expanduser() if env else DEFAULT_SHARED_ROOT


def person() -> str:
    """``CF_PERSON``, else the macOS user name: the owner of rows that point at local things (ADR 0013)."""
    return _env("CF_PERSON") or getpass.getuser()


def mount_hint(root: Path) -> str:
    return (f"the shared root {root} is not available; on Nastya's Mac connect to smb://<author-mac>.local/Shared "
            f"(it mounts at /Volumes/Shared); on the author's Mac check the symlink {root} (docs/shared-setup.md)")


def ensure_shared_root(root: Path | None = None) -> Path:
    """``root`` (default: the shared root) when it is a directory; ``StoreError`` with the mount hint otherwise.
    Writers of shared files call it first, so an unmounted share never gets local files in its place."""
    r = Path(root) if root is not None else shared_root()
    if not r.is_dir():
        raise StoreError(mount_hint(r))
    return r


def default_db_path(root: Path | None = None) -> Path:
    """``CF_FACTORY_DB`` or ``<root>/factory.db`` (``root`` defaults to the shared root)."""
    env = _env("CF_FACTORY_DB")
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

# Version 10 (ADR 0013): two people share the store; rows naming something under a person's local root carry
# its owner (CF_PERSON): the Idea's Brief, a Video Note, the Idea <-> Video link. '' = the author's, from before.
V10 = """
ALTER TABLE idea ADD COLUMN brief_owner TEXT;
ALTER TABLE note ADD COLUMN owner TEXT NOT NULL DEFAULT '';
CREATE TABLE idea_video_new (
    idea_id     INTEGER NOT NULL REFERENCES idea (id) ON DELETE CASCADE,
    owner       TEXT NOT NULL DEFAULT '',
    video_slug  TEXT NOT NULL,
    linked_at   TEXT NOT NULL,
    PRIMARY KEY (idea_id, owner, video_slug)
);
INSERT INTO idea_video_new (idea_id, owner, video_slug, linked_at) SELECT idea_id, '', video_slug, linked_at FROM idea_video;
DROP TABLE idea_video;
ALTER TABLE idea_video_new RENAME TO idea_video;
CREATE INDEX idea_video_slug ON idea_video (video_slug);
"""

PLATFORMS = ("youtube", "instagram")

MIGRATIONS: list[str] = [V1, V2, V3, V4, V5, V6, V7, V8, V9, V10]  # MIGRATIONS[i] takes the store from version i to i + 1
SCHEMA_VERSION = len(MIGRATIONS)


OLD_NUMBERING_HINT = ("this store was migrated by the pre-merge code (Library as V6, idea_video as V7); "
                      "run `python -m cf.research db renumber` first")


def old_numbering(conn: sqlite3.Connection) -> bool:
    """True for a store migrated by the pre-merge code: the Library as V6 and idea_video as V7, no Instagram tables."""
    version = int(conn.execute("PRAGMA user_version").fetchone()[0])
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    return version in (6, 7) and "pack" in names and "insight" not in names


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
        if old_numbering(self.conn):
            raise StoreError(f"{self.path}: {OLD_NUMBERING_HINT}")
        if self.schema_version() > 0 and self.path is not None:
            from cf.research import backup
            backup.backup(self.conn, self.path, f"pre-v{SCHEMA_VERSION}")
        try:
            self.conn.execute("BEGIN IMMEDIATE")
        except sqlite3.OperationalError as exc:
            if is_busy(exc):
                raise StoreBusy(BUSY_MESSAGE) from exc
            raise
        try:
            version = self.schema_version()
            if old_numbering(self.conn):
                raise StoreError(f"{self.path}: {OLD_NUMBERING_HINT}")
            if version > SCHEMA_VERSION:
                raise StoreError(f"database {self.path} is schema version {version}, newer than this "
                                 f"code ({SCHEMA_VERSION}); update the repo")
            for v in range(version, SCHEMA_VERSION):
                try:
                    for stmt in _statements(MIGRATIONS[v]):
                        self.conn.execute(stmt)
                    self.conn.execute(f"PRAGMA user_version = {v + 1}")
                except sqlite3.Error as exc:
                    if is_busy(exc):
                        raise StoreBusy(BUSY_MESSAGE) from exc
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


def missing_message(p: Path) -> str:
    """Why there is no store at ``p`` and what to do: the mount hint when the folder that should hold it (the
    shared root) is not there, else ``db init``."""
    if not p.parent.is_dir():
        return f"no research store at {p}: {mount_hint(p.parent)}"
    return f"no research store at {p}; `python -m cf.research db init` creates it"


def connect(p: Path, *, readonly: bool = False) -> sqlite3.Connection:
    """A connection to the store file at ``p`` with the busy timeout; ``readonly`` opens it ``mode=ro``."""
    if readonly:
        conn = sqlite3.connect(f"{Path(p).resolve().as_uri()}?mode=ro", uri=True, timeout=BUSY_TIMEOUT_S)
    else:
        conn = sqlite3.connect(p, timeout=BUSY_TIMEOUT_S)
    conn.row_factory = sqlite3.Row
    return conn


def journal_mode(conn: sqlite3.Connection) -> str:
    return str(conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()


def open_store(path: str | Path | None = None, *, seed: bool = True, create: bool = False,
               migrate: bool = True) -> Store:
    """Open the store at ``path`` or ``default_db_path()``.

    Only ``create=True`` creates a missing file and its folder (``db init``, test fixtures); otherwise a
    missing file, at the default path or an explicit ``--db``, raises ``StoreMissing`` with the
    ``db init`` hint (or the mount hint when its folder is not there). A dangling symlink on the way
    (the share not mounted) is refused even with ``create=True``. The journal must be ``delete`` (WAL does not work over SMB). With
    ``migrate`` the store is brought to ``SCHEMA_VERSION``; without it another version raises
    ``SchemaMismatch``. Unless ``seed`` is false, taxonomy seed values the store lacks are added
    (nothing is written when none is missing).
    """
    p = Path(path).expanduser() if path is not None else default_db_path()
    if not p.exists():
        if not create:
            raise StoreMissing(missing_message(p))
        dangling = next((a for a in (p, *p.parents) if a.is_symlink() and not a.exists()), None)
        if dangling is not None:
            raise StoreMissing(f"cannot create {p}: {dangling} is a symlink to a missing folder; "
                               f"{mount_hint(dangling)}")
        p.parent.mkdir(parents=True, exist_ok=True)
    conn = connect(p)
    conn.execute("PRAGMA foreign_keys = ON")
    s = Store(conn, p)
    try:
        mode = journal_mode(conn)
        if mode == "wal":
            raise StoreError(f"{p} is in WAL mode; WAL does not work over SMB; switch it back with "
                             "`sqlite3 factory.db 'PRAGMA journal_mode=DELETE'` while nobody runs anything")
        version = s.schema_version()
        if version != SCHEMA_VERSION and not migrate:
            raise SchemaMismatch(f"the research store {p} is schema version {version}, this code reads "
                                 f"{SCHEMA_VERSION}; `python -m cf.research db migrate` migrates it", version)
        s.migrate()
        if seed:
            from cf.research import taxonomy
            taxonomy.load_seed(s)
    except sqlite3.OperationalError as exc:
        s.close()
        if is_busy(exc):
            raise StoreBusy(BUSY_MESSAGE) from exc
        raise
    except BaseException:
        s.close()
        raise
    return s


def dumps(value: Any) -> str:
    """Compact JSON for a JSON column."""
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))
