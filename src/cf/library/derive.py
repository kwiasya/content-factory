"""Derived files of the Library cache (keyed alpha, converted gifs, png stills, posters, previews) and loudness.

Every target is named by the Asset id and made only when missing; ffmpeg writes a temp file beside it that is
then moved into place. A failure is an error line of the report, never a crash of the run.
"""

from __future__ import annotations

import math
import os
import subprocess
from functools import lru_cache
from pathlib import Path
from typing import Callable

from cf.library import refs
from cf.library.files import temp_beside
from cf.render_check import FFMPEG, parse_loudnorm

SUBDIRS = ("keyed", "converted", "png", "previews")
STILL_TO_PNG = {"jfif", "webp", "avif", "bmp", "tif", "tiff", "webm"}
BACKDROP = "0x202020"
POSTER_W = 240
PREVIEW_S = 8
LOUDNORM = "loudnorm=I=-14:TP=-1:LRA=11:print_format=json"


@lru_cache(maxsize=1)
def ffmpeg_version() -> str | None:
    try:
        out = subprocess.run([FFMPEG, "-version"], capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return None
    words = out.split()
    return words[2] if len(words) > 2 and words[0] == "ffmpeg" else None


class FfmpegFailed(Exception):
    pass


def _ffmpeg(args: list[str], target: Path) -> None:
    tmp = temp_beside(target)
    try:
        res = subprocess.run([FFMPEG, "-v", "error", "-y", "-nostdin", *args, str(tmp)],
                             capture_output=True, text=True)
        if res.returncode or not tmp.is_file():
            raise FfmpegFailed(res.stderr.strip()[-300:] or f"ffmpeg exit {res.returncode}")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)


def _input(path: Path, *, vp9_alpha: bool = False, seek: float | None = None, limit: float | None = None) -> list[str]:
    out: list[str] = []
    if seek:
        out += ["-ss", f"{seek:.3f}"]
    if limit:
        out += ["-t", str(limit)]
    if vp9_alpha:
        out += ["-c:v", "libvpx-vp9"]
    return out + ["-i", str(path)]


def _over_backdrop(width: int | None, height: int | None, tail: str) -> list[str]:
    w, h = width or 512, height or 512
    return ["-filter_complex", f"color=c={BACKDROP}:s={w}x{h}[bg];[0:v]setpts=PTS-STARTPTS[fg];[bg][fg]overlay=shortest=1,{tail}"]


def chroma_key(src: Path, target: Path, color: str, similarity: float, blend: float) -> None:
    vf = (f"chromakey=color={color}:similarity={similarity}:blend={blend},despill=type=green,"
          "format=yuva444p10le")
    _ffmpeg(["-i", str(src), "-vf", vf, "-c:v", "prores_ks", "-profile:v", "4444", "-qscale:v", "9",
             "-pix_fmt", "yuva444p10le", "-vendor", "apl0", "-an"], target)


def gif_to_mov(src: Path, target: Path) -> None:
    _ffmpeg(["-i", str(src), "-vf", "format=yuva444p10le", "-c:v", "prores_ks", "-profile:v", "4444",
             "-qscale:v", "9", "-pix_fmt", "yuva444p10le", "-vendor", "apl0"], target)


def to_png(src: Path, target: Path, *, vp9_alpha: bool = False) -> None:
    _ffmpeg([*_input(src, vp9_alpha=vp9_alpha), "-frames:v", "1"], target)


def poster(src: Path, target: Path, *, duration: float | None, alpha: bool, vp9_alpha: bool,
           width: int | None, height: int | None) -> None:
    seek = min(1.0, duration / 3) if duration and duration > 0.1 else None
    tail = f"scale={POSTER_W}:-2"
    filt = _over_backdrop(width, height, tail) if alpha else ["-vf", tail]
    _ffmpeg([*_input(src, vp9_alpha=vp9_alpha, seek=seek), *filt, "-frames:v", "1"], target)


def preview(src: Path, target: Path, *, alpha: bool, vp9_alpha: bool, width: int | None, height: int | None) -> None:
    tail = f"scale={POSTER_W}:-2,format=yuv420p"
    filt = _over_backdrop(width, height, tail) if alpha else ["-vf", tail]
    _ffmpeg([*_input(src, vp9_alpha=vp9_alpha, limit=PREVIEW_S), *filt, "-c:v", "libx264", "-preset", "veryfast",
             "-crf", "28", "-an", "-movflags", "+faststart"], target)


def measure(src: Path) -> dict:
    def once(af: str) -> dict:
        res = subprocess.run([FFMPEG, "-hide_banner", "-nostats", "-nostdin", "-i", str(src), "-map", "0:a:0",
                              "-af", af, "-f", "null", "-"], capture_output=True, text=True)
        if res.returncode:
            raise FfmpegFailed(res.stderr.strip()[-300:])
        return parse_loudnorm(res.stderr)

    def finite(v) -> bool:
        return isinstance(v, (int, float)) and math.isfinite(v)

    m, method = once(LOUDNORM), "loudnorm"
    if not finite(m.get("input_i")):
        m, method = once(f"apad=whole_dur=3,{LOUDNORM}"), "padded"
    if not finite(m.get("input_i")):
        raise FfmpegFailed(f"loudness is not finite: {m.get('input_i')}")
    out = {"i": m.get("input_i"), "tp": m.get("input_tp"), "lra": m.get("input_lra"), "method": method}
    return {k: (v if not isinstance(v, float) or math.isfinite(v) else None) for k, v in out.items()}


