"""Apple SDR mezzanines: HDR clips (iPhone HLG / Dolby Vision) tone-mapped to SDR by AVFoundation.

    python -m cf.mezz <walk_dir> [--clips IMG_1.MOV,IMG_2.MOV] [--force]
    python -m cf.mezz <clip.mov> <out.mov> [--force]

Why (docs/adr/0011-hdr-clips-through-apple-tone-mapping.md): the author judges colour on her
Mac, where QuickTime and Photos show an iPhone HLG clip through Apple's own HDR -> SDR tone
mapping. Resolve's HLG -> Rec.709 conversion does not match it (about +30 to +45 luma levels,
flat, grey sky). So with ``hdr_source`` ``apple-sdr`` (the default, ``style.json``
``color.hdr_source``) cf.build does not give Resolve the HLG file: it gives it
``<walk>/mezz/<stem>.mov``, made by ``tools/apple-sdr`` (Swift, AVFoundation):

- read through ``AVAssetReader`` with the tags ``AVAssetImageGenerator``'s forceSDR returns
  (BT.2020 primaries, SDR 709 transfer), which reproduces Apple's SDR rendition (within
  0.5 level of the generator's frames on IMG_0477);
- converted BT.2020-SDR -> Rec.709 by Core Image with the CoreMedia colour spaces of both tag
  sets (the ColorSync transform a Mac uses to show each), so the 709 file shows as Apple's
  rendition does. Colours outside Rec.709 (a hot-pink hoodie) are clipped: unavoidable in an SDR
  Rec.709 delivery;
- written as ProRes 422 HQ, Rec.709 tags, the source's size, timestamps (fps) and rotation
  matrix, with every audio track passed through.

Resolve imports it as ``Rec.709 Gamma 2.4``, which round-trips unchanged to the Rec.709 output,
so no HLG CDL and no Look are applied to it. SDR clips (DJI/Osmo, iPhone SDR) are used as they
are: Apple shows their code values as they are, and Resolve passes them through.

A mezzanine is cached: ``<stem>.json`` next to it records the source's size and mtime and the
tool's version and method; a change in any remakes it. One conversion at a time (8 GB Mac):
about 9 s for a 27 s 1080p60 clip, about 1.5 GB per 27 s.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TOOL_DIR = REPO_ROOT / "tools" / "apple-sdr"
TOOL = TOOL_DIR / ".build" / "release" / "apple-sdr"
TOOL_VERSION = "1"  # tools/apple-sdr main.swift `version`; bump both when the pixels change
METHOD = "colorsync"

HDR_SOURCES = ("apple-sdr", "resolve")
DEFAULT_HDR_SOURCE = "apple-sdr"
MEZZ_DIR = "mezz"
MEZZ_INPUT_COLOR_SPACE = "Rec.709 Gamma 2.4"
HDR_PROFILES = {"iphone_hlg_dv", "hlg"}
HDR_TRANSFERS = {"arib-std-b67", "smpte2084"}


class MezzError(RuntimeError):
    pass


def is_hdr(clip: dict) -> bool:
    """True for a manifest clip that is HLG or PQ (an iPhone HLG / Dolby Vision clip)."""
    return clip.get("color_profile") in HDR_PROFILES or clip.get("color_transfer") in HDR_TRANSFERS


def hdr_source_default(style: dict) -> str:
    """``style.json`` ``color.hdr_source``, else ``apple-sdr``."""
    value = (style.get("color") or {}).get("hdr_source") or DEFAULT_HDR_SOURCE
    if value not in HDR_SOURCES:
        raise ValueError(f"style.json color.hdr_source must be one of {HDR_SOURCES}, got {value!r}")
    return value


def effective_hdr_source(hdr_source: str, deliver: str) -> str:
    """An HDR delivery needs the HLG itself, so it always reads HDR clips through Resolve."""
    if hdr_source not in HDR_SOURCES:
        raise ValueError(f"hdr_source must be one of {HDR_SOURCES}, got {hdr_source!r}")
    return "resolve" if deliver == "hdr-hlg" else hdr_source


def mezz_path(walk_dir: Path, clip_file: str) -> Path:
    return Path(walk_dir) / MEZZ_DIR / (Path(clip_file).stem + ".mov")


def sidecar_path(mezz: Path) -> Path:
    return mezz.with_suffix(".json")


def source_stamp(src: Path) -> dict:
    st = Path(src).stat()
    return {"path": str(src), "size": st.st_size, "mtime": round(st.st_mtime, 3)}


def is_fresh(src: Path, mezz: Path) -> bool:
    """The cached mezzanine was made from this exact source by this tool version and method."""
    side = sidecar_path(mezz)
    if not (mezz.exists() and side.exists()):
        return False
    try:
        meta = json.loads(side.read_text())
    except (OSError, json.JSONDecodeError):
        return False
    stamp = source_stamp(src)
    old = meta.get("source_file") or {}
    return (old.get("size") == stamp["size"] and old.get("mtime") == stamp["mtime"]
            and meta.get("version") == TOOL_VERSION and meta.get("method") == METHOD)


def plan_sources(clips: dict[str, dict], walk_dir: Path, raw_paths: dict[str, str], hdr_source: str) -> dict[str, dict]:
    """Per clip: the file Resolve imports and its Input Color Space.

    ``clips``: manifest clips by file name; ``raw_paths``: the raw file per clip. HDR clips
    under ``apple-sdr`` get their mezzanine and ``Rec.709 Gamma 2.4``; everything else keeps the
    raw file and the manifest's ``resolve_input_color_space``.
    """
    out = {}
    for name, raw in raw_paths.items():
        c = clips[name]
        if hdr_source == "apple-sdr" and is_hdr(c):
            out[name] = {"path": str(mezz_path(walk_dir, name)), "raw": raw, "mezz": True,
                         "input_color_space": MEZZ_INPUT_COLOR_SPACE}
        else:
            out[name] = {"path": raw, "raw": raw, "mezz": False,
                         "input_color_space": c.get("resolve_input_color_space")}
    return out


def ensure_tool() -> Path:
    """Build tools/apple-sdr (release) when the binary is missing; about 40 s the first time."""
    if TOOL.exists():
        return TOOL
    res = subprocess.run(["swift", "build", "-c", "release"], cwd=TOOL_DIR, capture_output=True, text=True)
    if res.returncode or not TOOL.exists():
        raise MezzError(f"swift build of {TOOL_DIR} failed:\n{res.stderr[-2000:]}")
    return TOOL


def make_mezz(src: Path, dst: Path, force: bool = False) -> dict:
    """Make (or reuse) the mezzanine of ``src`` at ``dst``; returns the sidecar plus ``action``."""
    src, dst = Path(src), Path(dst)
    if not force and is_fresh(src, dst):
        return {**json.loads(sidecar_path(dst).read_text()), "action": "cached"}
    tool = ensure_tool()
    dst.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run([str(tool), "convert", str(src), str(dst), "--method", METHOD],
                         capture_output=True, text=True)
    if res.returncode:
        raise MezzError(f"apple-sdr failed on {src.name}: {res.stderr.strip()[-1500:]}")
    meta = json.loads(res.stdout)
    if meta.get("version") != TOOL_VERSION:
        raise MezzError(f"apple-sdr reports version {meta.get('version')!r}, cf.mezz expects {TOOL_VERSION!r}")
    meta["source_file"] = source_stamp(src)
    sidecar_path(dst).write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
    return {**meta, "action": "made"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="cf.mezz", description=__doc__.split("\n\n")[0])
    ap.add_argument("src", help="Walk folder (with clip_manifest.json) or one clip")
    ap.add_argument("out", nargs="?", help="output .mov (one-clip form)")
    ap.add_argument("--clips", help="comma-separated clip files (Walk form; default every HDR clip)")
    ap.add_argument("--force", action="store_true", help="remake even when the cache is fresh")
    args = ap.parse_args(argv)
    src = Path(args.src).expanduser().resolve()
    try:
        if src.is_file():
            if not args.out:
                ap.error("the one-clip form needs <out.mov>")
            print(json.dumps(make_mezz(src, Path(args.out).expanduser().resolve(), args.force), indent=2,
                             ensure_ascii=False))
            return 0
        manifest = json.loads((src / "clip_manifest.json").read_text())
        from cf.script_schema import manifest_clips  # noqa: PLC0415

        clips = manifest_clips(manifest)
        names = args.clips.split(",") if args.clips else [n for n, c in clips.items() if is_hdr(c)]
        for n in names:
            raw = src / "raw" / n
            raw = raw if raw.exists() else Path(clips[n].get("path") or raw)
            r = make_mezz(raw, mezz_path(src, n), args.force)
            print(f"{n}: {r['action']} {mezz_path(src, n)} ({r.get('seconds', '-')} s)")
    except (MezzError, OSError, KeyError) as exc:
        print(f"cf.mezz: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
