"""Exposure, blur and hard-cut metrics from one ffmpeg pass over a proxy.

One decode, split three ways:
  A. full frame rate: signalstats + scdet  -> metadata=print to a temp file
  B. fps=10: blurdetect (the expensive one; 10 fps is plenty per second)
  C. fps=5: the Y plane at half size piped as raw gray -> % pixels clipped

Timing uses each frame's pts_time (sources can be VFR), binned into 1 s bins.
"""

from __future__ import annotations

import subprocess
import tempfile
from pathlib import Path

import numpy as np

from cf.metrics.common import ProxyInfo, bin_reduce, ffmpeg_bin, fill_gaps, n_bins, rounded

BLUR_FPS = 10
CLIP_FPS = 5

# Clip thresholds on 8-bit Y. Limited ("tv") range: 233 is ~99% of 16..235,
# 18 is ~1%; full range uses 250 / 5 (research section 3).
CLIP_THRESHOLDS = {"tv": (233, 18), "pc": (250, 5)}

FIELDS = {
    "lavfi.signalstats.YAVG": "yavg",
    "lavfi.signalstats.YLOW": "ylow",
    "lavfi.signalstats.YHIGH": "yhigh",
    "lavfi.signalstats.YMIN": "ymin",
    "lavfi.signalstats.YMAX": "ymax",
    "lavfi.signalstats.SATAVG": "sat",
    "lavfi.signalstats.UAVG": "uavg",
    "lavfi.signalstats.VAVG": "vavg",
    "lavfi.blur": "blur",
    "lavfi.scd.score": "scd",
}


def parse_metadata(text: str) -> tuple[list[float], dict[str, list[float]]]:
    """Parse `metadata=print` output into (pts_times, {field: values}) aligned per frame.

    Fields missing for a frame are NaN.
    """
    times: list[float] = []
    cols: dict[str, list[float]] = {}
    current: dict[str, float] | None = None

    def flush():
        if current is None:
            return
        for name in set(cols) | set(current):
            cols.setdefault(name, [float("nan")] * (len(times) - 1)).append(current.get(name, float("nan")))

    for line in text.splitlines():
        if line.startswith("frame:"):
            flush()
            pts_time = float("nan")
            for tok in line.split():
                if tok.startswith("pts_time:"):
                    try:
                        pts_time = float(tok.split(":", 1)[1])
                    except ValueError:
                        pass
            times.append(pts_time)
            current = {}
        elif "=" in line and current is not None:
            key, _, val = line.partition("=")
            name = FIELDS.get(key.strip())
            if name:
                try:
                    current[name] = float(val)
                except ValueError:
                    current[name] = float("nan")
    flush()
    for name, vals in cols.items():
        if len(vals) < len(times):
            vals.extend([float("nan")] * (len(times) - len(vals)))
    return times, cols


def luma_norm(y: np.ndarray, color_range: str | None) -> np.ndarray:
    if color_range == "pc":
        return np.clip(y / 255.0, 0, 1)
    return np.clip((y - 16.0) / 219.0, 0, 1)


def clip_pcts(frame: np.ndarray, color_range: str | None) -> tuple[float, float]:
    hi, lo = CLIP_THRESHOLDS["pc" if color_range == "pc" else "tv"]
    n = frame.size
    return 100.0 * np.count_nonzero(frame >= hi) / n, 100.0 * np.count_nonzero(frame <= lo) / n


