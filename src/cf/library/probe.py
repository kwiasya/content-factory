"""Facts about one Pack file from ffprobe: codec, size, rate, duration, audio, alpha."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cf.probe import parse_rate
from cf.render_check import FFPROBE

ALPHA_PREFIXES = ("yuva", "rgba", "bgra", "argb", "abgr", "gbrap", "ya", "pal8")


def has_alpha(stream: dict) -> bool:
    tags = {k.lower(): v for k, v in (stream.get("tags") or {}).items()}
    if str(tags.get("alpha_mode", "")) == "1":
        return True
    return str(stream.get("pix_fmt") or "").startswith(ALPHA_PREFIXES)


def _num(value) -> float | None:
    try:
        n = float(value)
    except (TypeError, ValueError):
        return None
    return n if n == n else None


def run(path: Path, *, count_frames: bool = False) -> dict:
    cmd = [FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json"]
    if count_frames:
        cmd.insert(3, "-count_packets")
    cmd.append(str(path))
    return json.loads(subprocess.run(cmd, check=True, capture_output=True, text=True).stdout or "{}")


def facts(path: Path, kind: str) -> dict:
    """``kind`` is the extension kind; the result's ``kind`` is refined (an animated gif is video)."""
    gif = path.suffix.lower() == ".gif"
    data = run(path, count_frames=gif)
    streams = data.get("streams") or []
    fmt = data.get("format") or {}
    video = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio = next((s for s in streams if s.get("codec_type") == "audio"), None)
    out: dict = {"codec": None, "pix_fmt": None, "alpha": False, "width": None, "height": None, "fps": None,
                 "duration_s": _num(fmt.get("duration")), "has_audio": audio is not None, "kind": kind}
    if video is not None:
        rate = parse_rate(video.get("avg_frame_rate")) or parse_rate(video.get("r_frame_rate"))
        out.update(codec=video.get("codec_name"), pix_fmt=video.get("pix_fmt"), alpha=has_alpha(video),
                   width=video.get("width"), height=video.get("height"),
                   fps=round(rate, 3) if rate and kind == "video" else None)
    elif audio is not None:
        out["codec"] = audio.get("codec_name")
    if gif and video is not None:
        frames = int(video.get("nb_read_packets") or video.get("nb_frames") or 1)
        out["kind"] = "video" if frames > 1 else "image"
        if out["kind"] == "video":
            rate = parse_rate(video.get("avg_frame_rate")) or parse_rate(video.get("r_frame_rate"))
            out["fps"] = round(rate, 3) if rate else None
    if out["kind"] == "image":
        out["duration_s"] = None
        out["fps"] = None
    if out["duration_s"] is not None:
        out["duration_s"] = round(out["duration_s"], 3)
    return out
