"""Make 540p SDR Rec.709 analysis proxies for every Clip in a Walk manifest, or for one file.

Usage:
  python -m cf.proxy <clip_manifest.json | raw_dir> <proxy_dir> [--force]
  python -m cf.proxy <media_file> <out_dir | out.mp4> [--force]

The second form needs no manifest: the file is probed on the spot (cf.probe.probe_file:
ffprobe, exiftool when available) and the proxy goes to <out_dir>/<stem>.mp4 (or
<stem>_approx.mp4), or exactly to out.mp4 when the destination ends in .mp4.
From Python: proxy_file(src, dest, force=False) -> result dict with "proxy_path" and "clip".

One ffmpeg at a time (a limit set on the earlier 8 GB M2; not re-measured on the M5 Max 36 GB). HLG sources are tone-mapped with
zscale + tonemap when the ffmpeg build has zscale. Without zscale they get an
approximate conversion (BT.2020 gamma as a stand-in for HLG, then a mild
contrast lift), written as <stem>_approx.mp4 so they are easy to find and
replace once a full ffmpeg is installed.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
from functools import lru_cache
from pathlib import Path

from cf import VIDEO_EXTENSIONS

PROXY_SHORT_SIDE = 540
PROXY_EXT = ".mp4"
APPROX_SUFFIX = "_approx"
VIDEO_BITRATE = "2500k"

# Candidates checked in order; the first one with zscale wins, else the first that runs.
FFMPEG_CANDIDATES = [
    os.environ.get("CF_FFMPEG"),
    "/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg",
    shutil.which("ffmpeg"),
]

HDR_PROFILES = {"iphone_hlg_dv", "hlg"}
LOG_PROFILES = {"apple_log", "dji_dlog", "dji_dlog2"}

# Full HLG -> SDR chain (needs zscale). Scaling first keeps the float stages small.
HLG_TONEMAP = (
    "zscale=tin=arib-std-b67:pin=bt2020:min=bt2020nc:rin=tv:t=linear:npl=100,"
    "format=gbrpf32le,zscale=p=bt709,tonemap=hable:desat=0,"
    "zscale=t=bt709:m=bt709:r=tv,format=yuv420p"
)
# Approximate HLG -> SDR without zscale: treat HLG as BT.2020 gamma (close below
# ~50% signal, highlights clip), convert gamut properly, lift contrast a little.
HLG_APPROX = (
    "format=yuv420p10le,"
    "colorspace=all=bt709:iprimaries=bt2020:itrc=bt2020-10:ispace=bt2020ncl:irange=tv:range=tv:format=yuv420p,"
    "eq=gamma=0.9:contrast=1.1:saturation=1.1"
)


@lru_cache(maxsize=None)
def ffmpeg_filters(binary: str) -> frozenset[str]:
    try:
        out = subprocess.run([binary, "-hide_banner", "-filters"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return frozenset()
    names = set()
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 3 and "->" in parts[2]:
            names.add(parts[1])
    return frozenset(names)


def pick_ffmpeg() -> tuple[str, bool]:
    """Return (ffmpeg binary, has_zscale)."""
    candidates = [c for c in dict.fromkeys(FFMPEG_CANDIDATES) if c and Path(c).exists()]
    if not candidates:
        raise SystemExit("ffmpeg not found (set CF_FFMPEG)")
    for c in candidates:
        if "zscale" in ffmpeg_filters(c):
            return c, True
    return candidates[0], False


def proxy_size(clip: dict) -> tuple[int, int]:
    """Display-oriented proxy size: short side 540, even dimensions, aspect kept."""
    w, h = clip["width"], clip["height"]
    if abs(clip.get("rotation") or 0) % 180 == 90:
        w, h = h, w
    if w <= h:
        pw = PROXY_SHORT_SIDE
        ph = round(h * PROXY_SHORT_SIDE / w / 2) * 2
    else:
        ph = PROXY_SHORT_SIDE
        pw = round(w * PROXY_SHORT_SIDE / h / 2) * 2
    return pw, ph


def build_filter(clip: dict, has_zscale: bool) -> tuple[str, bool]:
    """Return (filtergraph, approx). ffmpeg autorotates before this graph runs."""
    pw, ph = proxy_size(clip)
    in_range = "pc" if clip.get("color_range") == "pc" else "tv"
    profile = clip.get("color_profile")

    if profile in HDR_PROFILES:
        scale = f"scale={pw}:{ph}:flags=bicubic"
        if has_zscale:
            return f"{scale},{HLG_TONEMAP}", False
        return f"{scale},{HLG_APPROX}", True

    if profile in LOG_PROFILES:
        # No LUTs in the repo yet: pass through untransformed and flag it.
        scale = f"scale={pw}:{ph}:flags=bicubic:in_range={in_range}:out_range=tv:out_color_matrix=bt709"
        return f"{scale},format=yuv420p", True

    # rec709 / unknown: scale, normalise to limited range, Rec.709 matrix.
    scale = f"scale={pw}:{ph}:flags=bicubic:in_range={in_range}:out_range=tv:out_color_matrix=bt709"
    return f"{scale},format=yuv420p", False


def ffmpeg_cmd(binary: str, src: Path, dst: Path, vf: str, hwaccel: bool) -> list[str]:
    cmd = [binary, "-hide_banner", "-nostdin", "-v", "error", "-stats", "-y"]
    if hwaccel:
        cmd += ["-hwaccel", "videotoolbox"]
    cmd += [
        "-i", str(src),
        "-map", "0:v:0",
        "-an", "-sn", "-dn",
        "-vf", vf,
        "-c:v", "h264_videotoolbox",
        "-b:v", VIDEO_BITRATE,
        "-profile:v", "high",
        "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709",
        "-color_trc", "bt709",
        "-colorspace", "bt709",
        "-color_range", "tv",
        "-movflags", "+faststart",
        str(dst),
    ]
    return cmd


def proxy_paths(clip: dict, proxy_dir: Path) -> tuple[Path, Path]:
    stem = Path(clip["file"]).stem
    return proxy_dir / f"{stem}{PROXY_EXT}", proxy_dir / f"{stem}{APPROX_SUFFIX}{PROXY_EXT}"


def is_fresh(proxy: Path, src: Path) -> bool:
    return proxy.exists() and proxy.stat().st_size > 0 and proxy.stat().st_mtime > src.stat().st_mtime


def make_proxy(clip: dict, src: Path, proxy_dir: Path, binary: str, has_zscale: bool, force: bool,
               out: Path | None = None) -> dict:
    """Encode one proxy into proxy_dir (Walk naming), or exactly to `out` when given."""
    exact, approx_path = (out, out) if out else proxy_paths(clip, proxy_dir)
    vf, approx = build_filter(clip, has_zscale)
    dst = approx_path if approx else exact

    if not force and is_fresh(dst, src):
        return {"file": clip["file"], "proxy": dst.name, "status": "skipped (fresh)", "approx": approx}
    if not force and approx and exact != approx_path and is_fresh(exact, src):
        # An exact proxy already exists (made with a full ffmpeg earlier); never downgrade it.
        return {"file": clip["file"], "proxy": exact.name, "status": "skipped (exact exists)", "approx": False}

    tmp = dst.with_name(dst.stem + ".partial" + PROXY_EXT)
    started = time.monotonic()
    proc = subprocess.run(ffmpeg_cmd(binary, src, tmp, vf, hwaccel=True), capture_output=True, text=True)
    if proc.returncode != 0:
        # VideoToolbox decode can refuse some streams; retry on the CPU decoder.
        proc = subprocess.run(ffmpeg_cmd(binary, src, tmp, vf, hwaccel=False), capture_output=True, text=True)
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        err = (proc.stderr or "").strip().splitlines()[-5:]
        return {"file": clip["file"], "proxy": None, "status": "FAILED", "approx": approx, "error": "\n".join(err)}

    tmp.replace(dst)
    if not approx and approx_path != exact:
        approx_path.unlink(missing_ok=True)  # an exact proxy supersedes the approximation
    return {
        "file": clip["file"],
        "proxy": dst.name,
        "status": "made",
        "approx": approx,
        "seconds": round(time.monotonic() - started, 1),
    }


def proxy_file(src: Path, dest: Path, force: bool = False) -> dict:
    """Proxy for one media file outside a Walk, no manifest.

    `dest` ending in .mp4 is the exact output path; anything else is a directory that gets
    <stem>.mp4 (or <stem>_approx.mp4). Returns make_proxy's result plus "proxy_path"
    (absolute, None on failure) and "clip" (the cf.probe.probe_file entry).
    """
    from cf.probe import probe_file

    src = Path(src)
    dest = Path(dest)
    clip = probe_file(src)
    out = dest if dest.suffix.lower() == PROXY_EXT else None
    proxy_dir = dest.parent if out else dest
    proxy_dir.mkdir(parents=True, exist_ok=True)
    binary, has_zscale = pick_ffmpeg()
    res = make_proxy(clip, src, proxy_dir, binary, has_zscale, force, out=out)
    res["proxy_path"] = str((proxy_dir / res["proxy"]).resolve()) if res["proxy"] else None
    res["clip"] = clip
    return res


def is_media_file(arg: Path) -> bool:
    return arg.is_file() and arg.suffix.lower() in VIDEO_EXTENSIONS


def single_file(args) -> int:
    res = proxy_file(args.manifest, args.proxy_dir, args.force)
    extra = f" {res['seconds']}s" if "seconds" in res else ""
    flag = "  [approx]" if res["approx"] else ""
    print(f"{res['file']} -> {res['proxy_path'] or '-'} {res['status']}{extra}{flag}", flush=True)
    if res.get("error"):
        print("    " + res["error"].replace("\n", "\n    "), file=sys.stderr)
        return 1
    return 0


def load_manifest(arg: Path) -> Path:
    if arg.is_dir():
        for cand in (arg / "clip_manifest.json", arg.parent / "clip_manifest.json"):
            if cand.exists():
                return cand
        raise SystemExit(f"no clip_manifest.json next to {arg}; run python -m cf.probe first")
    return arg


def resolve_source(clip: dict, manifest: dict, manifest_path: Path) -> Path:
    for cand in (
        Path(clip.get("path", "")),
        Path(manifest.get("raw_dir", "")) / clip["file"],
        manifest_path.parent / "raw" / clip["file"],
    ):
        if cand.is_file():
            return cand
    raise FileNotFoundError(clip["file"])


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.proxy", description=__doc__.splitlines()[0])
    ap.add_argument("manifest", type=Path, help="clip_manifest.json, the raw/ dir next to it, or one media file")
    ap.add_argument("proxy_dir", type=Path, help="proxy directory; for one media file also an exact out .mp4 path")
    ap.add_argument("--force", action="store_true", help="re-encode even when the proxy is newer than the source")
    args = ap.parse_args(argv)

    if is_media_file(args.manifest):
        return single_file(args)

    manifest_path = load_manifest(args.manifest)
    manifest = json.loads(manifest_path.read_text())
    args.proxy_dir.mkdir(parents=True, exist_ok=True)

    binary, has_zscale = pick_ffmpeg()
    print(f"ffmpeg: {binary} (zscale: {'yes' if has_zscale else 'NO, HDR proxies will be approximate'})")

    results = []
    for clip in manifest["clips"]:
        src = resolve_source(clip, manifest, manifest_path)
        res = make_proxy(clip, src, args.proxy_dir, binary, has_zscale, args.force)
        results.append(res)
        extra = f" {res['seconds']}s" if "seconds" in res else ""
        flag = "  [approx]" if res["approx"] else ""
        print(f"{clip['file']:<16} -> {res['proxy'] or '-':<24} {res['status']}{extra}{flag}", flush=True)
        if res.get("error"):
            print("    " + res["error"].replace("\n", "\n    "), file=sys.stderr)

    approx = [r for r in results if r["approx"] and r["proxy"]]
    failed = [r for r in results if r["status"] == "FAILED"]
    if approx:
        print(
            f"\nWARNING: {len(approx)} proxies are approximate ({APPROX_SUFFIX}): "
            + ("HDR tone-map needs an ffmpeg with zscale; re-run once it is installed."
               if not has_zscale else "log footage has no LUT yet.")
        )
    if failed:
        print(f"\n{len(failed)} proxies FAILED", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