def analyze(info: ProxyInfo) -> dict:
    """Per-second arrays: luma_mean, clip_hi_pct, clip_lo_pct, blur, scd_score, sat, warmth, contrast.

    luma_mean 0..1 of the nominal range; clip_* in % of pixels; blur is blurdetect's
    edge-width metric (higher = blurrier); scd_score is the max scdet score in the
    second; sat = SATAVG/128; warmth = (VAVG-UAVG)/128 (>0 red/orange cast);
    contrast = (YHIGH-YLOW) 10th..90th percentile spread, 0..1.
    """
    nb = n_bins(info.duration_s)
    w2, h2 = (info.width // 4) * 2, (info.height // 4) * 2
    with tempfile.TemporaryDirectory(prefix="cf-ffstats-") as tmp:
        meta_a, meta_b, err = Path(tmp, "a.txt"), Path(tmp, "b.txt"), Path(tmp, "err.txt")
        graph = (
            "[0:v]split=3[a][b][c];"
            f"[a]signalstats,scdet,metadata=print:file='{meta_a}'[oa];"
            f"[b]fps={BLUR_FPS},blurdetect,metadata=print:file='{meta_b}'[ob];"
            f"[c]fps={CLIP_FPS},extractplanes=y,scale={w2}:{h2}:flags=neighbor,format=gray[oc]"
        )
        cmd = [
            ffmpeg_bin(), "-hide_banner", "-nostdin", "-nostats", "-loglevel", "error", "-threads", "2",
            "-i", str(info.path), "-filter_complex", graph,
            "-map", "[oa]", "-f", "null", "-",
            "-map", "[ob]", "-f", "null", "-",
            "-map", "[oc]", "-f", "rawvideo", "-pix_fmt", "gray", "pipe:1",
        ]
        frame_bytes = w2 * h2
        clip_t: list[float] = []
        clip_hi: list[float] = []
        clip_lo: list[float] = []
        with err.open("wb") as errf:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=errf)
            assert proc.stdout is not None
            i = 0
            while True:
                buf = proc.stdout.read(frame_bytes)
                if len(buf) < frame_bytes:
                    break
                frame = np.frombuffer(buf, dtype=np.uint8)
                hi, lo = clip_pcts(frame, info.color_range)
                clip_t.append(i / CLIP_FPS)
                clip_hi.append(hi)
                clip_lo.append(lo)
                i += 1
            rc = proc.wait()
        if rc != 0:
            raise RuntimeError(f"ffmpeg stats failed ({rc}): {err.read_text()[-2000:]}")
        ta, ca = parse_metadata(meta_a.read_text())
        tb, cb = parse_metadata(meta_b.read_text())

    ya = np.asarray(ca.get("yavg", []), dtype=float)
    luma = bin_reduce(ta, luma_norm(ya, info.color_range), nb)
    sat = bin_reduce(ta, np.asarray(ca.get("sat", []), dtype=float) / 128.0, nb)
    warm = bin_reduce(
        ta, (np.asarray(ca.get("vavg", []), dtype=float) - np.asarray(ca.get("uavg", []), dtype=float)) / 128.0, nb
    )
    span = 255.0 if info.color_range == "pc" else 219.0
    contrast = bin_reduce(
        ta, (np.asarray(ca.get("yhigh", []), dtype=float) - np.asarray(ca.get("ylow", []), dtype=float)) / span, nb
    )
    scd = bin_reduce(ta, ca.get("scd", []), nb, np.max)
    blur = bin_reduce(tb, cb.get("blur", []), nb)
    return {
        "luma_mean": rounded(fill_gaps(luma)),
        "clip_hi_pct": rounded(fill_gaps(bin_reduce(clip_t, clip_hi, nb)), 2),
        "clip_lo_pct": rounded(fill_gaps(bin_reduce(clip_t, clip_lo, nb)), 2),
        "blur": rounded(fill_gaps(blur)),
        "scd_score": rounded(fill_gaps(scd), 2),
        "sat": rounded(fill_gaps(sat)),
        "warmth": rounded(fill_gaps(warm)),
        "contrast": rounded(fill_gaps(contrast)),
        "_frames": len(ta),
    }


if __name__ == "__main__":
    import json
    import sys

    from cf.metrics.common import probe_proxy

    print(json.dumps(analyze(probe_proxy(Path(sys.argv[1])))))
