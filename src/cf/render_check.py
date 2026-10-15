"""Verify a rendered Reel file for Instagram: color tags, format, frame rate, loudness.

    python -m cf.render_check <file.mp4> [--target-lufs -14] [--target-tp -1]
                              [--expect-duration S] [--fix-loudness] [--canvas WxH] [--hdr]

Checks (docs/research/03-color-iphone-osmo/result-a.md Section D, and
docs/research/05-music-and-sound/result-a.md for loudness): ffprobe says
bt709/bt709/bt709, color_range tv, yuv420p, the canvas size and fps (``--canvas``, else the
``canvas`` of ``<reel>/script.json`` for a file in ``<reel>/out/``, else ``style.json`` canvas:
2160x3840, 30 fps; ``--canvas 1080x1920`` checks a comparison render), no Dolby Vision side data,
AAC 48 kHz audio; ffmpeg ``loudnorm`` (print mode) gives integrated loudness within
``--lufs-tolerance`` LU of the target and true peak at or below the target.
Prints a PASS/FAIL table and exits 1 on any FAIL.

``--hdr`` checks a Rec.2100 HLG render (``cf.render --hdr``) instead: hevc Main 10 with the
``hvc1`` tag (iOS and Instagram need it), ``yuv420p10le``, bt2020 / arib-std-b67 / bt2020nc,
limited range; the other rows are the same. The SDR default is unchanged.

``--fix-loudness`` runs the two-pass ``loudnorm`` into ``<name>.normalized.mp4`` with the
video stream copied (``-c:v copy``), repeating the second pass on its own output (at most
3 rounds) when loudnorm falls back to dynamic mode and misses, then checks that file
too; the exit code is then the verdict on the normalized file.

The parsing and verdict functions (``parse_probe``, ``parse_loudnorm``, ``evaluate``) are
pure and unit-tested in ``tests/test_render_check.py``.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any

from cf.canvas import Canvas, for_reel

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = REPO_ROOT / "style.json"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"

TARGET_LUFS = -14.0
TARGET_TP = -1.0
TARGET_LRA = 11.0
LUFS_TOLERANCE = 1.0
DURATION_TOLERANCE = 0.1  # seconds; the AAC stream can run a frame or two past the video
BASE_EXPECTED = {
    "pix_fmt": "yuv420p",
    "color_range": "tv",
    "color_primaries": "bt709",
    "color_transfer": "bt709",
    "color_space": "bt709",
    "video_codec": "h264",
    "audio_codec": "aac",
    "sample_rate": 48000,
}
# Rec.2100 HLG delivery (cf.render --hdr): what differs from BASE_EXPECTED.
HDR_EXPECTED = {
    "pix_fmt": "yuv420p10le",
    "color_primaries": "bt2020",
    "color_transfer": "arib-std-b67",
    "color_space": "bt2020nc",
    "video_codec": "hevc",
    "profile": "Main 10",
    "codec_tag": "hvc1",
}
NORMALIZED_SUFFIX = ".normalized"
AUDIO_BITRATE = "256k"
TP_MARGIN = 0.5  # dB of true-peak headroom kept for the AAC encode
MAX_ROUNDS = 3


def expected_for(canvas: Canvas, hdr: bool = False) -> dict:
    """The checked facts for a file rendered at ``canvas`` (``hdr``: Rec.2100 HLG HEVC)."""
    return {"width": canvas.width, "height": canvas.height, "fps": float(canvas.fps), **BASE_EXPECTED,
            **(HDR_EXPECTED if hdr else {})}


def style_canvas(override: str | None = None, script_canvas: str | None = None) -> Canvas:
    """``override`` (CLI) > ``script_canvas`` > style.json ``canvas``."""
    try:
        style = json.loads(STYLE_PATH.read_text())
    except (OSError, ValueError):
        style = {}
    return for_reel(style, script_canvas, override)


def script_canvas_for(path: Path) -> str | None:
    """The ``canvas`` of the Script of a file rendered to ``<reel>/out/<name>.mp4`` (None if none)."""
    for script in (path.parent.parent / "script.json", path.parent / "script.json"):
        try:
            v = json.loads(script.read_text()).get("canvas")
        except (OSError, ValueError, AttributeError):
            continue
        return v if isinstance(v, str) and v.strip() else None
    return None


@dataclass
class Check:
    name: str
    expected: Any
    actual: Any
    ok: bool


# -- pure parsing and verdict ------------------------------------------------------
def _rate(value: str | None) -> float | None:
    if not value or value in ("0/0", "N/A"):
        return None
    try:
        r = Fraction(value)
    except (ValueError, ZeroDivisionError):
        return None
    return float(r) if r else None


def _num(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_probe(j: dict) -> dict:
    """Flatten ``ffprobe -show_streams -show_format -of json`` output to the checked facts."""
    streams = j.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"), {})
    a = next((s for s in streams if s.get("codec_type") == "audio"), {})
    side = [d.get("side_data_type", "") for d in v.get("side_data_list") or []]
    fmt = j.get("format") or {}
    return {
        "video_codec": v.get("codec_name"),
        "codec_tag": v.get("codec_tag_string"),
        "profile": v.get("profile"),
        "width": v.get("width"),
        "height": v.get("height"),
        "pix_fmt": v.get("pix_fmt"),
        "color_range": v.get("color_range"),
        "color_primaries": v.get("color_primaries"),
        "color_transfer": v.get("color_transfer"),
        "color_space": v.get("color_space"),
        "fps": _rate(v.get("r_frame_rate")),
        "avg_fps": _rate(v.get("avg_frame_rate")),
        "nb_frames": int(v["nb_frames"]) if str(v.get("nb_frames", "")).isdigit() else None,
        "video_duration": _num(v.get("duration")),
        "video_bit_rate": _num(v.get("bit_rate")),
        "dovi": any("dovi" in s.lower() or "dolby vision" in s.lower() for s in side),
        "side_data": side,
        "audio_codec": a.get("codec_name"),
        "sample_rate": int(a["sample_rate"]) if str(a.get("sample_rate", "")).isdigit() else None,
        "channels": a.get("channels"),
        "audio_bit_rate": _num(a.get("bit_rate")),
        "duration": _num(fmt.get("duration")),
        "size_bytes": int(fmt["size"]) if str(fmt.get("size", "")).isdigit() else None,
        "bit_rate": _num(fmt.get("bit_rate")),
    }


_JSON_BLOCK = re.compile(r"\{[^{}]*\}", re.S)


def parse_loudnorm(stderr: str) -> dict:
    """The JSON block ``loudnorm=print_format=json`` writes at the end of ffmpeg's stderr."""
    blocks = [b for b in _JSON_BLOCK.findall(stderr) if '"input_i"' in b]
    if not blocks:
        raise ValueError("no loudnorm JSON in ffmpeg output")
    raw = json.loads(blocks[-1])
    out: dict[str, Any] = {}
    for k, val in raw.items():
        n = _num(val)
        out[k] = n if n is not None and k != "normalization_type" else val
    return out


