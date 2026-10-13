"""One Pack's index: ``<footage>/library/<pack>/index.json``, built incrementally from a scan of the Pack.

The Pack is only read. Everything derived lives in the cache folder next to the index; the Author's fields live
in the store and are never written here.
"""

from __future__ import annotations

import json
import re
import shutil
import time
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from cf.library import ids, probe, refs
from cf.library.files import atomic_write
from cf.library.errors import PackError
from cf.library.packs import Folder, PackConfig, get_pack, list_packs, mark_indexed
from cf.library.scan import FALLBACK, FileEntry, scan
from cf.research.store import Store, now_iso

SCHEMA = "cf-library-index/1"
STICKER_RE = re.compile(r"(\d{6,8})_sticker")
DERIVED_KEYS = ("alpha", "converted", "png", "poster", "preview")
SUBDIRS = ("keyed", "converted", "png", "previews", "sheets")


def cache_dir(footage: Path, pack_id: str) -> Path:
    return Path(footage) / "library" / pack_id


def index_path(footage: Path, pack_id: str) -> Path:
    return cache_dir(footage, pack_id) / "index.json"


def read_index(footage: Path, pack_id: str) -> dict | None:
    p = index_path(footage, pack_id)
    if not p.is_file():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) and data.get("schema") == SCHEMA else None


def write_index(footage: Path, pack_id: str, data: dict) -> None:
    p = index_path(footage, pack_id)
    p.parent.mkdir(parents=True, exist_ok=True)
    atomic_write(p, (json.dumps(data, ensure_ascii=False, indent=1) + "\n").encode("utf-8"))


@dataclass
class Report:
    scanned: int = 0
    assets: int = 0
    new: int = 0
    changed: int = 0
    removed: int = 0
    unchanged: int = 0
    probed: int = 0
    duplicates: int = 0
    derived: dict = field(default_factory=lambda: {"keyed": 0, "converted": 0, "png": 0, "previews": 0,
                                                   "loudness": 0})
    skipped: list = field(default_factory=list)
    fallback: dict = field(default_factory=dict)
    junk: int = 0
    symlinks: int = 0
    orphans_removed: int = 0
    aliases: int = 0
    errors: list = field(default_factory=list)
    seconds: float = 0.0

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _variant(entry: FileEntry, root: Path, prev: dict | None, report: Report) -> dict | None:
    path = root / entry.rel
    if prev and prev.get("size") == entry.size and prev.get("mtime_ns") == entry.mtime_ns and not entry.bundle:
        return {**prev}
    v: dict = {"role": "original", "path": entry.rel, "size": entry.size,
               "mtime": round(entry.mtime_ns / 1e9, 3), "mtime_ns": entry.mtime_ns, "kind": entry.kind}
    try:
        v["content_id"] = ids.bundle_id(path) if entry.bundle else ids.content_id(path)
    except OSError as exc:
        report.errors.append({"ref": entry.rel, "step": "hash", "stderr": str(exc)[-300:]})
        return None
    if entry.kind in ("audio", "video", "image"):
        try:
            v.update(probe.facts(path, entry.kind))
            report.probed += 1
        except Exception as exc:
            report.errors.append({"ref": entry.rel, "step": "probe", "stderr": str(getattr(exc, "stderr", exc))[-300:]})
            v.update({"codec": None, "pix_fmt": None, "alpha": False, "width": None, "height": None, "fps": None,
                      "duration_s": None, "has_audio": False})
    return v


def _stem(rel: str, bundle: bool) -> str:
    name = rel.rsplit("/", 1)[-1]
    if bundle:
        return name[:-4] if name.lower().endswith(".dra") else name
    return Path(name).stem


def _group_key(entry: FileEntry) -> tuple:
    if entry.mapping and entry.mapping[1].group == "sticker":
        m = STICKER_RE.search(Path(entry.rel).stem)
        if m:
            return ("sticker", entry.mapping[1].category, m.group(1))
    return ("file", entry.rel)


def _role(v: dict, sticker: bool) -> str:
    if not sticker:
        return "original"
    ext = v["path"].rsplit(".", 1)[-1].lower()
    if ext == "webm":
        return "original"
    if ext == "mov" and v.get("alpha"):
        return "alpha"
    if ext == "png":
        return "still"
    return "original"


