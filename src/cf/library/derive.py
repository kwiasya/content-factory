"""Derived files of the Library cache (keyed alpha, converted gifs, png stills, previews) and loudness."""

from __future__ import annotations

import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Callable

from cf.render_check import FFMPEG


@lru_cache(maxsize=1)
def ffmpeg_version() -> str | None:
    try:
        out = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    words = out.split()
    return words[2] if len(words) > 2 and words[0] == "ffmpeg" else None


def run(cache: Path, root: Path, assets: list[dict], report, *, key: bool, previews: bool, loudness: bool,
        log: Callable[[str], None]) -> None:
    return None


def remove_orphans(cache: Path, keep: set[str]) -> int:
    return 0