def evaluate(facts: dict, loud: dict | None, target_lufs: float = TARGET_LUFS, target_tp: float = TARGET_TP,
             lufs_tolerance: float = LUFS_TOLERANCE, expect_duration: float | None = None,
             expected: dict | None = None) -> list[Check]:
    """One Check per rule; ``ok`` is the verdict for that row. ``expected`` defaults to the
    style.json canvas (``expected_for``)."""
    exp = expected or expected_for(style_canvas())
    rows: list[Check] = []

    def eq(name: str, key: str) -> None:
        rows.append(Check(name, exp[key], facts.get(key), facts.get(key) == exp[key]))

    eq("video codec", "video_codec")
    if "profile" in exp:
        eq("video profile", "profile")
    if "codec_tag" in exp:
        eq("codec tag", "codec_tag")
    rows.append(Check("resolution", f"{exp['width']}x{exp['height']}",
                      f"{facts.get('width')}x{facts.get('height')}",
                      (facts.get("width"), facts.get("height")) == (exp["width"], exp["height"])))
    fps = facts.get("fps")
    rows.append(Check("frame rate", exp["fps"], None if fps is None else round(fps, 3),
                      fps is not None and abs(fps - exp["fps"]) < 1e-3))
    eq("pixel format", "pix_fmt")
    eq("color range", "color_range")
    eq("color primaries", "color_primaries")
    eq("color transfer", "color_transfer")
    eq("color matrix", "color_space")
    rows.append(Check("Dolby Vision side data", "none", ", ".join(facts.get("side_data") or []) or "none",
                      not facts.get("dovi")))
    eq("audio codec", "audio_codec")
    eq("audio sample rate", "sample_rate")
    dur = video_duration(facts)
    if expect_duration is None:
        rows.append(Check("duration (s)", "> 0", dur, bool(dur and dur > 0)))
    else:
        rows.append(Check("duration (s)", f"{expect_duration:.3f} ±{DURATION_TOLERANCE}", dur,
                          dur is not None and abs(dur - expect_duration) <= DURATION_TOLERANCE))
    if loud is None:
        rows.append(Check("integrated loudness (LUFS)", target_lufs, "not measured", False))
        rows.append(Check("true peak (dBTP)", f"<= {target_tp}", "not measured", False))
    else:
        i, tp = loud.get("input_i"), loud.get("input_tp")
        rows.append(Check("integrated loudness (LUFS)", f"{target_lufs:g} ±{lufs_tolerance:g}", i,
                          isinstance(i, float) and abs(i - target_lufs) <= lufs_tolerance))
        rows.append(Check("true peak (dBTP)", f"<= {target_tp:g}", tp,
                          isinstance(tp, float) and tp <= target_tp + 0.05))
    return rows


