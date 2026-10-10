"""Shared helpers: tool paths, proxy probing and 1 s binning of timestamped samples."""

from __future__ import annotations

import json
import math
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Sequence

import numpy as np

# Output reference: shake and translation are reported in px at 1080 px short side
# (the width of a 1080x1920 Reel), whatever the proxy size.
REF_SHORT_SIDE = 1080
# A trailing partial second shorter than this is dropped from the bins.
MIN_LAST_BIN_S = 0.5


def ffmpeg_bin() -> str:
    for cand in (os.environ.get("CF_FFMPEG"), "/opt/homebrew/bin/ffmpeg", shutil.which("ffmpeg")):
        if cand and Path(cand).exists():
            return cand
    raise FileNotFoundError("ffmpeg not found (set CF_FFMPEG)")


def ffprobe_bin() -> str:
    ff = Path(ffmpeg_bin())
    sibling = ff.with_name("ffprobe")
    if sibling.exists():
        return str(sibling)
    found = shutil.which("ffprobe")
    if not found:
        raise FileNotFoundError("ffprobe not found")
    return found


def tool_version(binary: str) -> str | None:
    try:
        out = subprocess.run([binary, "-version"], capture_output=True, text=True, timeout=10).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    first = out.splitlines()[0] if out else ""
    parts = first.split()
    return parts[2] if len(parts) > 2 else first or None


@dataclass(frozen=True)
class ProxyInfo:
    path: Path
    width: int
    height: int
    duration_s: float
    fps: float | None
    color_range: str | None
    creation_time: str | None

    @property
    def short_side(self) -> int:
        return min(self.width, self.height)

    @property
    def px_scale(self) -> float:
        """Multiply proxy pixels by this to get px at REF_SHORT_SIDE."""
        return REF_SHORT_SIDE / self.short_side


def probe_proxy(path: Path) -> ProxyInfo:
    out = subprocess.run(
        [ffprobe_bin(), "-v", "error", "-select_streams", "v:0", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    data = json.loads(out)
    stream = data["streams"][0]
    fmt = data.get("format", {})
    duration = stream.get("duration") or fmt.get("duration")
    fps = None
    rate = stream.get("avg_frame_rate") or stream.get("r_frame_rate")
    if rate and rate not in ("0/0", "N/A"):
        num, _, den = rate.partition("/")
        try:
            fps = float(num) / float(den or 1)
        except (ValueError, ZeroDivisionError):
            fps = None
    w, h = int(stream["width"]), int(stream["height"])
    rotation = 0
    for sd in stream.get("side_data_list") or []:
        if sd.get("side_data_type") == "Display Matrix":
            rotation = int(sd.get("rotation") or 0)
    if abs(rotation) % 180 == 90:
        w, h = h, w
    tags = (fmt.get("tags") or {}) | (stream.get("tags") or {})
    return ProxyInfo(
        path=path,
        width=w,
        height=h,
        duration_s=float(duration),
        fps=fps,
        color_range=stream.get("color_range"),
        creation_time=tags.get("creation_time"),
    )


def n_bins(duration_s: float) -> int:
    """Number of 1 s bins: full seconds plus a trailing partial one if >= MIN_LAST_BIN_S."""
    full = int(math.floor(duration_s + 1e-9))
    rest = duration_s - full
    return max(1, full + (1 if rest >= MIN_LAST_BIN_S else 0))


def bin_reduce(
    times: Sequence[float],
    values: Sequence[float],
    nbins: int,
    reducer: Callable[[np.ndarray], float] = np.mean,
) -> list[float | None]:
    """Group samples by floor(t) into nbins 1 s bins and reduce each; empty bins -> None.

    Samples past the last bin (a dropped partial second) fold into the last bin.
    NaN values are ignored.
    """
    t = np.asarray(times, dtype=float)
    v = np.asarray(values, dtype=float)
    out: list[float | None] = [None] * nbins
    if t.size == 0:
        return out
    idx = np.clip(np.floor(t + 1e-9).astype(int), 0, nbins - 1)
    for b in range(nbins):
        sel = v[(idx == b) & ~np.isnan(v)]
        if sel.size:
            out[b] = float(reducer(sel))
    return out


def fill_gaps(values: Sequence[float | None]) -> list[float | None]:
    """Fill None bins from the nearest earlier (else later) bin; all-None stays None."""
    vals = list(values)
    known = [i for i, v in enumerate(vals) if v is not None]
    if not known:
        return vals
    for i, v in enumerate(vals):
        if v is None:
            j = min(known, key=lambda k: (abs(k - i), k > i))
            vals[i] = vals[j]
    return vals


def rounded(values: Sequence[float | None], nd: int = 3) -> list[float | None]:
    return [None if v is None else round(float(v), nd) for v in values]
