"""Backups of the research store, next to it in ``backups/``.

``backup`` copies an open connection with SQLite's online backup API (consistent under the
rollback journal) into ``backups/.factory-<ts>-<label>.db.part`` and renames it to
``factory-<YYYYMMDD-HHMM>-<label>.db``. Labels: ``daily`` (``ensure_daily``: the first CLI
command of the day, after a passing ``quick_check``), ``pre-<command>`` before a bulk command,
``pre-v<N>`` before a migration, ``pre-renumber``, ``pre-merge``, ``manual`` and any label given
to ``db backup --label``. ``prune`` keeps the newest 14 ``daily`` and the newest 10 bulk-command
backups (``BULK_LABELS``); every other label is kept until a person removes it.
"""

from __future__ import annotations

import re
import sqlite3
from datetime import datetime
from pathlib import Path

from cf.research.store import StoreError, Store

KEEP_DAILY = 14
KEEP_BULK = 10
BULK_LABELS = frozenset({"pre-scout", "pre-snapshot", "pre-fetch", "pre-index", "pre-pack-remove", "pre-own"})
NAME = re.compile(r"^factory-(\d{8})-(\d{4})-([a-z0-9][a-z0-9-]*)\.db$")
LABEL = re.compile(r"^[a-z0-9][a-z0-9-]*$")


def backups_dir(db_path: Path) -> Path:
    """``backups/`` next to the store file the path resolves to (a symlinked path backs up next to the real file)."""
    return Path(db_path).resolve().parent / "backups"


def backup(conn: sqlite3.Connection, db_path: Path, label: str, now: datetime | None = None) -> Path:
    """Copy the store behind ``conn`` into ``backups/factory-<ts>-<label>.db``; prune; return the file."""
    if not LABEL.match(label):
        raise StoreError(f"backup label {label!r}: use lowercase letters, digits and dashes")
    folder = backups_dir(db_path)
    folder.mkdir(parents=True, exist_ok=True)
    stamp = (now or datetime.now()).strftime("%Y%m%d-%H%M")
    final = folder / f"factory-{stamp}-{label}.db"
    part = folder / f".{final.name}.part"
    part.unlink(missing_ok=True)
    dest = sqlite3.connect(part)
    try:
        conn.backup(dest)
    finally:
        dest.close()
    part.replace(final)
    prune(folder)
    return final


def before(store: Store, label: str) -> Path | None:
    """Back up ``store`` before a bulk command (label ``pre-<command>``); None for a store without a file."""
    if store.path is None:
        return None
    return backup(store.conn, store.path, label)


def listing(folder: Path) -> list[tuple[str, str, Path]]:
    """``(stamp, label, path)`` of every backup file in ``folder``, oldest first."""
    if not folder.is_dir():
        return []
    out = []
    for p in folder.iterdir():
        m = NAME.match(p.name)
        if m:
            out.append((f"{m.group(1)}-{m.group(2)}", m.group(3), p))
    return sorted(out)


def newest_per_label(db_path: Path) -> dict[str, str]:
    """The newest backup file name per label."""
    return {label: p.name for _, label, p in listing(backups_dir(db_path))}


def prune(folder: Path) -> list[Path]:
    """Delete ``daily`` beyond the newest ``KEEP_DAILY`` and bulk-command backups beyond the newest ``KEEP_BULK``."""
    files = listing(folder)
    daily = [p for _, label, p in files if label == "daily"]
    bulk = [p for _, label, p in files if label in BULK_LABELS]
    gone = daily[:-KEEP_DAILY] + bulk[:-KEEP_BULK]
    for p in gone:
        p.unlink(missing_ok=True)
    return gone


def quick_check(conn: sqlite3.Connection) -> str:
    """``PRAGMA quick_check``: ``ok`` or the problems it found, one per line."""
    return "\n".join(str(r[0]) for r in conn.execute("PRAGMA quick_check").fetchall())


def ensure_daily(store: Store, now: datetime | None = None) -> Path | None:
    """Take today's ``daily`` backup unless one exists; refuse a store that fails ``quick_check``."""
    if store.path is None:
        return None
    day = (now or datetime.now()).strftime("%Y%m%d")
    if any(stamp.startswith(day) and label == "daily" for stamp, label, _ in listing(backups_dir(store.path))):
        return None
    result = quick_check(store.conn)
    if result != "ok":
        raise StoreError(f"{store.path} failed quick_check ({result.splitlines()[0]}); do not write to it; "
                         "restore a file from backups/ while nobody runs anything (docs/shared-setup.md)")
    return backup(store.conn, store.path, "daily", now)
