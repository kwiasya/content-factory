"""Reference cards, schema ``cf-reference-card/1``.

A card has two sections: ``measured`` (computed by ``measure`` from the
Reference folder's artifacts, rewritten on every fetch) and ``analysis``
(written by the Editor with the Sandcastles fields; None until then). Measuring
again never touches the analysis. The store row (table ``card``) is the source
of truth; ``card.json`` in the Reference folder is a copy for humans.
"""

from __future__ import annotations

import json
from pathlib import Path

from cf.research.store import Store, dumps, now_iso

SCHEMA = "cf-reference-card/1"


def _card(row: dict) -> dict:
    return {"schema": row["schema"], "measured": json.loads(row["measured"]),
            "analysis": None if row["analysis"] is None else json.loads(row["analysis"])}


def load(store: Store, video_id: int) -> dict | None:
    """The card of a video (store id), or None."""
    row = store.one("SELECT schema, measured, analysis FROM card WHERE video_id = ?", (video_id,))
    return None if row is None else _card(row)


def save(store: Store, video_id: int, measured: dict, *, path: Path | None = None) -> dict:
    """Write the measured section (analysis kept, or None for a new card); also to ``path`` if given."""
    with store.transaction() as c:
        c.execute("INSERT INTO card (video_id, schema, measured, analysis, written_at) VALUES (?, ?, ?, NULL, ?) "
                  "ON CONFLICT (video_id) DO UPDATE SET schema = excluded.schema, measured = excluded.measured, "
                  "written_at = excluded.written_at",
                  (video_id, SCHEMA, dumps(measured), now_iso()))
    saved = load(store, video_id)
    if path is not None:
        write_json(saved, path)
    return saved


def write_json(card: dict, path: Path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(card, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(path)
