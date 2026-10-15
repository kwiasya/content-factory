"""Create a Walk folder from a source folder of Clips and stills, linking the files in place (ADR 0008).

    python -m cf.walk init <walk> --from <source_dir> [--copy]
"""

from __future__ import annotations

import argparse
import os
import re
import shutil
import sys
from dataclasses import dataclass, field
from pathlib import Path

from cf import STILL_EXTENSIONS, VIDEO_EXTENSIONS
from cf.research.store import local_root

WALK_ID = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*-\d{4}-\d{2}-\d{2}$")
WALK_ID_RULE = "a Walk id is <place>-<YYYY-MM-DD>: lowercase letters, digits and dashes, ending with the first shooting day"
SUBDIRS = ("raw", "proxy", "shotlog", "stills")


class WalkError(Exception):
    pass


@dataclass
class Result:
    walk_dir: Path
    clips: list[str] = field(default_factory=list)
    stills: list[str] = field(default_factory=list)
    present: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    folders: list[str] = field(default_factory=list)


def walk_dir_of(walk: str) -> Path:
    if "/" in walk or walk.startswith((".", "~")):
        path = Path(walk).expanduser().absolute()
    else:
        path = local_root() / walk
    if not WALK_ID.match(path.name):
        raise WalkError(f"bad Walk id {path.name!r}: {WALK_ID_RULE}")
    return path


def is_same(dest: Path, src: Path) -> bool:
    if dest.is_symlink():
        return dest.resolve() == src
    if not dest.is_file():
        return False
    a, b = dest.stat(), src.stat()
    return a.st_size == b.st_size and abs(a.st_mtime - b.st_mtime) < 1


def copy_file(src: Path, dest: Path) -> None:
    part = dest.with_name(dest.name + ".part")
    shutil.copy2(src, part)
    os.replace(part, dest)


def plan(source: Path, walk_dir: Path) -> tuple[list[tuple[Path, Path, str]], list[str], list[str], list[str]]:
    todo, present, skipped, folders = [], [], [], []
    for src in sorted(source.iterdir()):
        if src.name.startswith("."):
            continue
        if src.is_dir():
            folders.append(src.name)
            continue
        if not src.is_file():
            continue
        suffix = src.suffix.lower()
        sub = "raw" if suffix in VIDEO_EXTENSIONS else "stills" if suffix in STILL_EXTENSIONS else None
        if sub is None:
            skipped.append(src.name)
            continue
        dest = walk_dir / sub / src.name
        target = src.resolve()
        if dest.is_symlink() or dest.exists():
            if not is_same(dest, target):
                raise WalkError(f"{dest} already exists and is not {target}")
            present.append(src.name)
            continue
        todo.append((target, dest, sub))
    return todo, present, skipped, folders


def init(walk: str, source: Path, copy: bool = False) -> Result:
    walk_dir = walk_dir_of(walk)
    source = source.expanduser()
    if not source.is_dir():
        raise WalkError(f"not a directory: {source}")
    todo, present, skipped, folders = plan(source, walk_dir)
    if not todo and not present:
        hint = f"; folders not scanned: {', '.join(folders)}" if folders else ""
        raise WalkError(f"no Clips or stills directly in {source}{hint}")
    result = Result(walk_dir, present=present, skipped=skipped, folders=folders)
    try:
        for sub in SUBDIRS:
            (walk_dir / sub).mkdir(parents=True, exist_ok=True)
        for target, dest, sub in todo:
            if copy:
                copy_file(target, dest)
            else:
                dest.symlink_to(target)
            (result.clips if sub == "raw" else result.stills).append(dest.name)
    except OSError as e:
        raise WalkError(f"cannot write {e.filename or walk_dir}: {e.strerror or e}") from e
    return result


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.walk", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init", help="create the Walk folder and link (or copy) the Clips and stills")
    p.add_argument("walk", help="a Walk id (resolved under the footage root) or a path to the Walk folder")
    p.add_argument("--from", dest="source", type=Path, required=True, help="folder with the Clips and stills")
    p.add_argument("--copy", action="store_true", help="copy instead of linking (cards and drives that get unplugged)")
    args = ap.parse_args(argv)

    try:
        result = init(args.walk, args.source, copy=args.copy)
    except WalkError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    verb = "copied" if args.copy else "linked"
    line = f"{result.walk_dir}: {len(result.clips)} clips {verb}, {len(result.stills)} stills, " \
           f"{len(result.present)} already present, {len(result.skipped)} skipped"
    if result.skipped:
        line += ": " + ", ".join(result.skipped)
    print(line)
    if result.folders:
        print("folders not scanned: " + ", ".join(result.folders))
    print("next:")
    print(f"  .venv/bin/python -m cf.probe {result.walk_dir / 'raw'}")
    print(f"  .venv/bin/python -m cf.proxy {result.walk_dir / 'raw'} {result.walk_dir / 'proxy'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