def _build_asset(key: tuple, variants: list[dict], entries: dict[str, FileEntry]) -> dict:
    sticker = key[0] == "sticker"
    for v in variants:
        v["role"] = _role(v, sticker)
    order = {"original": 0, "alpha": 1, "still": 2}
    variants.sort(key=lambda v: (order[v["role"]], v["path"]))
    primary = variants[0]
    entry = entries[primary["path"]]
    mapping: tuple[str, Folder] | None = entry.mapping
    kind = primary.get("kind", entry.kind)
    if kind == "template":
        category = "template"
        source = "mapping" if mapping and mapping[1].category == "template" else "kind"
    elif mapping:
        category, source = mapping[1].category, "mapping"
    else:
        category, source = FALLBACK[kind], "fallback"
    duration, fps = primary.get("duration_s"), primary.get("fps")
    alpha_variant = next((v for v in variants if v["role"] == "alpha"), None)
    if alpha_variant and (duration is None or duration < 0.1) and kind == "video":
        duration, fps = alpha_variant.get("duration_s"), alpha_variant.get("fps")
    folder = mapping[1] if mapping and source == "mapping" else None
    green = bool(folder and folder.key and kind == "video")
    stem = f"{key[2]}_sticker" if sticker else _stem(primary["path"], entry.bundle)
    return {
        "id": None, "category": category, "category_source": source, "name": None, "slug": refs.slug(stem),
        "kind": kind, "folder": entry.folder, "group": f"sticker:{key[2]}" if sticker else None,
        "variants": variants,
        "duration_s": duration, "fps": fps, "width": primary.get("width"), "height": primary.get("height"),
        "has_audio": bool(primary.get("has_audio")), "alpha": any(v.get("alpha") for v in variants),
        "green_screen": green, "loudness": None,
        "derived": {k: None for k in DERIVED_KEYS},
        "rights_default": (folder.rights if folder and folder.rights else "unknown"),
        "agent": None,
    }


def _owners(store: Store, footage: Path, pack_id: str) -> dict[str, dict[str, str]]:
    """Names held outside this Pack's file-derived names: other Packs' names, Author names, aliases."""
    out: dict[str, dict[str, str]] = defaultdict(dict)
    for info in list_packs(store):
        if info.id == pack_id:
            continue
        other = read_index(footage, info.id) or {}
        for a in other.get("assets", []):
            out[a["category"]][a["name"]] = a["id"]
    cats: dict[str, str] = {}
    for idx in [read_index(footage, i.id) or {} for i in list_packs(store)]:
        for a in idx.get("assets", []):
            cats[a["id"]] = a["category"]
    for row in store.query("SELECT asset_id, name FROM asset_author WHERE name IS NOT NULL"):
        if row["asset_id"] in cats:
            out[cats[row["asset_id"]]][row["name"]] = row["asset_id"]
    for row in store.query("SELECT ref, asset_id FROM asset_alias"):
        try:
            cat, name = refs.parse(row["ref"])
        except Exception:
            continue
        out[cat].setdefault(name, row["asset_id"])
    return out


def _within(rel: str, only: tuple[str, ...]) -> bool:
    return any(rel == p or rel.startswith(p + "/") for p in only)