def video_duration(facts: dict) -> float | None:
    """Picture duration: frames / fps, else the video stream's duration, else the container's.

    The container duration includes the AAC tail (encoder padding), which runs up to a
    few frames past the picture, so it is only the last resort.
    """
    if facts.get("nb_frames") and facts.get("fps"):
        return round(facts["nb_frames"] / facts["fps"], 4)
    return facts.get("video_duration") or facts.get("duration")


def passed(rows: list[Check]) -> bool:
    return all(r.ok for r in rows)


def format_table(path: Path, rows: list[Check], facts: dict | None = None, loud: dict | None = None) -> str:
    w = max(len(r.name) for r in rows)
    lines = [f"render_check {path}"]
    lines.append(f"  {'check':<{w}}  {'expected':<18} {'actual':<24} verdict")
    for r in rows:
        lines.append(f"  {r.name:<{w}}  {str(r.expected):<18} {str(r.actual):<24} {'PASS' if r.ok else 'FAIL'}")
    if facts:
        mbps = (facts.get("video_bit_rate") or 0) / 1e6
        lines.append(f"  info: {facts.get('profile')} profile, video {mbps:.1f} Mbit/s, "
                     f"{facts.get('nb_frames')} frames, container {facts.get('duration')} s, "
                     f"{facts.get('channels')} audio ch, {(facts.get('size_bytes') or 0) / 1e6:.1f} MB")
    if loud:
        lines.append(f"  loudness: LRA {loud.get('input_lra')} LU, threshold {loud.get('input_thresh')} LUFS")
    lines.append(f"  RESULT: {'PASS' if passed(rows) else 'FAIL'}")
    return "\n".join(lines)


# -- tools -----------------------------------------------------------------------
def ffprobe(path: Path) -> dict:
    out = subprocess.run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)


def _loudnorm_filter(target_lufs: float, target_tp: float, measured: dict | None = None) -> str:
    af = f"loudnorm=I={target_lufs:g}:TP={target_tp:g}:LRA={TARGET_LRA:g}"
    if measured:
        af += (f":measured_I={measured['input_i']}:measured_TP={measured['input_tp']}"
               f":measured_LRA={measured['input_lra']}:measured_thresh={measured['input_thresh']}"
               f":offset={measured['target_offset']}:linear=true")
    return af + ":print_format=json"


