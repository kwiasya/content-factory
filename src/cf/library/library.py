"""The Library: every registered Pack's index merged with the Author's fields and aliases from the store."""

from __future__ import annotations

import difflib
from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from pathlib import Path

from cf.library import author, refs
from cf.library.errors import RefError
from cf.library.index import cache_dir, read_index
from cf.library.packs import PackInfo, list_packs
from cf.research.store import Store

SERVED_KINDS = ("audio", "video", "image", "font")


@dataclass(frozen=True)
class Asset:
    id: str
    pack: str
    root: Path
    cache: Path
    category: str
    category_source: str
    name: str
    author_name: str | None
    kind: str
    folder: str
    group: str | None
    variants: tuple[dict, ...]
    duration_s: float | None
    fps: float | None
    width: int | None
    height: int | None
    has_audio: bool
    alpha: bool
    green_screen: bool
    loudness: dict | None
    derived: dict
    rights_default: str
    rights_override: str | None
    caption: str | None
    tags: tuple[str, ...]
    agent: dict | None
    aliases: tuple[str, ...]
    updated_at: str | None
    hidden_agent_tags: tuple[str, ...] = ()

    @property
    def ref(self) -> str:
        return refs.make(self.category, self.author_name or self.name)

    @property
    def file_ref(self) -> str:
        return refs.make(self.category, self.name)

    @property
    def rights(self) -> str:
        return self.rights_override or self.rights_default

    @property
    def primary(self) -> dict:
        return self.variants[0]

    @property
    def path(self) -> Path:
        return self.root / self.primary["path"]

    def variant(self, role: str) -> dict | None:
        return next((v for v in self.variants if v["role"] == role), None)

    @property
    def alpha_path(self) -> Path | None:
        """A file with an alpha channel Resolve can use: the Pack alpha variant, the keyed or converted cache file,
        or an alpha .mov/.mp4 primary."""
        v = self.variant("alpha")
        if v is not None:
            return self.root / v["path"]
        d = self.derived.get("alpha") or self.derived.get("converted")
        if d:
            return self.cache / d
        if self.primary.get("alpha") and self.path.suffix.lower() in (".mov", ".mp4"):
            return self.path
        return None

    @property
    def png_path(self) -> Path | None:
        d = self.derived.get("png")
        if d:
            return self.cache / d
        v = self.variant("still")
        if v is not None:
            return self.root / v["path"]
        return self.path if self.primary["path"].lower().endswith(".png") else None

    def pack_media(self, rel: str) -> str:
        return f"packs/{self.pack}/{rel}"

    def cache_media(self, sub: str | None) -> str | None:
        return f"library/{self.pack}/{sub}" if sub else None

    @property
    def media(self) -> dict[str, str | None]:
        served = self.kind in SERVED_KINDS
        alpha_v = self.variant("alpha")
        alpha = self.pack_media(alpha_v["path"]) if alpha_v else self.cache_media(
            self.derived.get("alpha") or self.derived.get("converted"))
        png = self.cache_media(self.derived.get("png"))
        if png is None and self.variant("still") is not None:
            png = self.pack_media(self.variant("still")["path"])
        return {"original": self.pack_media(self.primary["path"]) if served else None,
                "alpha": alpha, "png": png,
                "poster": self.cache_media(self.derived.get("poster")),
                "preview": self.cache_media(self.derived.get("preview"))}

    @property
    def agent_caption(self) -> str | None:
        return (self.agent or {}).get("caption")

    @property
    def proposed_agent_tags(self) -> tuple[str, ...]:
        return tuple((self.agent or {}).get("tags") or ())

    @property
    def agent_tags(self) -> tuple[str, ...]:
        """The agent's tags minus those the Author hid."""
        hidden = {t.lower() for t in self.hidden_agent_tags}
        return tuple(t for t in self.proposed_agent_tags if t.lower() not in hidden)

    def author_hits(self, wanted: Iterable[str]) -> int:
        mine = {t.lower() for t in self.tags}
        return sum(1 for t in wanted if t.lower() in mine)

    def all_tags(self) -> list[str]:
        out, seen = [], set()
        for t in (*self.tags, *self.agent_tags):
            if t.lower() not in seen:
                seen.add(t.lower())
                out.append(t)
        return out

    def haystack(self) -> str:
        parts = [self.ref, self.file_ref, self.name, self.author_name or "", *self.aliases, self.caption or "",
                 self.agent_caption or "", *self.tags, *self.agent_tags,
                 *(v["path"].rsplit("/", 1)[-1] for v in self.variants)]
        return "\n".join(parts).lower()


