"""A store in the pre-merge numbering, built by SQL: V1-V5, the Library as V6, idea_video as V7."""

import sqlite3
from pathlib import Path

from cf.research import store as st


def make_old_store(path: Path, version: int = 7) -> None:
    """Write a store at ``path`` the pre-merge code would have left at ``version`` (6 or 7), with a few rows."""
    conn = sqlite3.connect(path)
    scripts = list(st.MIGRATIONS[:5]) + [st.V7, st.V8][: version - 5]
    for v, script in enumerate(scripts):
        conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
    conn.executescript("""
        INSERT INTO watchlist (name, format_id, author_channel, language, queries, created_at)
            VALUES ('city', 'walk-reel', 'me', 'en', '["old town"]', '2026-10-01T00:00:00Z');
        INSERT INTO channel (platform, external_id, handle, title) VALUES ('', 'UCaaaaaaaaaaaaaaaaaaaaaa', '@alpha', 'A');
        INSERT INTO video (platform, external_id, channel_id, title, published_at)
            VALUES ('youtube', 'vid00000001', 1, 'first', '2026-09-01T00:00:00Z');
        INSERT INTO snapshot (video_id, taken_at, views) VALUES (1, '2026-10-01T00:00:00Z', 10);
        INSERT INTO card (video_id, schema, measured, analysis, written_at)
            VALUES (1, 'reference-card/1', '{}', '{"summary":"s"}', '2026-10-02T00:00:00Z');
        INSERT INTO taxonomy (kind, value, status, source, created_at)
            VALUES ('hook', 'old_proposal', 'proposed', 'agent', '2026-10-01T00:00:00Z');
        INSERT INTO quota (day, bucket, method, calls, units) VALUES ('2026-10-01', 'youtube', 'videos.list', 2, 2);
        INSERT INTO pack (id, root, config, created_at) VALUES ('tpl', '/x/tpl', '{}', '2026-10-01T00:00:00Z');
        INSERT INTO asset_author (asset_id, pack_id, name, updated_at) VALUES ('a1', 'tpl', 'one', 'x');
        INSERT INTO asset_alias (ref, asset_id, source, created_at) VALUES ('@face/one', 'a1', 'catalog', 'x');
    """)
    conn.close()
