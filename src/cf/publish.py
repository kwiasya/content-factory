"""Copy a reel's final renders into the human-facing "Готовые ролики" folder.

    python -m cf.publish <reel_dir> [--root ~/Movies/Готовые\\ ролики] [--variant NAME]

Reads ``script.json``: ``title`` (what the video is, e.g. "Майорка — отель и пляж"),
the caption, hashtags and location tag.
Writes, for one reel, two files side by side:

    <root>/<title> (вертикаль).mp4           the video to upload; the author adds the sound in Instagram
    <root>/<title> — подпись к посту.txt     caption, hashtags, location

The video is the no-music render when one exists, else the main render. The root is flat on
purpose: the author opens one folder and sees only finished videos and their captions.

Source files: ``out/<reel>.normalized.mp4`` (falls back to ``out/<reel>.mp4``) and
``out/<reel>.ambience.normalized.mp4`` (falls back to ``out/<reel>.ambience.mp4``).
Older copies of the same title go to the Trash (the author wants old versions recoverable), so the
folder always holds the latest cut.
``--variant hdr`` publishes ``out/<reel>.hdr.normalized.mp4`` (or ``.hdr.mp4``) instead, and
``out/<reel>.ambience.hdr.normalized.mp4`` (or ``.ambience.hdr.mp4``) when it exists; without
it the default no-music file is used and a note says so.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Movies" / "Готовые ролики"


def _duration_s(path: Path) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip()
    return float(out)


def _orientation(path: Path) -> str:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
         "-of", "csv=p=0", str(path)],
        capture_output=True, text=True, check=True,
    ).stdout.strip().splitlines()[0]
    w, h = (int(x) for x in out.split(","))
    return "вертикаль" if h > w else "горизонталь"


def _first(*paths: Path) -> Path | None:
    return next((p for p in paths if p.exists()), None)


def caption_text(script: dict) -> str:
    parts = [script.get("caption", "").strip()]
    tags = " ".join(script.get("hashtags") or [])
    if tags:
        parts.append(tags)
    if script.get("location_tag"):
        parts.append(f"Геотег: {script['location_tag']}")
    return "\n\n".join(p for p in parts if p) + "\n"


def sources(out: Path, reel: str, variant: str | None = None) -> tuple[Path | None, Path | None, bool]:
    """(music file, no-music file, whether the no-music file is the variant's own)."""
    v = f".{variant}" if variant else ""
    music = _first(out / f"{reel}{v}.normalized.mp4", out / f"{reel}{v}.mp4")
    own = _first(out / f"{reel}.ambience{v}.normalized.mp4", out / f"{reel}.ambience{v}.mp4")
    if own is not None or not variant:
        return music, own, True
    return music, _first(out / f"{reel}.ambience.normalized.mp4", out / f"{reel}.ambience.mp4"), False


def publish(reel_dir: Path, root: Path = DEFAULT_ROOT, variant: str | None = None) -> list[Path]:
    """Two files per reel, side by side in ``root``: the video and its caption.

    The author adds the sound in Instagram herself (2026-10-12), so the video is the no-music render
    when one exists and the main render otherwise.
    """
    reel_dir = reel_dir.expanduser().resolve()
    script = json.loads((reel_dir / "script.json").read_text())
    title = script.get("title")
    if not title:
        raise SystemExit(f"{reel_dir}/script.json needs a 'title' to publish")
    reel = reel_dir.name
    out = reel_dir / "out"
    music, ambience, own = sources(out, reel, variant)
    if music is None:
        raise SystemExit(f"no render in {out}" + (f" for variant {variant!r}" if variant else ""))
    if ambience is not None and not own:
        print(f"note: no no-music render for variant {variant!r}; using {ambience.name}", file=sys.stderr)
    video = ambience if ambience is not None else music

    dest = root.expanduser()
    dest.mkdir(parents=True, exist_ok=True)
    txt = dest / f"{title} — подпись к посту.txt"
    for old in [*dest.glob(f"{title} (*"), *([txt] if txt.exists() else [])]:
        _to_trash(old)
    target = dest / f"{title} ({_orientation(video)}).mp4"
    shutil.copy2(video, target)
    txt.write_text(caption_text(script))
    return [target, txt]


def _to_trash(path: Path, trash: Path = Path.home() / ".Trash") -> Path:
    """Move ``path`` into the user's Trash under a free name (never delete outright)."""
    trash.mkdir(exist_ok=True)
    dest, n = trash / path.name, 1
    while dest.exists():
        dest, n = trash / f"{path.stem} ({n}){path.suffix}", n + 1
    shutil.move(str(path), dest)
    return dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.publish", description=__doc__.splitlines()[0])
    ap.add_argument("reel_dir", type=Path)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--variant", help="publish out/<reel>.<variant>[.normalized].mp4, e.g. hdr or sdr-bright")
    a = ap.parse_args(argv)
    for p in publish(a.reel_dir, a.root, a.variant):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
