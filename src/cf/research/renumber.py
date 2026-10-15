"""Repair the schema numbering of a store migrated by the pre-merge code (``db renumber``).

Before Instagram (V6) and the Library were merged, one checkout numbered the Library as V6 and
``idea_video`` as V7. Such a store (``store.old_numbering``: version 6 or 7, ``pack`` present,
``insight`` absent) cannot be migrated by the current code: its V7 would create ``pack`` again.
``renumber`` backs the file up (``pre-renumber``), adds what the current V6 adds and the store
lacks (platforms, ``video_platform``, ``video.marks``, ``insight``, ``watchlist_pick``, ``rate``,
``rate_pressure``) in one ``BEGIN IMMEDIATE``, sets the version the current numbering gives that
shape (7 without ``idea_video``, 8 with it), then opens the store the normal way so the remaining
migrations run. A store already in the current numbering is left alone; any other shape is refused.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path

from cf.research import backup
from cf.research import store as st


def _tables(conn: sqlite3.Connection) -> list[str]:
    return [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")]


def _columns(conn: sqlite3.Connection, table: str) -> set[str]:
    return {r[1] for r in conn.execute(f"PRAGMA table_info({table})")}


def counts(conn: sqlite3.Connection) -> dict[str, int]:
    """Rows per table."""
    return {t: int(conn.execute(f'SELECT count(*) FROM "{t}"').fetchone()[0]) for t in _tables(conn)}


def _v6_missing(conn: sqlite3.Connection) -> list[str]:
    out = []
    for stmt in st._statements(st.V6):
        if stmt.startswith("ALTER TABLE video ADD COLUMN marks"):
            if "marks" not in _columns(conn, "video"):
                out.append(stmt)
        elif stmt.startswith("CREATE TABLE "):
            out.append(stmt.replace("CREATE TABLE ", "CREATE TABLE IF NOT EXISTS ", 1))
        elif stmt.startswith("CREATE INDEX "):
            out.append(stmt.replace("CREATE INDEX ", "CREATE INDEX IF NOT EXISTS ", 1))
        else:
            out.append(stmt)
    return out


def _target_version(conn: sqlite3.Connection, version: int) -> int:
    has_idea_video = "idea_video" in _tables(conn)
    has_hidden = "hidden_agent_tags" in _columns(conn, "asset_author")
    if version == 7:
        if not (has_idea_video and has_hidden):
            raise st.StoreError("an old-numbering store at version 7 must have idea_video and "
                                "asset_author.hidden_agent_tags; this one does not, renumber refused")
        return 8
    if has_idea_video or has_hidden:
        raise st.StoreError("an old-numbering store at version 6 must not have idea_video yet; renumber refused")
    return 7


def renumber(path: str | Path) -> dict:
    """Renumber the store at ``path`` and migrate it to ``SCHEMA_VERSION``; see the module docstring."""
    p = Path(path).expanduser()
    if not p.is_file():
        raise st.StoreError(f"no research store at {p}")
    conn = sqlite3.connect(p, timeout=st.BUSY_TIMEOUT_S)
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        before = counts(conn)
        version = int(conn.execute("PRAGMA user_version").fetchone()[0])
        if not st.old_numbering(conn):
            if version >= 8 and "insight" in before:
                return {"path": str(p), "renumbered": False, "from_version": version, "backup": None,
                        "counts_before": before}
            raise st.StoreError(f"{p} (schema version {version}) is not in the old numbering "
                                "(version 6 or 7 with pack and without insight); nothing to renumber")
        saved = backup.backup(conn, p, "pre-renumber")
        conn.execute("BEGIN IMMEDIATE")
        try:
            if not st.old_numbering(conn):
                conn.rollback()
                return {"path": str(p), "renumbered": False, "from_version": version, "backup": str(saved),
                        "counts_before": before}
            version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            target = _target_version(conn, version)
            for stmt in _v6_missing(conn):
                conn.execute(stmt)
            conn.execute(f"PRAGMA user_version = {target}")
        except BaseException:
            conn.rollback()
            raise
        conn.commit()
    finally:
        conn.close()
    with st.open_store(p, seed=False) as s:
        after = counts(s.conn)
        final = s.schema_version()
    changed = {t: (n, after.get(t)) for t, n in before.items() if after.get(t) != n}
    return {"path": str(p), "renumbered": True, "from_version": version, "renumbered_to": target,
            "version": final, "backup": str(saved), "counts_before": before, "counts_after": after,
            "changed": changed}