def measure_loudness(path: Path, target_lufs: float = TARGET_LUFS, target_tp: float = TARGET_TP) -> dict:
    """First pass of loudnorm (print mode) over the first audio stream."""
    res = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-i", str(path), "-map", "0:a:0",
                          "-af", _loudnorm_filter(target_lufs, target_tp), "-f", "null", "-"],
                         capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(f"ffmpeg loudnorm failed: {res.stderr[-500:]}")
    return parse_loudnorm(res.stderr)


def normalized_path(path: Path) -> Path:
    return path.with_name(path.stem + NORMALIZED_SUFFIX + path.suffix)


def fix_loudness(path: Path, measured: dict, target_lufs: float = TARGET_LUFS, target_tp: float = TARGET_TP,
                 lufs_tolerance: float = LUFS_TOLERANCE, max_rounds: int = MAX_ROUNDS) -> tuple[Path, list[dict]]:
    """Two-pass loudnorm into ``<name>.normalized.mp4``; the video stream is copied.

    Each round is a loudnorm second pass (``linear=true``, the measured values of the
    previous round) on 48 kHz float PCM. On wide-range material (walk ambience with a
    few loud bursts) loudnorm falls back to dynamic mode and undershoots, so a round is
    repeated on its own output until the integrated loudness is within half the
    tolerance, at most ``max_rounds`` times. The true-peak target is lowered by
    ``TP_MARGIN`` because the final AAC encode adds a few tenths of a dB of overshoot.
    The audio is encoded to AAC once, at the end.
    """
    import tempfile  # noqa: PLC0415

    out = normalized_path(path)
    tp = target_tp - TP_MARGIN
    rounds: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="cf-loudnorm-") as tmp:
        cur = Path(tmp) / "r0.wav"
        subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(path), "-map", "0:a:0", "-c:a", "pcm_f32le",
                        "-ar", "48000", str(cur)], check=True)
        meas = measured
        for n in range(1, max_rounds + 1):
            nxt = Path(tmp) / f"r{n}.wav"
            res = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-y", "-i", str(cur),
                                  "-af", _loudnorm_filter(target_lufs, tp, meas) + ",aresample=48000",
                                  "-c:a", "pcm_f32le", str(nxt)], capture_output=True, text=True)
            if res.returncode:
                raise RuntimeError(f"ffmpeg loudnorm pass 2 failed: {res.stderr[-800:]}")
            pass2 = parse_loudnorm(res.stderr)
            meas = measure_loudness(nxt, target_lufs, tp)
            rounds.append({"round": n, "normalization_type": pass2.get("normalization_type"),
                           "integrated": meas["input_i"], "true_peak": meas["input_tp"], "lra": meas["input_lra"]})
            cur = nxt
            if abs(meas["input_i"] - target_lufs) <= lufs_tolerance / 2 and meas["input_tp"] <= tp + 0.1:
                break
        res = subprocess.run([FFMPEG, "-v", "error", "-y", "-i", str(path), "-i", str(cur), "-map", "0:v:0",
                              "-map", "1:a:0", "-c:v", "copy", *video_tag_args(path), "-c:a", "aac",
                              "-b:a", AUDIO_BITRATE, "-ar", "48000", "-movflags", "+faststart", str(out)],
                             capture_output=True, text=True)
        if res.returncode:
            raise RuntimeError(f"ffmpeg mux failed: {res.stderr[-800:]}")
    return out, rounds


def tag_args_for(video_codec: str | None) -> list[str]:
    """Extra mux arguments for a stream copy: ffmpeg's mp4 muxer tags copied HEVC ``hev1``,
    which iOS Photos and Instagram do not play; ``hvc1`` keeps the HLG file playable."""
    return ["-tag:v", "hvc1"] if video_codec == "hevc" else []


def video_tag_args(path: Path) -> list[str]:
    return tag_args_for(parse_probe(ffprobe(path)).get("video_codec"))