@dataclass(frozen=True)
class PackView:
    info: PackInfo
    index_missing: bool
    indexed_at: str | None
    report: dict


class Library:
    def __init__(self, footage: Path, packs: list[PackView], assets: list[Asset], alias_map: dict[str, str]):
        self.footage = Path(footage)
        self._packs = packs
        self.assets = assets
        self._by_id = {a.id: a for a in assets}
        self._canonical = {a.ref: a for a in assets}
        self._file = {a.file_ref: a for a in assets}
        self._alias = {ref: self._by_id[i] for ref, i in alias_map.items() if i in self._by_id}

    def packs(self) -> list[PackView]:
        return list(self._packs)

    def pack(self, pack_id: str) -> PackView | None:
        return next((p for p in self._packs if p.info.id == pack_id), None)

    def get(self, asset_id: str) -> Asset | None:
        return self._by_id.get(asset_id)

    def lookup(self, ref: str) -> tuple[Asset, bool] | None:
        """The Asset a ref names and whether it was named other than by its canonical ref."""
        refs.parse(ref)
        ref = ref.strip()
        if ref in self._canonical:
            return self._canonical[ref], False
        if ref in self._file:
            return self._file[ref], True
        if ref in self._alias:
            return self._alias[ref], True
        return None

    def resolve(self, ref: str) -> Asset | None:
        hit = self.lookup(ref)
        return hit[0] if hit else None

    def find(self, ref_or_id: str) -> Asset | None:
        if ref_or_id.startswith("@"):
            return self.resolve(ref_or_id)
        return self.get(ref_or_id)

    def suggest(self, q: str, limit: int = 20) -> list[Asset]:
        q = q.strip().lower()
        if not q:
            return sorted(self.assets, key=lambda a: a.ref)[:limit]
        bare = q[1:] if q.startswith("@") else q
        cat, _, rest = bare.partition("/")
        has_cat = "/" in bare

        def rank(a: Asset) -> int | None:
            names = [a.ref.lower(), a.file_ref.lower()]
            if any(n[1:].startswith(bare) for n in names):
                return 0
            if has_cat:
                if cat != a.category:
                    return None
                needle = rest
            else:
                needle = bare
            if needle and any(needle in n.split("/", 1)[1] for n in names):
                return 1
            if not needle:
                return 1
            texts = [a.caption or "", *a.tags]
            if any(needle in t.lower() for t in texts):
                return 2
            if any(needle in t.lower() for t in (a.agent_caption or "", *a.agent_tags)):
                return 3
            return None

        ranked = [(r, a.ref, a) for a in self.assets if (r := rank(a)) is not None]
        ranked.sort(key=lambda x: (x[0], x[1]))
        return [a for _, _, a in ranked[:limit]]

    def nearest(self, ref: str, limit: int = 5) -> list[Asset]:
        try:
            cat, name = refs.parse(ref)
        except RefError:
            return self.suggest(ref, limit)
        out = [a for a in self.suggest(f"{cat}/{name}", limit)]
        if len(out) < limit:
            pool = {a.ref.split("/", 1)[1]: a for a in self.assets if a.category == cat}
            for n in difflib.get_close_matches(name, list(pool), n=limit, cutoff=0.4):
                if pool[n] not in out:
                    out.append(pool[n])
        if not out:
            out = [a for a in self.suggest(cat, limit)]
        return out[:limit]

    def check(self, refs_in: Iterable[str]) -> dict[str, Asset | list[Asset]]:
        out: dict[str, Asset | list[Asset]] = {}
        for r in refs_in:
            try:
                hit = self.resolve(r)
            except RefError:
                hit = None
            out[r] = hit if hit is not None else self.nearest(r)
        return out

    def query(self, *, pack: str | None = None, category: str | None = None, tags: Iterable[str] = (),
              text: str = "", rights: str | None = None) -> list[Asset]:
        """Assets matching every filter. With tags, those whose Author tags hit more of them come first
        (the Author's tags weigh more than the agent's); then by category and ref."""
        want = [t.lower() for t in tags if t.strip()]
        text = text.strip().lower()
        out = []
        for a in self.assets:
            if pack and a.pack != pack:
                continue
            if category and a.category != category:
                continue
            if rights and a.rights != rights:
                continue
            if want:
                have = {t.lower() for t in a.all_tags()}
                if not all(t in have for t in want):
                    continue
            if text and text not in a.haystack():
                continue
            out.append(a)
        return sorted(out, key=lambda a: (-a.author_hits(want), a.category, a.ref))

    def tag_counts(self, assets: Iterable[Asset] | None = None) -> list[dict]:
        author_n: Counter = Counter()
        agent_n: Counter = Counter()
        label: dict[str, str] = {}
        for a in (self.assets if assets is None else assets):
            mine = {t.lower() for t in a.tags}
            for t in a.tags:
                label.setdefault(t.lower(), t)
                author_n[t.lower()] += 1
            for t in a.agent_tags:
                if t.lower() not in mine:
                    label.setdefault(t.lower(), t)
                    agent_n[t.lower()] += 1
        rows = [{"tag": label[k], "n": author_n[k] + agent_n.get(k, 0), "author": author_n[k] > 0}
                for k in set(author_n) | set(agent_n)]
        rows.sort(key=lambda r: (not r["author"], -r["n"], r["tag"].lower()))
        return rows