def _have(cache: Path, rel: str | None) -> bool:
    return bool(rel) and (cache / rel).is_file()


def run(cache: Path, root: Path, assets: list[dict], report, *, key: bool, previews: bool, loudness: bool,
        log: Callable[[str], None]) -> None:
    if not key:
        report.skipped.append("key")
    if not previews:
        report.skipped.append("previews")
    if not loudness:
        report.skipped.append("loudness")
    for sub in SUBDIRS:
        (cache / sub).mkdir(parents=True, exist_ok=True)
    for i, a in enumerate(assets, 1):
        _derive_one(cache, root, a, report, key=key, previews=previews, loudness=loudness, folder=a.get("_folder"))
        if i % 100 == 0:
            log(f"derive: {i}/{len(assets)}")


def _derive_one(cache: Path, root: Path, a: dict, report, *, key: bool, previews: bool, loudness: bool,
                folder) -> None:
    ref = refs.make(a["category"], a["name"])
    primary = a["variants"][0]
    src = root / primary["path"]
    ext = primary["path"].rsplit(".", 1)[-1].lower()
    d = a["derived"]
    aid = a["id"]

    def step(name: str, fn: Callable[[], None]) -> bool:
        try:
            fn()
            return True
        except (FfmpegFailed, OSError, ValueError) as exc:
            report.errors.append({"ref": ref, "step": name, "stderr": str(exc)[-300:]})
            return False

    if a["kind"] == "video":
        if a["green_screen"] and folder is not None and folder.key:
            if not _have(cache, d["alpha"]):
                if key:
                    rel = f"keyed/{aid}.mov"
                    if step("key", lambda: chroma_key(src, cache / rel, folder.key, folder.key_similarity,
                                                       folder.key_blend)):
                        d["alpha"] = rel
                        report.derived["keyed"] += 1
                else:
                    d["alpha"] = None
        if ext == "gif" and not _have(cache, d["converted"]):
            rel = f"converted/{aid}.mov"
            if step("convert", lambda: gif_to_mov(src, cache / rel)):
                d["converted"] = rel
                report.derived["converted"] += 1
    has_still = any(v["role"] == "still" for v in a["variants"])
    if a["kind"] == "image" and ext in STILL_TO_PNG | {"gif"} and not has_still and not _have(cache, d["png"]):
        rel = f"png/{aid}.png"
        vp9 = primary.get("codec") == "vp9" and bool(primary.get("alpha"))
        if step("png", lambda: to_png(src, cache / rel, vp9_alpha=vp9)):
            d["png"] = rel
            report.derived["png"] += 1

    if previews and a["kind"] in ("video", "image"):
        vsrc, alpha, vp9 = _visual_source(cache, root, a)
        if not _have(cache, d["poster"]):
            rel = f"previews/{aid}.jpg"
            if step("poster", lambda: poster(vsrc, cache / rel, duration=a.get("duration_s"), alpha=alpha,
                                             vp9_alpha=vp9, width=a.get("width"), height=a.get("height"))):
                d["poster"] = rel
                report.derived["previews"] += 1
        if a["kind"] == "video" and not _have(cache, d["preview"]):
            rel = f"previews/{aid}.mp4"
            if step("preview", lambda: preview(vsrc, cache / rel, alpha=alpha, vp9_alpha=vp9,
                                               width=a.get("width"), height=a.get("height"))):
                d["preview"] = rel
                report.derived["previews"] += 1

    if loudness and a.get("has_audio") and a.get("loudness") is None:
        def meas() -> None:
            a["loudness"] = measure(src)
        if step("loudness", meas):
            report.derived["loudness"] += 1


def _visual_source(cache: Path, root: Path, a: dict) -> tuple[Path, bool, bool]:
    """The file a poster or preview is made from, whether it carries alpha, and whether it is VP9 alpha."""
    d = a["derived"]
    if d.get("alpha") and (cache / d["alpha"]).is_file():
        return cache / d["alpha"], True, False
    alpha_v = next((v for v in a["variants"] if v["role"] == "alpha"), None)
    if alpha_v is not None:
        return root / alpha_v["path"], True, False
    if d.get("converted") and (cache / d["converted"]).is_file():
        return cache / d["converted"], True, False
    primary = a["variants"][0]
    if d.get("png") and (cache / d["png"]).is_file():
        return cache / d["png"], bool(primary.get("alpha")), False
    still = next((v for v in a["variants"] if v["role"] == "still"), None)
    if a["kind"] == "image" and still is not None:
        return root / still["path"], bool(still.get("alpha")), False
    vp9 = primary.get("codec") == "vp9" and bool(primary.get("alpha"))
    return root / primary["path"], bool(primary.get("alpha")), vp9


def remove_orphans(cache: Path, keep: set[str]) -> int:
    n = 0
    for sub in SUBDIRS:
        folder = cache / sub
        if not folder.is_dir():
            continue
        for p in folder.iterdir():
            if not p.is_file() or p.is_symlink():
                continue
            leftover = p.name.startswith(".") and (".part" in p.name or p.name.endswith(".tmp"))
            if leftover or (not p.name.startswith(".") and p.name.split(".", 1)[0] not in keep):
                p.unlink()
                n += 1
    return n
