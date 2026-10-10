"""Contact sheet: 12 frames between in/out of a proxy as a 3x4 grid with burned-in timestamps.

Usage: python -m cf.sheet <proxy> <in_s> <out_s> [-o out.png]

Frames are evenly spaced (centre of 12 equal slices). Long edge <= 1568 px, so
the sheet fits one image input without downscaling.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from cf.metrics.common import ffmpeg_bin, probe_proxy

COLS, ROWS = 3, 4
N = COLS * ROWS
MAX_LONG_EDGE = 1568
PAD = 4  # px between and around tiles
FONTS = ["/System/Library/Fonts/Menlo.ttc", "/System/Library/Fonts/Helvetica.ttc", "/Library/Fonts/Arial.ttf"]


def tile_size(w: int, h: int) -> tuple[int, int]:
    """Largest even tile size keeping the 3x4 sheet's long edge <= MAX_LONG_EDGE."""
    sheet_w = lambda k: COLS * w * k + PAD * (COLS + 1)
    sheet_h = lambda k: ROWS * h * k + PAD * (ROWS + 1)
    k = min((MAX_LONG_EDGE - PAD * (COLS + 1)) / (COLS * w), (MAX_LONG_EDGE - PAD * (ROWS + 1)) / (ROWS * h), 1.0)
    tw, th = int(w * k) // 2 * 2, int(h * k) // 2 * 2
    assert max(sheet_w(tw / w), sheet_h(th / h)) <= MAX_LONG_EDGE + 1
    return tw, th


def build_cmd(proxy: Path, in_s: float, out_s: float, out: Path, w: int, h: int) -> list[str]:
    dur = out_s - in_s
    tw, th = tile_size(w, h)
    times = [in_s + (i + 0.5) * dur / N for i in range(N)]
    # select the first frame at/after each target time (VFR-safe, no fps resampling)
    expr = "+".join(f"gte(t\\,{t:.3f})*lt(prev_selected_t\\,{t:.3f})" for t in times)
    font = next((f for f in FONTS if Path(f).exists()), None)
    fontsize = max(12, th // 20)
    draw = (
        "drawtext="
        + (f"fontfile='{font}':" if font else "")
        + f"text='%{{pts\\:hms}}':x=6:y=h-th-6:fontsize={fontsize}:fontcolor=white:box=1:boxcolor=black@0.55:boxborderw=4"
    )
    vf = (
        f"select='gt(isnan(prev_selected_t)*gte(t\\,{times[0]:.3f})+{expr}\\,0)',"
        f"scale={tw}:{th},{draw},tile={COLS}x{ROWS}:padding={PAD}:margin={PAD}:color=black"
    )
    return [
        ffmpeg_bin(), "-hide_banner", "-nostdin", "-loglevel", "error", "-y",
        "-i", str(proxy), "-vf", vf, "-fps_mode", "passthrough", "-frames:v", "1", "-update", "1", str(out),
    ]


def make_sheet(proxy: Path, in_s: float, out_s: float, out: Path | None = None) -> Path:
    info = probe_proxy(proxy)
    out_s = min(out_s, info.duration_s)
    if out_s <= in_s:
        raise ValueError(f"out ({out_s}) must be after in ({in_s})")
    out = out or proxy.with_name(f"{proxy.stem}_{in_s:g}-{out_s:g}.png")
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(build_cmd(proxy, in_s, out_s, out, info.width, info.height), capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        raise RuntimeError(f"ffmpeg sheet failed: {proc.stderr[-1500:]}")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.sheet", description=__doc__.splitlines()[0])
    ap.add_argument("proxy", type=Path)
    ap.add_argument("in_s", type=float)
    ap.add_argument("out_s", type=float)
    ap.add_argument("-o", "--output", type=Path)
    args = ap.parse_args(argv)
    print(make_sheet(args.proxy, args.in_s, args.out_s, args.output))
    return 0


if __name__ == "__main__":
    sys.exit(main())