def _asset(info: PackInfo, cache: Path, a: dict, row: dict | None, aliases: tuple[str, ...]) -> Asset:
    row = row or {}
    return Asset(
        id=a["id"], pack=info.id, root=info.root, cache=cache, category=a["category"],
        category_source=a.get("category_source", "mapping"), name=a["name"], author_name=row.get("name"),
        kind=a["kind"], folder=a.get("folder", ""), group=a.get("group"), variants=tuple(a["variants"]),
        duration_s=a.get("duration_s"), fps=a.get("fps"), width=a.get("width"), height=a.get("height"),
        has_audio=bool(a.get("has_audio")), alpha=bool(a.get("alpha")), green_screen=bool(a.get("green_screen")),
        loudness=a.get("loudness"), derived=dict(a.get("derived") or {}),
        rights_default=a.get("rights_default") or "unknown", rights_override=row.get("rights"),
        caption=row.get("caption"), tags=tuple(row.get("tags") or ()), agent=a.get("agent"),
        aliases=aliases, updated_at=row.get("updated_at"),
        hidden_agent_tags=tuple(row.get("hidden_agent_tags") or ()))


def load(footage: Path, store: Store | None) -> Library:
    footage = Path(footage)
    if store is None:
        return Library(footage, [], [], {})
    rows = author.rows(store)
    alias_rows = author.alias_rows(store)
    by_asset: dict[str, list[str]] = {}
    for r in alias_rows:
        by_asset.setdefault(r["asset_id"], []).append(r["ref"])
    views, assets = [], []
    for info in list_packs(store):
        idx = read_index(footage, info.id)
        views.append(PackView(info, idx is None, (idx or {}).get("indexed_at"), (idx or {}).get("report") or {}))
        cache = cache_dir(footage, info.id)
        for a in (idx or {}).get("assets", []):
            assets.append(_asset(info, cache, a, rows.get(a["id"]), tuple(sorted(by_asset.get(a["id"], ())))))
    shown = {a.ref for a in assets} | {a.file_ref for a in assets}
    assets = [replace(a, aliases=tuple(r for r in a.aliases if r not in shown)) for a in assets]
    return Library(footage, views, assets, {r["ref"]: r["asset_id"] for r in alias_rows})


def _iso(mtime: float | None) -> str | None:
    if mtime is None:
        return None
    return datetime.fromtimestamp(mtime, timezone.utc).isoformat(timespec="seconds")


def card(a: Asset, *, full: bool = True) -> dict:
    p = a.primary
    out = {
        "id": a.id, "pack": a.pack, "category": a.category, "category_source": a.category_source,
        "ref": a.ref, "name": a.name, "author_name": a.author_name, "aliases": list(a.aliases),
        "kind": a.kind, "folder": a.folder,
        "file": {"path": p["path"], "name": p["path"].rsplit("/", 1)[-1], "size": p.get("size"),
                 "mtime": _iso(p.get("mtime"))},
        "media": a.media,
        "duration_s": a.duration_s, "fps": a.fps, "width": a.width, "height": a.height, "has_audio": a.has_audio,
        "alpha": a.alpha, "green_screen": a.green_screen, "loudness": a.loudness,
        "rights": a.rights, "rights_default": a.rights_default, "rights_override": a.rights_override,
        "caption": a.caption, "tags": list(a.tags), "agent_caption": a.agent_caption,
        "agent_tags": list(a.agent_tags), "hidden_agent_tags": list(a.hidden_agent_tags),
        "updated_at": a.updated_at,
    }
    if full:
        served = a.kind in SERVED_KINDS
        out["variants"] = [{"role": v["role"], "path": v["path"], "media": a.pack_media(v["path"]) if served else None,
                            "size": v.get("size"), "alpha": bool(v.get("alpha")), "codec": v.get("codec"),
                            "pix_fmt": v.get("pix_fmt"), "duration_s": v.get("duration_s"),
                            "width": v.get("width"), "height": v.get("height")} for v in a.variants]
    return out
