"""Rec.2100 HLG delivery helpers: HLG math and SDR overlays placed at HDR graphics white.

    python -m cf.hdr overlay <sdr.mov> <hlg.mov>

An HDR build (``cf.build --deliver hdr-hlg``) outputs Rec.2100 HLG. The overlays are SDR
ProRes 4444 with alpha (Remotion, Rec.709). Resolve's inverse DRT (``useInverseDRT='1'``,
needed for the HLG clips to round-trip) maps SDR white to about 1000 nits, the HLG peak,
which makes white text glare on an HDR screen. So the build converts each overlay to HLG
itself, per ITU-R BT.2408: SDR white = HDR graphics white, 203 nits = 75 % HLG signal.
The converted file is tagged and imported as ``Rec.2020 HLG ARIB STD-B67``, which
round-trips through the timeline unchanged (docs/research/hdr-hlg-delivery.md).

Per pixel (``sdr_to_hlg``): Rec.709 code -> display light (gamma 2.4, 1.0 = SDR white) ->
x 203 nits -> Rec.2020 primaries -> HLG inverse EOTF at 1000 nits (inverse OOTF with
system gamma 1.2 on luminance, then the OETF).

Alpha (``log_composite_alpha``): Resolve composites V2 over V1 in the timeline space,
DaVinci Intermediate (log). Over a bright HDR sky that darkens a soft black backdrop about
2.5x more (in stops) than the gamma-space composite the overlay was designed in (measured:
-1.4 to -1.8 stops instead of -0.5 to -0.6). The alpha is rescaled so the log composite
gives the design's display-gamma result over a reference background of ``REF_BG_NITS``
(the overlays sit over sky); opaque pixels and alpha 0 are unchanged.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np

from cf.look import LUMA_709, REC709_TO_XYZ, di_encode, rgb_to_xyz

FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"
FFPROBE = shutil.which("ffprobe") or "/opt/homebrew/bin/ffprobe"

# ITU-R BT.2100 HLG
HLG_A = 0.17883277
HLG_B = 1 - 4 * HLG_A
HLG_C = 0.5 - HLG_A * np.log(4 * HLG_A)
PEAK_NITS = 1000.0
SYSTEM_GAMMA = 1.2  # at 1000 nits
GRAPHICS_WHITE_NITS = 203.0  # ITU-R BT.2408: HDR reference / graphics white (75 % HLG)
SDR_GAMMA = 2.4

REC2020_TO_XYZ = rgb_to_xyz(((0.708, 0.292), (0.170, 0.797), (0.131, 0.046)), (0.3127, 0.3290))
REC709_TO_2020 = np.linalg.solve(REC2020_TO_XYZ, REC709_TO_XYZ)
LUMA_2020 = REC2020_TO_XYZ[1]  # 0.2627 0.6780 0.0593

WORKING_NITS_PER_UNIT = 100.0  # timeline linear 1.0 = 100 nits (DaVinci Intermediate, HDR 1000)
REF_BG_NITS = 300.0  # typical background under the overlays (sky, 290-460 nits in reel-01)

# Resolve strings (docs/resolve-rules.md): the HLG clip input and the matching output.
HLG_INPUT_COLOR_SPACE = "Rec.2020 HLG ARIB STD-B67"


def hlg_oetf(e: np.ndarray) -> np.ndarray:
    """Scene-linear (0..1) -> HLG signal (0..1)."""
    e = np.clip(np.asarray(e, dtype=np.float64), 0, 1)
    with np.errstate(divide="ignore", invalid="ignore"):
        log = HLG_A * np.log(np.maximum(12 * e - HLG_B, 1e-12)) + HLG_C
    return np.where(e <= 1 / 12, np.sqrt(3 * e), log)


def hlg_inverse_oetf(v: np.ndarray) -> np.ndarray:
    """HLG signal (0..1) -> scene-linear (0..1)."""
    v = np.clip(np.asarray(v, dtype=np.float64), 0, 1)
    return np.where(v <= 0.5, v * v / 3, (np.exp((v - HLG_C) / HLG_A) + HLG_B) / 12)


def hlg_signal_to_nits(v: np.ndarray) -> np.ndarray:
    """HLG signal of a neutral (grey) pixel -> display luminance in nits at a 1000-nit peak."""
    return PEAK_NITS * hlg_inverse_oetf(v) ** SYSTEM_GAMMA


def nits_to_hlg_signal(nits: np.ndarray) -> np.ndarray:
    """Display luminance of a neutral pixel (nits) -> HLG signal at a 1000-nit peak."""
    return hlg_oetf((np.asarray(nits, dtype=np.float64) / PEAK_NITS) ** (1 / SYSTEM_GAMMA))


def sdr_to_hlg(code: np.ndarray, white_nits: float = GRAPHICS_WHITE_NITS) -> np.ndarray:
    """Rec.709 gamma-2.4 RGB code values (..., 3), 0..1 -> Rec.2100 HLG RGB code values, 0..1.

    SDR white (1, 1, 1) lands at ``white_nits`` (203 -> 0.75), black at 0.
    """
    rgb = np.clip(np.asarray(code, dtype=np.float64), 0, 1) ** SDR_GAMMA * (white_nits / PEAK_NITS)
    rgb = np.clip(rgb @ REC709_TO_2020.T, 0, None)  # display light, 1.0 = 1000 nits
    yd = rgb @ LUMA_2020
    with np.errstate(divide="ignore", invalid="ignore"):
        # inverse OOTF: E_s = F_d / Y_d^((gamma-1)/gamma)  (normalised to the peak)
        scale = np.where(yd > 0, np.power(np.maximum(yd, 1e-12), (1 - SYSTEM_GAMMA) / SYSTEM_GAMMA), 0.0)
    return hlg_oetf(np.clip(rgb * scale[..., None], 0, 1))


def log_composite_alpha(code: np.ndarray, alpha: np.ndarray, ref_nits: float = REF_BG_NITS,
                        white_nits: float = GRAPHICS_WHITE_NITS) -> np.ndarray:
    """Alpha for a composite in DaVinci Intermediate that matches a display-gamma composite.

    ``code``: the overlay's Rec.709 RGB (..., 3), 0..1; ``alpha``: straight alpha (...).
    Design (Remotion, SDR): out_code = (1 - a) bg_code + a ov_code, in gamma 2.4. Resolve:
    out_DI = (1 - a') DI(bg) + a' DI(ov). Solved for a' with bg = ``ref_nits`` (neutral),
    on luminance; where overlay and background are about equally bright, a' = a.
    """
    a = np.clip(np.asarray(alpha, dtype=np.float64), 0, 1)
    ov_nits = white_nits * (np.clip(np.asarray(code, dtype=np.float64), 0, 1) ** SDR_GAMMA @ LUMA_709)
    bg_code = (ref_nits / white_nits) ** (1 / SDR_GAMMA)
    ov_code = (ov_nits / white_nits) ** (1 / SDR_GAMMA)
    design_nits = white_nits * ((1 - a) * bg_code + a * ov_code) ** SDR_GAMMA
    d_bg = di_encode(ref_nits / WORKING_NITS_PER_UNIT)
    d_ov = di_encode(ov_nits / WORKING_NITS_PER_UNIT)
    d_t = di_encode(design_nits / WORKING_NITS_PER_UNIT)
    den = d_bg - d_ov
    with np.errstate(divide="ignore", invalid="ignore"):
        out = np.where(np.abs(den) > 1e-3, (d_bg - d_t) / den, a)
    return np.clip(out, 0, 1)


# -- overlay files ---------------------------------------------------------------------------
def _probe_size(path: Path) -> tuple[int, int, str, int | None]:
    out = subprocess.run([FFPROBE, "-v", "error", "-select_streams", "v:0", "-count_packets", "-show_entries",
                          "stream=width,height,r_frame_rate,nb_read_packets", "-of", "csv=p=0", str(path)],
                         capture_output=True, text=True, check=True).stdout.strip().split(",")
    w, h, rate = int(out[0]), int(out[1]), out[2]
    n = int(out[3]) if len(out) > 3 and out[3].isdigit() else None
    return w, h, rate, n


def convert_overlay(src: Path, dst: Path, white_nits: float = GRAPHICS_WHITE_NITS, log_alpha: bool = True) -> dict:
    """SDR ProRes 4444 overlay -> HLG ProRes 4444 (alpha kept), tagged bt2020 / arib-std-b67.

    Only pixels with alpha > 0 are converted (colour under alpha 0 is irrelevant), and
    identical frames (holds) reuse the previous result, so a 2160x3840 overlay takes seconds.
    """
    w, h, rate, frames = _probe_size(src)
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.stem + ".part" + dst.suffix)
    dec = subprocess.Popen([FFMPEG, "-v", "error", "-i", str(src), "-vf",
                            "scale=in_color_matrix=bt709:in_range=tv,format=rgba64le", "-f", "rawvideo", "-"],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen([FFMPEG, "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgba64le", "-s", f"{w}x{h}",
                            "-r", rate, "-i", "-", "-vf",
                            "scale=out_color_matrix=bt2020nc:out_range=tv,format=yuva444p10le",
                            "-c:v", "prores_ks", "-profile:v", "4", "-alpha_bits", "16",
                            "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
                            "-color_range", "tv", "-movflags", "+write_colr", str(tmp)], stdin=subprocess.PIPE)
    size = w * h * 4 * 2
    n, last_in, last_out = 0, None, None
    assert dec.stdout is not None and enc.stdin is not None
    while True:
        buf = dec.stdout.read(size)
        if len(buf) < size:
            break
        if buf != last_in:
            px = np.frombuffer(buf, np.uint16).reshape(h, w, 4)
            out = px.copy()
            m = px[..., 3] > 0
            sel = px[m].astype(np.float64) / 65535.0
            rgb = sel[:, :3]
            out[m, :3] = np.round(sdr_to_hlg(rgb, white_nits) * 65535.0).astype(np.uint16)
            if log_alpha:
                out[m, 3] = np.round(log_composite_alpha(rgb, sel[:, 3], white_nits=white_nits) * 65535.0
                                     ).astype(np.uint16)
            out[~m, :3] = 0
            last_in, last_out = buf, out.tobytes()
        enc.stdin.write(last_out)
        n += 1
    enc.stdin.close()
    if dec.wait() or enc.wait():
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"ffmpeg failed converting {src} -> {dst}")
    tmp.replace(dst)
    if frames is not None and n != frames:
        raise RuntimeError(f"{src}: converted {n} frames, the file has {frames}")
    return {"src": str(src), "dst": str(dst), "frames": n, "size": f"{w}x{h}", "white_nits": white_nits,
            "log_alpha": log_alpha, "ref_bg_nits": REF_BG_NITS if log_alpha else None}


CONVERSION_VERSION = 2  # bump when the conversion changes; cached files are then remade


def hlg_overlay(src: Path, white_nits: float = GRAPHICS_WHITE_NITS) -> tuple[Path, dict | None]:
    """``overlays/hlg/<name>.mov`` for ``overlays/<name>.mov``; remade unless its sidecar
    ``<name>.json`` records the same source (size, mtime) and conversion settings."""
    dst = src.parent / "hlg" / src.name
    side = dst.with_suffix(".json")
    st = src.stat()
    key = {"version": CONVERSION_VERSION, "src_size": st.st_size, "src_mtime": st.st_mtime,
           "white_nits": white_nits, "ref_bg_nits": REF_BG_NITS}
    try:
        if dst.exists() and json.loads(side.read_text()) == key:
            return dst, None
    except (OSError, ValueError):
        pass
    info = convert_overlay(src, dst, white_nits)
    side.write_text(json.dumps(key))
    return dst, info


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.hdr", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("overlay", help="convert an SDR ProRes 4444 overlay to HLG at graphics white")
    o.add_argument("src")
    o.add_argument("dst")
    o.add_argument("--white-nits", type=float, default=GRAPHICS_WHITE_NITS)
    o.add_argument("--keep-alpha", action="store_true", help="copy alpha unchanged (no log-composite correction)")
    args = ap.parse_args(argv)
    info = convert_overlay(Path(args.src).expanduser(), Path(args.dst).expanduser(), args.white_nits,
                           log_alpha=not args.keep_alpha)
    print(info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