def index_pack(store: Store, footage: Path, pack_id: str, *, key: bool = True, previews: bool = True,
               loudness: bool = True, only: tuple[str, ...] | str | None = None,
               log: Callable[[str], None] = print) -> Report:
    from cf.library import aliases, derive

    started = time.monotonic()
    footage = Path(footage)
    info = get_pack(store, pack_id)
    cfg: PackConfig = info.config
    if not cfg.root.is_dir():
        raise PackError(f"Pack root {cfg.root} is not a folder; re-register it with pack add --root")
    lib_root = (footage / "library").resolve()
    if cfg.root.resolve() == lib_root or cfg.root.resolve().is_relative_to(lib_root):
        raise PackError(f"Pack root {cfg.root} is inside the Library cache {lib_root}; a Pack is never there")
    only_t = (only,) if isinstance(only, str) else tuple(only or ())
    report = Report()
    prev = read_index(footage, pack_id) or {"assets": []}
    prev_assets = {a["id"]: a for a in prev.get("assets", [])}
    prev_variants = {v["path"]: v for a in prev.get("assets", []) for v in a["variants"]}

    result = scan(cfg, only_t)
    report.junk, report.symlinks, report.scanned = result.junk, result.symlinks, len(result.files)
    entries = {e.rel: e for e in result.files}
    groups: dict[tuple, list[dict]] = defaultdict(list)
    per_folder: dict[str, int] = defaultdict(int)
    for e in result.files:
        per_folder[e.folder] += 1
        v = _variant(e, cfg.root, prev_variants.get(e.rel), report)
        if v is not None:
            groups[_group_key(e)].append(v)
    for folder, n in sorted(per_folder.items()):
        log(f"{folder or '.'}: {n}")

    built = [_build_asset(k, vs, entries) for k, vs in groups.items()]
    built.sort(key=lambda a: a["variants"][0]["path"])
    seen: set[str] = set()
    for a in built:
        cid = a["variants"][0]["content_id"]
        if cid in seen:
            cid = ids.disambiguated(cid, a["variants"][0]["path"])
            report.duplicates += 1
        seen.add(cid)
        a["id"] = cid
    prev_by_vcid = {v["content_id"]: a["id"] for a in prev.get("assets", []) for v in a["variants"]}
    claimed: set[str] = set()
    for a in built:
        if a["id"] in prev_assets:
            continue
        for v in a["variants"]:
            old_id = prev_by_vcid.get(v["content_id"])
            if old_id is not None and old_id not in seen and old_id not in claimed:
                a["_prev_id"] = old_id
                claimed.add(old_id)
                break

    carried = []
    if only_t:
        carried = [a for a in prev.get("assets", [])
                   if a["id"] not in seen and not any(_within(v["path"], only_t) for v in a["variants"])]
    for a in carried:
        seen.add(a["id"])

    owners = _owners(store, footage, pack_id)
    for a in carried:
        owners[a["category"]][a["name"]] = a["id"]
    by_cat: dict[str, list[dict]] = defaultdict(list)
    for a in built:
        by_cat[a["category"]].append(a)
    for cat, items in by_cat.items():
        triples = []
        for a in items:
            old = prev_assets.get(a.get("_prev_id") or a["id"])
            kept = old["name"] if old and old.get("slug") == a["slug"] and old.get("category") == cat else None
            triples.append((a["id"], a["slug"], kept))
        names = refs.assign(triples, owners.get(cat, {}))
        for a in items:
            a["name"] = names[a["id"]]

    for a in built:
        old = prev_assets.get(a.get("_prev_id") or a["id"])
        if old is None:
            report.new += 1
            continue
        same_src = old["variants"][0]["content_id"] == a["variants"][0]["content_id"]
        if same_src:
            a["derived"] = {k: (old.get("derived") or {}).get(k) for k in DERIVED_KEYS}
            a["loudness"] = old.get("loudness")
        a["agent"] = old.get("agent")
        sig_old = (old["name"], old["category"], [(v["path"], v["content_id"]) for v in old["variants"]])
        sig_new = (a["name"], a["category"], [(v["path"], v["content_id"]) for v in a["variants"]])
        if sig_old == sig_new and old["id"] == a["id"]:
            report.unchanged += 1
        else:
            report.changed += 1
    report.removed = len([i for i in prev_assets if i not in seen and i not in claimed])

    cache = cache_dir(footage, pack_id)
    derive.run(cache, cfg.root, built, report, key=key, previews=previews, loudness=loudness, log=log)
    report.aliases = aliases.after_index(store, pack_id, built, prev_assets)
    for a in built:
        a.pop("_prev_id", None)
    assets = sorted(built + carried, key=lambda a: (a["category"], a["name"]))
    report.assets = len(assets)
    report.fallback = dict(sorted(_fallback(assets).items()))
    report.orphans_removed = derive.remove_orphans(cache, {a["id"] for a in assets})
    report.seconds = round(time.monotonic() - started, 2)
    at = now_iso()
    write_index(footage, pack_id, {"schema": SCHEMA, "pack": pack_id, "root": str(cfg.root), "indexed_at": at,
                                   "ffmpeg": derive.ffmpeg_version(), "assets": assets, "report": report.to_dict()})
    mark_indexed(store, pack_id, at)
    return report


def _fallback(assets: list[dict]) -> dict[str, int]:
    out: dict[str, int] = defaultdict(int)
    for a in assets:
        if a["category_source"] == "fallback":
            out[a["folder"] or "."] += 1
    return out


def remove_cache(footage: Path, pack_id: str) -> None:
    shutil.rmtree(cache_dir(footage, pack_id), ignore_errors=True)
