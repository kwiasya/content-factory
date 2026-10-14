"""The Author's fields of an Asset (``asset_author``) and the aliases they leave behind (``asset_alias``)."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any

from cf.library import refs
from cf.library.errors import AssetNotFound, FieldInvalid, RefNameInvalid, RefTaken
from cf.research.store import Store, dumps, now_iso

if TYPE_CHECKING:
    from cf.library.library import Asset, Library

MAX_TAG = 40
MAX_CAPTION = 300


class _Unset:
    def __repr__(self) -> str:
        return "UNSET"


UNSET: Any = _Unset()
JSON_COLUMNS = ("tags", "hidden_agent_tags")


def _json_tags(raw: str | None) -> list[str]:
    try:
        value = json.loads(raw or "[]")
    except ValueError:
        return []
    return [t for t in value if isinstance(t, str)] if isinstance(value, list) else []


def rows(store: Store) -> dict[str, dict]:
    out = {}
    for r in store.query("SELECT * FROM asset_author"):
        for col in JSON_COLUMNS:
            r[col] = _json_tags(r.get(col))
        out[r["asset_id"]] = r
    return out


def alias_rows(store: Store) -> list[dict]:
    return store.query("SELECT ref, asset_id, source, created_at FROM asset_alias ORDER BY ref")


def normalise_tags(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or not all(isinstance(t, str) for t in value):
        raise FieldInvalid("tags_invalid", "tags must be a list of strings", detail="list")
    out, seen = [], set()
    for t in value:
        t = " ".join(t.split())
        if not t:
            continue
        if "," in t:
            raise FieldInvalid("tags_invalid", f"tag {t!r} contains a comma", detail="comma", tag=t)
        if len(t) > MAX_TAG:
            raise FieldInvalid("tags_invalid", f"tag {t[:20]!r}… is longer than {MAX_TAG} characters",
                               detail="length", tag=t[:20])
        if t.lower() not in seen:
            seen.add(t.lower())
            out.append(t)
    return out


def _caption(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise FieldInvalid("caption_invalid", "caption must be a string")
    value = " ".join(value.split())
    if len(value) > MAX_CAPTION:
        raise FieldInvalid("caption_invalid", f"caption is longer than {MAX_CAPTION} characters")
    return value or None


def _rights(value: Any) -> str | None:
    if value is None:
        return None
    if value not in refs.RIGHTS:
        raise FieldInvalid("rights_invalid", f"rights {value!r} must be one of {', '.join(refs.RIGHTS)}",
                           rights=str(value), values=", ".join(refs.RIGHTS))
    return value


def check_name(library: "Library", asset: "Asset", name: str) -> str:
    if not isinstance(name, str) or not name:
        raise RefNameInvalid(str(name), "item")
    clean = refs.slug(name)
    if clean != name:
        raise RefNameInvalid(name, clean)
    ref = refs.make(asset.category, name)
    hit = library.lookup(ref)
    if hit is not None and hit[0].id != asset.id:
        raise RefTaken(ref, hit[0].ref, hit[0].id, hit[0].primary["path"])
    return name


def write(store: Store, asset_id: str, pack_id: str, fields: dict) -> None:
    if not fields:
        return
    cols = {"asset_id": asset_id, "pack_id": pack_id, "updated_at": now_iso(), **fields}
    for col in JSON_COLUMNS:
        if col in cols:
            cols[col] = dumps(cols[col])
    names = ", ".join(cols)
    marks = ", ".join("?" for _ in cols)
    updates = ", ".join(f"{k} = excluded.{k}" for k in cols if k != "asset_id")
    with store.transaction() as c:
        c.execute(f"INSERT INTO asset_author ({names}) VALUES ({marks}) "
                  f"ON CONFLICT (asset_id) DO UPDATE SET {updates}", tuple(cols.values()))


def add_alias(store: Store, ref: str, asset_id: str, source: str) -> None:
    with store.transaction() as c:
        c.execute("INSERT INTO asset_alias (ref, asset_id, source, created_at) VALUES (?, ?, ?, ?) "
                  "ON CONFLICT (ref) DO UPDATE SET asset_id = excluded.asset_id, source = excluded.source",
                  (ref, asset_id, source, now_iso()))


def drop_alias(store: Store, ref: str, asset_id: str) -> None:
    with store.transaction() as c:
        c.execute("DELETE FROM asset_alias WHERE ref = ? AND asset_id = ?", (ref, asset_id))


def set_author(store: Store, library: "Library", asset_id: str, *, caption: Any = UNSET, tags: Any = UNSET,
               rights: Any = UNSET, name: Any = UNSET, hidden_agent_tags: Any = UNSET) -> "Asset":
    from cf.library.library import load

    asset = library.get(asset_id)
    if asset is None:
        raise AssetNotFound(asset_id)
    fields: dict[str, Any] = {}
    if caption is not UNSET:
        fields["caption"] = _caption(caption)
    if tags is not UNSET:
        fields["tags"] = normalise_tags(tags)
    if hidden_agent_tags is not UNSET:
        fields["hidden_agent_tags"] = normalise_tags(hidden_agent_tags)
    if rights is not UNSET:
        fields["rights"] = _rights(rights)
    if name is not UNSET:
        if name is not None and not isinstance(name, str):
            raise RefNameInvalid(str(name), refs.slug(str(name)))
        new = check_name(library, asset, name) if name else None
        prev = asset.author_name
        if prev and prev != new:
            add_alias(store, refs.make(asset.category, prev), asset.id, "author")
        if new:
            drop_alias(store, refs.make(asset.category, new), asset.id)
        fields["name"] = new
    write(store, asset.id, asset.pack, fields)
    fresh = load(library.footage, store).get(asset.id)
    assert fresh is not None
    return fresh
