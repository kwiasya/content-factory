"""Turn recorded Data API payloads into store rows.

``*_row`` functions are pure (payload item → dict of column values);
``ingest_*`` functions upsert those rows and return the store ids. This is the
layer tests feed with fixtures; the network never reaches past ``youtube``.
"""

from __future__ import annotations

from cf.research.store import Store, dumps, now_iso


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_handle(handle: str | None) -> str | None:
    """``@name`` lowercase, or None."""
    if not handle:
        return None
    return "@" + handle.strip().lstrip("@").lower()


def channel_row(item: dict) -> dict:
    """Column values of ``channel`` from one ``channels.list`` item (own flag not included)."""
    sn = item.get("snippet") or {}
    stats = item.get("statistics") or {}
    uploads = ((item.get("contentDetails") or {}).get("relatedPlaylists") or {}).get("uploads")
    return {
        "platform": "youtube",
        "external_id": item["id"],
        "handle": normalize_handle(sn.get("customUrl")),
        "title": sn.get("title"),
        "description": sn.get("description"),
        "country": sn.get("country"),
        "published_at": sn.get("publishedAt"),
        "subscriber_count": None if stats.get("hiddenSubscriberCount") else _int(stats.get("subscriberCount")),
        "video_count": _int(stats.get("videoCount")),
        "view_count": _int(stats.get("viewCount")),
        "uploads_playlist_id": uploads,
        "raw": dumps(item),
    }


def ingest_channels(store: Store, payload: dict, *, own: bool | None = None,
                    fetched_at: str | None = None) -> list[int]:
    """Upsert every channel in a ``channels.list`` payload; return their store ids in payload order.

    ``own`` sets the own flag when given; None keeps what the store has (new rows: not own).
    """
    ts = fetched_at or now_iso()
    ids: list[int] = []
    with store.transaction() as c:
        for item in payload.get("items") or []:
            row = channel_row(item)
            row["fetched_at"] = ts
            row["own"] = int(bool(own))
            cols = list(row)
            updates = [f"{k} = excluded.{k}" for k in cols if k not in ("platform", "external_id", "own")]
            if own is not None:
                updates.append("own = excluded.own")
            c.execute(
                f"INSERT INTO channel ({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)}) "
                f"ON CONFLICT (platform, external_id) DO UPDATE SET {', '.join(updates)}",
                tuple(row.values()))
            got = c.execute("SELECT id FROM channel WHERE platform = ? AND external_id = ?",
                            (row["platform"], row["external_id"])).fetchone()
            ids.append(int(got[0]))
    return ids