def check_file(path: Path, target_lufs: float = TARGET_LUFS, target_tp: float = TARGET_TP,
               lufs_tolerance: float = LUFS_TOLERANCE, expect_duration: float | None = None,
               expected: dict | None = None) -> tuple[list[Check], dict, dict | None]:
    facts = parse_probe(ffprobe(path))
    loud = measure_loudness(path, target_lufs, target_tp) if facts.get("audio_codec") else None
    return evaluate(facts, loud, target_lufs, target_tp, lufs_tolerance, expect_duration, expected), facts, loud


def run(path: Path, target_lufs: float = TARGET_LUFS, target_tp: float = TARGET_TP,
        lufs_tolerance: float = LUFS_TOLERANCE, expect_duration: float | None = None,
        fix: bool = False, report: Path | None = None, expected: dict | None = None) -> int:
    """Check ``path`` (and with ``fix`` its normalized copy); print tables; 0 when the final file passes."""
    expected = expected or expected_for(style_canvas())
    rows, facts, loud = check_file(path, target_lufs, target_tp, lufs_tolerance, expect_duration, expected)
    print(format_table(path, rows, facts, loud))
    result: dict[str, Any] = {"file": str(path), "pass": passed(rows), "checks": [asdict(r) for r in rows],
                              "facts": facts, "loudness": loud}
    final_ok = passed(rows)
    if fix:
        loud_rows = [r for r in rows if "loudness" in r.name or "peak" in r.name]
        if loud is None:
            print("\n--fix-loudness: no audio stream to normalize")
        elif all(r.ok for r in loud_rows):
            print("\n--fix-loudness: loudness already within target, nothing to do")
        else:
            out, rounds = fix_loudness(path, loud, target_lufs, target_tp, lufs_tolerance)
            print("\nloudnorm rounds (on PCM, before the AAC encode):")
            for r in rounds:
                print(f"  round {r['round']}: {r['normalization_type']:<8} I {r['integrated']} LUFS, "
                      f"TP {r['true_peak']} dBTP, LRA {r['lra']} LU")
            print(f"normalized -> {out}")
            rows2, facts2, loud2 = check_file(out, target_lufs, target_tp, lufs_tolerance, expect_duration,
                                              expected)
            print(format_table(out, rows2, facts2, loud2))
            result["normalized"] = {"file": str(out), "pass": passed(rows2), "rounds": rounds,
                                    "checks": [asdict(r) for r in rows2], "facts": facts2, "loudness": loud2}
            final_ok = passed(rows2)
    if report:
        report.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if final_ok else 1


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.render_check", description=__doc__.splitlines()[0])
    ap.add_argument("file", help="rendered .mp4")
    ap.add_argument("--target-lufs", type=float, default=TARGET_LUFS)
    ap.add_argument("--target-tp", type=float, default=TARGET_TP)
    ap.add_argument("--lufs-tolerance", type=float, default=LUFS_TOLERANCE, help="LU either side of the target")
    ap.add_argument("--expect-duration", type=float, help="seconds; checked to ±0.1 s (default: only > 0)")
    ap.add_argument("--fix-loudness", action="store_true",
                    help="two-pass loudnorm into <name>.normalized.mp4 (video copied), then check it")
    ap.add_argument("--report", help="also write the results as JSON here")
    ap.add_argument("--canvas", help="expected canvas: preset (portrait, landscape) or WxH; default the Script's "
                                     "canvas (<reel>/script.json next to out/), else style.json canvas")
    ap.add_argument("--hdr", action="store_true",
                    help="expect a Rec.2100 HLG render: hevc Main 10 hvc1, yuv420p10le, bt2020/arib-std-b67/bt2020nc")
    args = ap.parse_args(argv)
    path = Path(args.file).expanduser().resolve()
    try:
        expected = expected_for(style_canvas(args.canvas, script_canvas_for(path)), hdr=args.hdr)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    if not path.exists():
        print(f"no such file: {path}", file=sys.stderr)
        return 2
    return run(path, args.target_lufs, args.target_tp, args.lufs_tolerance, args.expect_duration,
               args.fix_loudness, Path(args.report) if args.report else None, expected)


if __name__ == "__main__":
    sys.exit(main())
