"""Walking a Pack: which files are media, which are templates, which are junk; symlinks are never followed."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from cf.library.packs import ROOT, Folder, PackConfig

AUDIO = frozenset({"mp3", "wav", "m4a", "aac", "ogg", "flac", "aif", "aiff"})
VIDEO = frozenset({"mp4", "mov", "m4v", "webm", "mkv"})
IMAGE = frozenset({"png", "jpg", "jpeg", "jfif", "webp", "avif", "gif", "bmp", "tif", "tiff"})
FONT = frozenset({"ttf", "otf"})
TEMPLATE = frozenset({"drfx", "drp", "setting", "drx", "cube", "lua"})
BUNDLE = "dra"
FALLBACK = {"audio": "sfx", "video": "footage", "image": "img", "font": "font", "template": "template"}


def kind_of(name: str) -> str | None:
    ext = name.rsplit(".", 1)[-1].lower() if "." in name else ""
    for kind, exts in (("audio", AUDIO), ("video", VIDEO), ("image", IMAGE), ("font", FONT), ("template", TEMPLATE)):
        if ext in exts:
            return kind
    return None


@dataclass(frozen=True)
class FileEntry:
    rel: str
    size: int
    mtime_ns: int
    kind: str
    bundle: bool = False
    mapping: tuple[str, Folder] | None = None

    @property
    def folder(self) -> str:
        return self.rel.rsplit("/", 1)[0] if "/" in self.rel else ""

    @property
    def ext(self) -> str:
        return self.rel.rsplit(".", 1)[-1].lower() if "." in self.rel.rsplit("/", 1)[-1] else ""


@dataclass
class ScanResult:
    files: list[FileEntry] = field(default_factory=list)
    junk: int = 0
    symlinks: int = 0


def _under(rel: str, prefixes: tuple[str, ...]) -> bool:
    return any(p == ROOT or rel == p or rel.startswith(p + "/") for p in prefixes)


def _above(rel: str, prefixes: tuple[str, ...]) -> bool:
    return any(p != ROOT and p.startswith(rel + "/") for p in prefixes)


def scan(cfg: PackConfig, only: tuple[str, ...] = ()) -> ScanResult:
    out = ScanResult()
    include = cfg.include

    def wanted(rel: str) -> bool:
        return not only or _under(rel, only)

    def walk(folder: Path, rel_dir: str) -> None:
        try:
            entries = sorted(os.scandir(folder), key=lambda e: e.name)
        except OSError:
            return
        for e in entries:
            rel = f"{rel_dir}/{e.name}" if rel_dir else e.name
            media_zone = _under(rel, include)
            if _under(rel, cfg.exclude):
                continue
            if e.is_symlink():
                out.symlinks += 1
                continue
            if e.name.startswith("."):
                if media_zone and e.is_file(follow_symlinks=False):
                    out.junk += 1
                continue
            if e.is_dir(follow_symlinks=False):
                if e.name.lower().endswith("." + BUNDLE):
                    if (media_zone or cfg.templates) and wanted(rel):
                        st = e.stat(follow_symlinks=False)
                        out.files.append(FileEntry(rel, st.st_size, st.st_mtime_ns, "template", True,
                                                   cfg.folder_for(rel)))
                    continue
                if media_zone or cfg.templates or _above(rel, include):
                    walk(Path(e.path), rel)
                continue
            if not e.is_file(follow_symlinks=False):
                continue
            kind = kind_of(e.name)
            if media_zone:
                if kind is None:
                    out.junk += 1
                    continue
            elif kind != "template" or not cfg.templates:
                continue
            if not wanted(rel):
                continue
            st = e.stat(follow_symlinks=False)
            out.files.append(FileEntry(rel, st.st_size, st.st_mtime_ns, kind, False, cfg.folder_for(rel)))

    walk(cfg.root, "")
    return out
