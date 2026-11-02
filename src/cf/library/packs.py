"""Pack configs (``cf-pack/1``) and the ``pack`` table that registers them."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any

from cf.library.errors import PackError, PackNotFound
from cf.library.refs import CATEGORIES
from cf.research.store import Store, dumps, now_iso

SCHEMA = "cf-pack/1"
ID_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")
HEX_RE = re.compile(r"0x[0-9A-Fa-f]{6}")
KEY_COLORS = {"green": "0x00FF00", "blue": "0x0000FF"}
ROOT = "."  # in include and folders: the Pack root itself (an inbox of loose files)
FOLDER_KEYS = {"category", "rights", "key", "key_similarity", "key_blend", "group"}


@dataclass(frozen=True)
class Folder:
    category: str
    rights: str | None = None
    key: str | None = None
    key_similarity: float = 0.30
    key_blend: float = 0.05
    group: str | None = None


@dataclass(frozen=True)
class PackConfig:
    id: str
    root: Path
    include: tuple[str, ...]
    exclude: tuple[str, ...]
    templates: bool
    folders: dict[str, Folder] = field(default_factory=dict)
    raw: dict = field(default_factory=dict, compare=False)

    def folder_for(self, rel: str) -> tuple[str, Folder] | None:
        """The mapping of the deepest configured folder holding ``rel``; ``"."`` holds everything."""
        best = None
        for key, folder in self.folders.items():
            if key == ROOT or rel == key or rel.startswith(key + "/"):
                depth = 0 if key == ROOT else len(key)
                if best is None or depth > best[2]:
                    best = (key, folder, depth)
        return best[:2] if best else None


@dataclass(frozen=True)
class PackInfo:
    id: str
    root: Path
    config: PackConfig
    created_at: str
    indexed_at: str | None

    def to_dict(self) -> dict:
        return {"id": self.id, "root": str(self.root), "created_at": self.created_at, "indexed_at": self.indexed_at}


def _relpath(value: Any, what: str, *, root_ok: bool = False) -> str:
    if root_ok and value == ROOT:
        return value
    if not isinstance(value, str) or not value.strip() or value == ROOT:
        raise PackError(f"{what}: a relative folder path is required, got {value!r}"
                        + ("" if root_ok else " ('.' is allowed only in include and folders)"))
    if value.startswith("/") or "\\" in value:
        raise PackError(f"{what}: {value!r} must be relative to the Pack root")
    parts = PurePosixPath(value).parts
    if any(p in ("..", ".") for p in parts) or value != PurePosixPath(value).as_posix():
        raise PackError(f"{what}: {value!r} must not contain '..' or '.'")
    return value


def _folder(key: str, value: Any) -> Folder:
    if not isinstance(value, dict):
        raise PackError(f"folders[{key!r}]: an object with a category is required")
    unknown = set(value) - FOLDER_KEYS
    if unknown:
        raise PackError(f"folders[{key!r}]: unknown fields {sorted(unknown)}")
    cat = value.get("category")
    if cat not in CATEGORIES:
        raise PackError(f"folders[{key!r}]: unknown category {cat!r}; one of {', '.join(CATEGORIES)}")
    rights = value.get("rights")
    if rights not in (None, "own", "free", "unknown"):
        raise PackError(f"folders[{key!r}]: rights {rights!r} must be own, free or unknown")
    key_color = value.get("key")
    if key_color is not None:
        key_color = KEY_COLORS.get(key_color, key_color)
        if not isinstance(key_color, str) or not HEX_RE.fullmatch(key_color):
            raise PackError(f"folders[{key!r}]: key {value.get('key')!r} must be green, blue or 0xRRGGBB")
    group = value.get("group")
    if group not in (None, "sticker"):
        raise PackError(f"folders[{key!r}]: group {group!r}; the only grouping rule is 'sticker'")
    try:
        sim = float(value.get("key_similarity", 0.30))
        blend = float(value.get("key_blend", 0.05))
    except (TypeError, ValueError) as exc:
        raise PackError(f"folders[{key!r}]: key_similarity and key_blend are numbers") from exc
    return Folder(cat, rights, key_color, sim, blend, group)


def parse_config(data: Any, *, root: Path | None = None) -> PackConfig:
    if not isinstance(data, dict):
        raise PackError("a Pack config is a JSON object")
    if data.get("schema") != SCHEMA:
        raise PackError(f"schema must be {SCHEMA!r}, got {data.get('schema')!r}")
    pid = data.get("id")
    if not isinstance(pid, str) or not ID_RE.fullmatch(pid):
        raise PackError(f"id {pid!r}: lowercase letters, digits and '-', up to 64 characters")
    root_value = root if root is not None else data.get("root")
    if not root_value:
        raise PackError("root: the Pack folder (absolute path) is required")
    root_path = Path(str(root_value)).expanduser()
    if not root_path.is_absolute():
        raise PackError(f"root {root_value!r} must be an absolute path")
    if not root_path.is_dir():
        raise PackError(f"root {root_path} is not a folder")
    include = data.get("include", [])
    exclude = data.get("exclude", [])
    if not isinstance(include, list) or not isinstance(exclude, list):
        raise PackError("include and exclude are lists of relative folders")
    folders = data.get("folders", {})
    if not isinstance(folders, dict):
        raise PackError("folders is an object of relative folder → mapping")
    raw = {**data, "root": str(root_path)}
    return PackConfig(
        id=pid, root=root_path,
        include=tuple(_relpath(v, "include", root_ok=True) for v in include),
        exclude=tuple(_relpath(v, "exclude") for v in exclude),
        templates=bool(data.get("templates", False)),
        folders={_relpath(k, "folders", root_ok=True): _folder(k, v) for k, v in folders.items()},
        raw=raw)


def _info(row: dict) -> PackInfo:
    data = json.loads(row["config"])
    try:
        cfg = parse_config(data, root=Path(row["root"]))
    except PackError:
        cfg = PackConfig(id=row["id"], root=Path(row["root"]), include=(), exclude=(), templates=False, raw=data)
    return PackInfo(row["id"], Path(row["root"]), cfg, row["created_at"], row["indexed_at"])


def register_pack(store: Store, config: dict, *, root: Path | None = None) -> PackInfo:
    cfg = parse_config(config, root=root)
    with store.transaction() as c:
        prev = store.one("SELECT created_at FROM pack WHERE id = ?", (cfg.id,))
        created = prev["created_at"] if prev else now_iso()
        c.execute("INSERT INTO pack (id, root, config, created_at) VALUES (?, ?, ?, ?) "
                  "ON CONFLICT (id) DO UPDATE SET root = excluded.root, config = excluded.config",
                  (cfg.id, str(cfg.root), dumps(cfg.raw), created))
    return get_pack(store, cfg.id)


def list_packs(store: Store) -> list[PackInfo]:
    return [_info(r) for r in store.query("SELECT * FROM pack ORDER BY id")]


def get_pack(store: Store, pack_id: str) -> PackInfo:
    row = store.one("SELECT * FROM pack WHERE id = ?", (pack_id,))
    if row is None:
        raise PackNotFound(pack_id)
    return _info(row)


def remove_pack(store: Store, pack_id: str) -> None:
    get_pack(store, pack_id)
    with store.transaction() as c:
        c.execute("DELETE FROM pack WHERE id = ?", (pack_id,))


def mark_indexed(store: Store, pack_id: str, at: str) -> None:
    with store.transaction() as c:
        c.execute("UPDATE pack SET indexed_at = ? WHERE id = ?", (at, pack_id))
