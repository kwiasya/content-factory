"""Apple Vision aesthetics and faces via the Swift CLI tools/vision-score (1 fps).

If the binary is missing or fails, every per-second value is None and a warning
is logged; cf.shotlog then redistributes the aesthetics weight.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path

import numpy as np

from cf.metrics.common import ProxyInfo, bin_reduce, n_bins, rounded

log = logging.getLogger("cf.vision")

REPO = Path(__file__).resolve().parents[3]
DEFAULT_BIN = REPO / "tools" / "vision-score" / ".build" / "release" / "vision-score"


def binary() -> Path:
    return Path(os.environ.get("CF_VISION_SCORE", DEFAULT_BIN))


def summarize(frames: list[dict], nbins: int) -> dict:
    """Bin the CLI's per-frame records. Pure; tested without the binary."""
    def col(key):
        t, v = [], []
        for f in frames:
            if f.get(key) is None or f.get("t") is None:
                continue
            t.append(float(f["t"]))
            v.append(float(f[key]))
        return t, v

    t_a, aes = col("aesthetic")
    t_u, util = col("is_utility")
    t_f, faces = col("faces")
    t_fh, face_h = col("max_face_h")
    t_h, humans = col("humans")
    t_hh, human_h = col("max_human_h")
    return {
        "aes": rounded(bin_reduce(t_a, aes, nbins), 3),
        "is_utility": [None if v is None else bool(v >= 0.5) for v in bin_reduce(t_u, util, nbins)],
        "faces": [None if v is None else int(v) for v in bin_reduce(t_f, faces, nbins, np.max)],
        "max_face_h": rounded(bin_reduce(t_fh, face_h, nbins, np.max), 3),
        "humans": [None if v is None else int(v) for v in bin_reduce(t_h, humans, nbins, np.max)],
        "max_human_h": rounded(bin_reduce(t_hh, human_h, nbins, np.max), 3),
    }


def analyze(info: ProxyInfo, fps: float = 1.0) -> dict:
    nb = n_bins(info.duration_s)
    exe = binary()
    empty = {k: [None] * nb for k in ("aes", "is_utility", "faces", "max_face_h", "humans", "max_human_h")}
    if not exe.exists():
        log.warning("vision-score not built (%s); aes will be null", exe)
        return empty | {"_available": False, "_error": "binary missing"}
    # The CLI writes JSON to stdout when --json is omitted ("--json -" creates a file named "-").
    proc = subprocess.run([str(exe), str(info.path), "--fps", str(fps)], capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not proc.stdout.strip():
        log.warning("vision-score failed (%s): %s", proc.returncode, proc.stderr.strip()[-500:])
        return empty | {"_available": False, "_error": proc.stderr.strip()[-300:] or f"exit {proc.returncode}"}
    try:
        frames = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        log.warning("vision-score output not JSON: %s", exc)
        return empty | {"_available": False, "_error": "bad json"}
    out = summarize(frames, nb)
    out["_available"] = True
    out["_frames"] = len(frames)
    return out


def landmark_frames(proxy: Path, fps: float = 5.0) -> tuple[list[dict] | None, str | None]:
    """Per-frame faces and mouth_open (`--landmarks --faces-only`). Returns (frames, error)."""
    exe = binary()
    if not exe.exists():
        return None, "vision-score binary missing"
    proc = subprocess.run([str(exe), str(proxy), "--fps", str(fps), "--landmarks", "--faces-only"],
                          capture_output=True, text=True, timeout=600)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None, proc.stderr.strip()[-300:] or f"exit {proc.returncode}"
    try:
        frames = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None, "bad json"
    if frames and "mouth_open" not in frames[0]:
        return None, "vision-score has no --landmarks (rebuild tools/vision-score)"
    return frames, None


if __name__ == "__main__":
    import sys

    from cf.metrics.common import probe_proxy

    logging.basicConfig(level=logging.INFO)
    print(json.dumps(analyze(probe_proxy(Path(sys.argv[1])))))
