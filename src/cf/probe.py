"""Probe a folder of raw Clips and write clip_manifest.json for the Walk.

Usage: python -m cf.probe <raw_dir> [-o clip_manifest.json]

Color detection follows docs/research/03-color-iphone-osmo/result-a.md Table A.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path

from cf import MANIFEST_SCHEMA, VIDEO_EXTENSIONS

FFPROBE = "ffprobe"
EXIFTOOL = "exiftool"

VFR_TOLERANCE = 0.005  # r_frame_rate vs avg_frame_rate relative difference

# Resolve "Input Color Space" strings per color_profile (Table A). The DJI
# strings are as written in the research and still need checking against the
# Resolve dropdown (smoke test S6).
RESOLVE_INPUT = {
    "iphone_hlg_dv": "Rec.2100 HLG (Scene)",
    "hlg": "Rec.2100 HLG (Scene)",
    "rec709": "Rec.709 Gamma 2.4",
    "apple_log": "Apple Log",
    "dji_dlog": "DJI D-Gamut / DJI D-Log",
    "dji_dlog2": "DJI D-Gamut2 / D-Log2",
}

DJI_GAMMA_SUFFIX = "colorgammasxs"  # matches DjiCameraColorGammaSxS / com.dji.camera.ColorGammaSxS


# --------------------------------------------------------------------------
# Small parsing helpers


def parse_rate(value: str | None) -> float | None:
    if not value or value in ("0/0", "N/A"):
        return None
    try:
        rate = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return float(rate) if rate else None


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def side_data(stream: dict, kind: str) -> dict | None:
    for item in stream.get("side_data_list") or []:
        if item.get("side_data_type") == kind:
            return item
    return None


def find_exif(exif: dict, *names: str):
    """Return the first exif value whose key (group stripped) matches one of names.

    exiftool -G1 keys look like "Keys:CreationDate"; matching is case-insensitive
    on the part after the last colon, in the order names are given. A name with
    a colon must match the full key.
    """
    lowered = {k.lower(): v for k, v in exif.items()}
    for name in names:
        n = name.lower()
        if ":" in n:
            if n in lowered:
                return lowered[n]
            continue
        for key, value in lowered.items():
            if key.rsplit(":", 1)[-1] == n:
                return value
    return None


def find_exif_suffix(exif: dict, suffix: str) -> tuple[str, object] | None:
    for key, value in exif.items():
        bare = key.rsplit(":", 1)[-1].lower().replace(".", "").replace("-", "")
        if bare.endswith(suffix):
            return key, value
    return None


# --------------------------------------------------------------------------
# Classifier (pure; tested in tests/test_probe.py)


def _dji_profile_from_gamma(value) -> str | None:
    norm = str(value).strip().lower().replace("-", "").replace(" ", "").replace("_", "").replace(".", "")
    if norm in ("dlog2",):
        return "dji_dlog2"
    if norm in ("dlog",):
        return "dji_dlog"
    if norm.startswith("dlogm"):
        return None  # Pocket 3 style D-Log M has no native Resolve entry
    if norm in ("rec709", "normal", "bt709"):
        return "rec709"
    if "hlg" in norm:
        return "hlg"
    return None


def classify(stream: dict, exif: dict | None = None) -> dict:
    """Classify a clip's color profile.

    `stream` is an ffprobe video stream dict, `exif` is a flat exiftool -G1 dict.
    Returns color_profile, confidence (high|medium|low), source_field and
    resolve_input_color_space (None when confidence is low).
    """
    exif = exif or {}
    make = str(find_exif(exif, "Keys:Make", "Make") or "").strip()
    transfer = stream.get("color_transfer")
    primaries = stream.get("color_primaries")
    space = stream.get("color_space")
    codec = stream.get("codec_name")
    dovi = side_data(stream, "DOVI configuration record")

    def result(profile, confidence, source_field):
        resolve = RESOLVE_INPUT.get(profile) if confidence != "low" else None
        return {
            "color_profile": profile,
            "confidence": confidence,
            "source_field": source_field,
            "resolve_input_color_space": resolve,
        }

    # 1. DJI: the ColorGammaSxS tag is authoritative (Pocket 4 / 4P).
    gamma = find_exif_suffix(exif, DJI_GAMMA_SUFFIX)
    is_dji = "dji" in make.lower() or gamma is not None
    if is_dji:
        if gamma is not None:
            key, value = gamma
            profile = _dji_profile_from_gamma(value)
            if profile:
                return result(profile, "high", f"exiftool:{key}={value}")
            return result("unknown_dji", "low", f"exiftool:{key}={value} (unrecognised value)")
        return result("unknown_dji", "low", "exiftool:Make=DJI, no ColorGammaSxS tag")

    # 2. Apple Log guess: ProRes + BT.2020 primaries + transfer not HLG.
    if codec == "prores" and primaries == "bt2020" and transfer != "arib-std-b67":
        return result("apple_log", "medium", f"ffprobe:codec_name=prores,color_primaries=bt2020,color_transfer={transfer}")

    # 3. HLG with BT.2020 primaries.
    if transfer == "arib-std-b67" and primaries == "bt2020":
        field = "ffprobe:color_transfer=arib-std-b67,color_primaries=bt2020"
        if dovi:
            field += f",dovi_profile={dovi.get('dv_profile')}"
        if make.lower() == "apple":
            return result("iphone_hlg_dv", "high", field)
        return result("hlg", "medium", field)

    # 4. Rec.709 SDR: all three tags bt709 and no Dolby Vision.
    if transfer == "bt709" and primaries == "bt709" and space == "bt709" and not dovi:
        return result("rec709", "high", "ffprobe:color_transfer=color_primaries=color_space=bt709")

    return result(
        "unknown",
        "low",
        f"ffprobe:color_transfer={transfer},color_primaries={primaries},color_space={space}",
    )


# --------------------------------------------------------------------------
# Tool calls


def run_ffprobe(path: Path) -> dict:
    out = subprocess.run(
        [FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return json.loads(out)


def run_exiftool(paths: list[Path]) -> dict[str, dict]:
    """One exiftool call for all files; returns {filename: flat tag dict}."""
    if not paths:
        return {}
    proc = subprocess.run(
        [EXIFTOOL, "-j", "-n", "-G1", "-a", "-u", "-ee3", "-api", "LargeFileSupport=1", *map(str, paths)],
        capture_output=True,
        text=True,
    )
    if not proc.stdout.strip():
        raise RuntimeError(f"exiftool produced no output: {proc.stderr.strip()}")
    return {Path(item["SourceFile"]).name: item for item in json.loads(proc.stdout)}


def primary_video_stream(probe: dict) -> dict | None:
    videos = [s for s in probe.get("streams", []) if s.get("codec_type") == "video"]
    defaults = [s for s in videos if (s.get("disposition") or {}).get("default")]
    return (defaults or videos or [None])[0]


def parse_creation_time(exif: dict, probe: dict) -> tuple[str | None, str | None]:
    """ISO 8601 creation time with timezone, and the field it came from."""
    keys_date = find_exif(exif, "Keys:CreationDate")
    if keys_date:
        for fmt in ("%Y:%m:%d %H:%M:%S%z", "%Y:%m:%d %H:%M:%S.%f%z"):
            try:
                return datetime.strptime(str(keys_date), fmt).isoformat(), "exiftool:Keys:CreationDate"
            except ValueError:
                pass
    qt_date = find_exif(exif, "QuickTime:CreateDate")
    if qt_date and not str(qt_date).startswith("0000"):
        try:
            # QuickTime CreateDate is UTC by spec.
            dt = datetime.strptime(str(qt_date), "%Y:%m:%d %H:%M:%S").replace(tzinfo=timezone.utc)
            return dt.isoformat(), "exiftool:QuickTime:CreateDate (UTC)"
        except ValueError:
            pass
    tag = (probe.get("format", {}).get("tags") or {}).get("creation_time")
    if tag:
        try:
            return datetime.fromisoformat(tag.replace("Z", "+00:00")).isoformat(), "ffprobe:format.creation_time (UTC)"
        except ValueError:
            pass
    return None, None


def parse_gps(exif: dict) -> dict | None:
    lat = _float(find_exif(exif, "Composite:GPSLatitude"))
    lon = _float(find_exif(exif, "Composite:GPSLongitude"))
    alt = _float(find_exif(exif, "Composite:GPSAltitude"))
    if lat is None or lon is None:
        coords = find_exif(exif, "Keys:GPSCoordinates", "GPSCoordinates")
        if coords:
            parts = str(coords).split()
            if len(parts) >= 2:
                lat, lon = _float(parts[0]), _float(parts[1])
                alt = _float(parts[2]) if len(parts) > 2 else None
    if lat is None or lon is None:
        return None
    gps = {"lat": lat, "lon": lon}
    if alt is not None:
        gps["alt_m"] = alt
    return gps


def probe_clip(path: Path, exif: dict) -> dict:
    probe = run_ffprobe(path)
    stream = primary_video_stream(probe)
    if stream is None:
        raise ValueError(f"{path.name}: no video stream")

    matrix = side_data(stream, "Display Matrix")
    rotation = _int(matrix.get("rotation")) if matrix else 0
    width, height = stream.get("width"), stream.get("height")
    if rotation is not None and abs(rotation) % 180 == 90:
        display_w, display_h = height, width
    else:
        display_w, display_h = width, height

    r_fps = parse_rate(stream.get("r_frame_rate"))
    avg_fps = parse_rate(stream.get("avg_frame_rate"))
    vfr = bool(r_fps and avg_fps and abs(r_fps - avg_fps) / r_fps > VFR_TOLERANCE)

    duration = _float(stream.get("duration")) or _float(probe.get("format", {}).get("duration"))
    dovi = side_data(stream, "DOVI configuration record")
    created, created_field = parse_creation_time(exif, probe)
    software = find_exif(exif, "Keys:Software", "Software")

    clip = {
        "file": path.name,
        "path": str(path.resolve()),
        "size_bytes": path.stat().st_size,
        "device": {
            "make": find_exif(exif, "Keys:Make", "Make"),
            "model": find_exif(exif, "Keys:Model", "Model"),
            "software": str(software) if software is not None else None,
        },
        "codec": stream.get("codec_name"),
        "profile": stream.get("profile"),
        "width": width,
        "height": height,
        "rotation": rotation,
        "display_width": display_w,
        "display_height": display_h,
        "r_frame_rate": stream.get("r_frame_rate"),
        "fps": round(r_fps, 6) if r_fps else None,
        "avg_frame_rate": stream.get("avg_frame_rate"),
        "avg_fps": round(avg_fps, 6) if avg_fps else None,
        "vfr": vfr,
        "duration_s": round(duration, 3) if duration is not None else None,
        "nb_frames": _int(stream.get("nb_frames")),
        "pix_fmt": stream.get("pix_fmt"),
        "color_range": stream.get("color_range"),
        "color_space": stream.get("color_space"),
        "color_transfer": stream.get("color_transfer"),
        "color_primaries": stream.get("color_primaries"),
        "dovi": (
            {
                "profile": dovi.get("dv_profile"),
                "level": dovi.get("dv_level"),
                "bl_signal_compatibility_id": dovi.get("dv_bl_signal_compatibility_id"),
            }
            if dovi
            else None
        ),
        "creation_time": created,
        "creation_time_source": created_field,
        "gps": parse_gps(exif),
    }
    clip.update(classify(stream, exif))
    return clip


# --------------------------------------------------------------------------
# CLI


def list_clips(raw_dir: Path) -> list[Path]:
    return sorted(
        p for p in raw_dir.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS and not p.name.startswith(".")
    )


def build_manifest(raw_dir: Path) -> dict:
    raw_dir = raw_dir.resolve()
    clips = list_clips(raw_dir)
    exif_by_name = run_exiftool(clips)
    entries = [probe_clip(p, exif_by_name.get(p.name, {})) for p in clips]
    walk = raw_dir.parent.name if raw_dir.name == "raw" else raw_dir.name
    return {
        "schema": MANIFEST_SCHEMA,
        "walk": walk,
        "raw_dir": str(raw_dir),
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
        "clips": entries,
    }


def format_table(manifest: dict) -> str:
    header = ("clip", "device", "WxH", "rot", "fps", "dur", "profile", "confidence")
    rows = [header]
    for c in manifest["clips"]:
        device = " ".join(x for x in (c["device"].get("make"), c["device"].get("model")) if x) or "?"
        fps = f"{c['fps']:g}" if c.get("fps") else "?"
        if c.get("vfr"):
            fps += f" (vfr {c['avg_fps']:.2f})"
        rows.append(
            (
                c["file"],
                device,
                f"{c['width']}x{c['height']}",
                str(c["rotation"]),
                fps,
                f"{c['duration_s']:.1f}" if c.get("duration_s") is not None else "?",
                c["color_profile"],
                c["confidence"],
            )
        )
    widths = [max(len(r[i]) for r in rows) for i in range(len(header))]
    lines = ["  ".join(cell.ljust(w) for cell, w in zip(row, widths)).rstrip() for row in rows]
    lines.insert(1, "  ".join("-" * w for w in widths))
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.probe", description=__doc__.splitlines()[0])
    ap.add_argument("raw_dir", type=Path)
    ap.add_argument("-o", "--output", type=Path, help="default: <raw_dir>/../clip_manifest.json when raw_dir is named raw/, else ./clip_manifest.json")
    args = ap.parse_args(argv)

    if not args.raw_dir.is_dir():
        ap.error(f"not a directory: {args.raw_dir}")
    manifest = build_manifest(args.raw_dir)
    if not manifest["clips"]:
        print(f"no video files in {args.raw_dir}", file=sys.stderr)
        return 1

    out = args.output
    if out is None:
        raw = args.raw_dir.resolve()
        out = (raw.parent if raw.name == "raw" else Path.cwd()) / "clip_manifest.json"
    out.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n")

    print(format_table(manifest))
    low = [c for c in manifest["clips"] if c["confidence"] != "high"]
    print(f"\n{len(manifest['clips'])} clips -> {out}")
    if low:
        print("needs a decision (confidence below high):")
        for c in low:
            print(f"  {c['file']}: {c['color_profile']} ({c['confidence']}) from {c['source_field']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
