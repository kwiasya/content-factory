"""Copy a reel's final renders into the human-facing "Готовые ролики" folder.

    python -m cf.publish <reel_dir> [--platform instagram|shorts] [--playlist NAME]
                         [--root ~/Movies/Готовые\\ ролики] [--variant NAME]

Reads ``script.json``: ``title`` (what the video is, e.g. "Майорка — отель и пляж"),
the caption, hashtags and location tag, and for Shorts ``youtube_playlist`` and the optional
``youtube_title`` and ``youtube_description``.

The root is sorted by Platform:

    <root>/Instagram/Очередь/              not posted on Instagram yet (cf.publish writes here)
    <root>/Instagram/Выложено/             posted (the author or an agent moves files here, never cf.publish)
    <root>/YouTube Shorts/<playlist>/      one folder per YouTube playlist (PLAYLISTS)
    <root>/Разное/                         loose files that are not a published reel

Writes, for one reel, two files side by side:

    instagram  Instagram/Очередь/   <title> (вертикаль).mp4         no music: the author adds the sound in Instagram
                                    <title> — подпись к посту.txt   caption, hashtags, location
    shorts     YouTube Shorts/<playlist>/
                                    <title> (shorts).mp4            WITH music: picking a track on YouTube is hard
                                    <title> — shorts.txt            playlist, YouTube title (≤100 chars),
                                                                    description, hashtags + #shorts

The Short's playlist is ``--playlist`` or ``youtube_playlist`` in script.json, one of PLAYLISTS.
Instagram source: the no-music render ``out/<reel>.ambience.normalized.mp4`` (falls back to
``out/<reel>.ambience.mp4``) when one exists, else the main render ``out/<reel>.normalized.mp4``
(falls back to ``out/<reel>.mp4``).
Shorts source: the music render ``out/<reel>.shorts.normalized.mp4`` (falls back to
``out/<reel>.shorts.mp4``; make it with ``cf.render --out out/<reel>.shorts.mp4 --fix-loudness`` from a
timeline with the Track on A2); without it, the main render when an ``.ambience`` render exists beside
it (then the main one is the music cut). Otherwise it stops: a no-music file is never published as
a Short.
Older copies of the same title go to the Trash (the author wants old versions recoverable), so the
folder always holds the latest cut: for Instagram from ``Очередь``, ``Выложено`` and the root itself
(the old flat layout); for Shorts from every playlist folder.
``--variant hdr`` publishes ``out/<reel>.hdr.normalized.mp4`` (or ``.hdr.mp4``) instead, and
``out/<reel>.ambience.hdr.normalized.mp4`` (or ``.ambience.hdr.mp4``) when it exists; without
it the default no-music file is used and a note says so. For Shorts it reads ``out/<reel>.shorts.hdr…``.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_ROOT = Path.home() / "Movies" / "Готовые ролики"
PLATFORMS = {"instagram": "Instagram", "shorts": "YouTube Shorts"}
QUEUE, POSTED, MISC = "Очередь", "Выложено", "Разное"
# The author's YouTube playlists (2026-11-01); a Short goes straight into one of them.
PLAYLISTS = {
    "Europe Travel Vlogs": "city trips, travel diaries, solo travel through Berlin, Prague, Vienna and beyond",
    "Travel Memes": "short relatable memes about travelling, packing too much, missing trains and everyday life",
    "Day In My Life": "cafes, trains, markets, small moments",
    "City Walks": "POV city walks and walking tours through European cities",
}
YT_TITLE_MAX = 100
SHORTS_MAX_S = 180.0


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


def platform_dirs(root: Path, platform: str) -> tuple[Path, Path]:
    """(Очередь, Выложено) of Instagram under ``root``."""
    base = root.expanduser() / PLATFORMS[platform]
    return base / QUEUE, base / POSTED


def playlist_dirs(root: Path) -> dict[str, Path]:
    """Every YouTube playlist folder under ``root``, by playlist name."""
    base = root.expanduser() / PLATFORMS["shorts"]
    return {name: base / name for name in PLAYLISTS}


def caption_text(script: dict) -> str:
    parts = [script.get("caption", "").strip()]
    tags = " ".join(script.get("hashtags") or [])
    if tags:
        parts.append(tags)
    if script.get("location_tag"):
        parts.append(f"Геотег: {script['location_tag']}")
    return "\n\n".join(p for p in parts if p) + "\n"


def _clip(text: str, limit: int) -> str:
    """``text`` cut to ``limit`` characters at a word boundary, with an ellipsis when cut."""
    if len(text) <= limit:
        return text
    cut = text[: limit - 1]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" ,.;:—-") + "…"


def shorts_text(script: dict, playlist: str | None = None) -> str:
    """Playlist, title (≤100 chars), description and hashtags for the YouTube upload form.

    ``youtube_title`` / ``youtube_description`` when set, else the first line of the caption and the
    caption; the hashtags end with #shorts.
    """
    caption = (script.get("caption") or "").strip()
    title = (script.get("youtube_title") or "").strip() or (caption.splitlines() or [""])[0].strip()
    title = _clip(title or script.get("title", ""), YT_TITLE_MAX)
    desc = (script.get("youtube_description") or "").strip() or caption
    tags, seen = [], set()
    for t in [*(script.get("hashtags") or []), "#shorts"]:
        if t.lower() not in seen:
            seen.add(t.lower())
            tags.append(t)
    parts = [f"Плейлист: {playlist}" if playlist else "", f"Название (до {YT_TITLE_MAX} знаков):\n{title}", f"Описание:\n{desc}" if desc else "",
             " ".join(tags)]
    return "\n\n".join(p for p in parts if p) + "\n"


def sources(out: Path, reel: str, variant: str | None = None) -> tuple[Path | None, Path | None, bool]:
    """(music file, no-music file, whether the no-music file is the variant's own)."""
    v = f".{variant}" if variant else ""
    music = _first(out / f"{reel}{v}.normalized.mp4", out / f"{reel}{v}.mp4")
    own = _first(out / f"{reel}.ambience{v}.normalized.mp4", out / f"{reel}.ambience{v}.mp4")
    if own is not None or not variant:
        return music, own, True
    return music, _first(out / f"{reel}.ambience.normalized.mp4", out / f"{reel}.ambience.mp4"), False


def shorts_source(out: Path, reel: str, variant: str | None = None) -> Path | None:
    """The render with music for YouTube Shorts, or None when the reel has none.

    ``<reel>.shorts[.<variant>][.normalized].mp4`` first; else the main render, but only when an
    ``.ambience`` render sits beside it (then the main one is the cut with the Track).
    """
    v = f".{variant}" if variant else ""
    own = _first(out / f"{reel}.shorts{v}.normalized.mp4", out / f"{reel}.shorts{v}.mp4")
    if own is not None:
        return own
    music, ambience, _ = sources(out, reel, variant)
    return music if ambience is not None else None


def publish(reel_dir: Path, root: Path = DEFAULT_ROOT, variant: str | None = None,
            platform: str = "instagram", playlist: str | None = None) -> list[Path]:
    """Two files per reel, side by side: the video and its text (Instagram ``Очередь`` or the playlist).

    Instagram gets the no-music render (the author adds the sound in Instagram, 2026-10-12); Shorts
    gets the music render (picking a track on YouTube is hard, 2026-11-01).
    """
    if platform not in PLATFORMS:
        raise SystemExit(f"unknown platform {platform!r}; one of {', '.join(PLATFORMS)}")
    reel_dir = reel_dir.expanduser().resolve()
    script = json.loads((reel_dir / "script.json").read_text())
    title = script.get("title")
    if not title:
        raise SystemExit(f"{reel_dir}/script.json needs a 'title' to publish")
    reel = reel_dir.name
    out = reel_dir / "out"
    if platform == "shorts":
        playlist = playlist or script.get("youtube_playlist")
        if playlist not in PLAYLISTS:
            raise SystemExit(f"a Short needs a playlist (--playlist or youtube_playlist in script.json), "
                             f"one of: {', '.join(PLAYLISTS)}; got {playlist!r}")
        video = shorts_source(out, reel, variant)
        if video is None:
            raise SystemExit(
                f"no music render for Shorts in {out}: render one with the Track to "
                f"out/{reel}.shorts{'.' + variant if variant else ''}.mp4 (cf.build without --no-track, then "
                f"cf.render --out … --fix-loudness), or mux the sound into that file with ffmpeg")
        if _orientation(video) != "вертикаль":
            raise SystemExit(f"{video.name} is not vertical; YouTube Shorts needs a vertical video")
        if _duration_s(video) > SHORTS_MAX_S:
            raise SystemExit(f"{video.name} is longer than {SHORTS_MAX_S:g} s, the Shorts limit")
        txt_name, body = f"{title} — shorts.txt", shorts_text(script, playlist)
        name = f"{title} (shorts).mp4"
        old_names = [name, txt_name]
        old_dirs = list(playlist_dirs(root).values())
        dest = playlist_dirs(root)[playlist]
    else:
        music, ambience, own = sources(out, reel, variant)
        if music is None:
            raise SystemExit(f"no render in {out}" + (f" for variant {variant!r}" if variant else ""))
        if ambience is not None and not own:
            print(f"note: no no-music render for variant {variant!r}; using {ambience.name}", file=sys.stderr)
        video = ambience if ambience is not None else music
        txt_name, body = f"{title} — подпись к посту.txt", caption_text(script)
        name = f"{title} ({_orientation(video)}).mp4"
        old_names = [f"{title} (вертикаль).mp4", f"{title} (горизонталь).mp4", txt_name]
        queue, posted = platform_dirs(root, platform)
        old_dirs = [queue, posted, root.expanduser()]  # the root itself: copies from the old flat layout
        dest = queue

    for d in old_dirs:
        for old in old_names:
            if (d / old).is_file():
                _to_trash(d / old)
    dest.mkdir(parents=True, exist_ok=True)
    target = dest / name
    shutil.copy2(video, target)
    txt = dest / txt_name
    txt.write_text(body)
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
    ap.add_argument("--platform", choices=sorted(PLATFORMS), default="instagram",
                    help="instagram: no-music video + caption; shorts: music video + YouTube text")
    ap.add_argument("--playlist", choices=list(PLAYLISTS),
                    help="YouTube playlist folder for a Short (default: youtube_playlist in script.json)")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--variant", help="publish out/<reel>.<variant>[.normalized].mp4, e.g. hdr or sdr-bright")
    a = ap.parse_args(argv)
    for p in publish(a.reel_dir, a.root, a.variant, a.platform, a.playlist):
        print(p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
