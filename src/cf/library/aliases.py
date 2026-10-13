"""After an index run: the old ref of a renamed Asset becomes an alias, and Author rows follow an Asset whose id
moved to another of its variants."""

from __future__ import annotations

from cf.library import author, refs
from cf.research.store import Store


def after_index(store: Store, pack_id: str, built: list[dict], prev_assets: dict[str, dict]) -> int:
    current = {refs.make(a["category"], a["name"]): a["id"] for a in built}
    written = 0
    for a in built:
        old = prev_assets.get(a.get("_prev_id") or a["id"])
        if old is None or (old["category"], old["name"]) == (a["category"], a["name"]):
            continue
        ref = refs.make(old["category"], old["name"])
        if current.get(ref, a["id"]) != a["id"]:
            continue
        author.add_alias(store, ref, a["id"], "rename")
        written += 1
    rekey(store, built)
    return written


def rekey(store: Store, built: list[dict]) -> None:
    have = {r["asset_id"] for r in store.query("SELECT asset_id FROM asset_author")}
    with store.transaction() as c:
        for a in built:
            olds = [v["content_id"] for v in a["variants"] if v["content_id"] != a["id"]]
            if a.get("_prev_id") and a["_prev_id"] != a["id"]:
                olds.insert(0, a["_prev_id"])
            for old in olds:
                if old in have and a["id"] not in have:
                    c.execute("UPDATE asset_author SET asset_id = ? WHERE asset_id = ?", (a["id"], old))
                    have.discard(old)
                    have.add(a["id"])
                c.execute("UPDATE asset_alias SET asset_id = ? WHERE asset_id = ?", (a["id"], old))
