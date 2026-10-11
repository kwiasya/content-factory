"""Copy a reel's final renders into the human-facing "Готовые ролики" folder.

    python -m cf.publish <reel_dir> [--root ~/Movies/Готовые\\ ролики]

Reads ``script.json``: ``title`` (what the video is, e.g. "Майорка — отель и пляж"),
the caption, hashtags, location tag and alt text.
Writes, for one reel:

    <root>/<title> (вертикаль).mp4                          the video to watch, with music
    <root>/_для публикации …/<title> — без музыки.mp4       upload with the sound added in Instagram
    <root>/_для публикации …/<title> — подпись к посту.txt   caption, hashtags, location, alt text

The root is flat on purpose: the author opens one folder and sees only finished videos.

Source files: ``out/<reel>.normalized.mp4`` (falls back to ``out/<reel>.mp4``) and
``out/<reel>.ambience.normalized.mp4`` (falls back to ``out/<reel>.ambience.mp4``).
Older copies of the same title are replaced, so the folder always holds the latest cut.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Movies" / "Готовые ролики"
EXTRAS = "_для публикации (без музыки и подписи)"


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
    if script.get("alt_text"):
        parts.append(f"Alt-текст: {script['alt_text']}")
    return "\n\n".join(p for p in parts if p) + "\n"


def publish(reel_dir: Path, root: Path = DEFAULT_ROOT) -> list[Path]:
    reel_dir = reel_dir.expanduser().resolve()
    script = json.loads((reel_dir / "script.json").read_text())
    title = script.get("title")
    if not title:
        raise SystemExit(f"{reel_dir}/script.json needs a 'title' to publish")
    reel = reel_dir.name
    out = reel_dir / "out"
    music = _first(out / f"{reel}.normalized.mp4", out / f"{reel}.mp4")
    ambience = _first(out / f"{reel}.ambience.normalized.mp4", out / f"{reel}.ambience.mp4")
    if music is None:
        raise SystemExit(f"no render in {out}")

    dest = root.expanduser()
    extras = dest / EXTRAS
    extras.mkdir(parents=True, exist_ok=True)
    for old in list(dest.glob(f"{title} (*")) + list(extras.glob(f"{title} —*")):
        old.unlink()
    written = []
    target = dest / f"{title} ({_orientation(music)}).mp4"
    shutil.copy2(music, target)
    written.append(target)
    if ambience is not None:
        target = extras / f"{title} — без музыки.mp4"
        shutil.copy2(ambience, target)
        written.append(target)
    txt = extras / f"{title} — подпись к посту.txt"
    txt.write_text(caption_text(script))
    written.append(txt)
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.publish", description=__doc__.splitlines()[0])
    ap.add_argument("reel_dir", type=Path)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    a = ap.parse_args(argv)
    for p in publish(a.reel_dir, a.root):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
