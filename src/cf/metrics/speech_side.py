"""Which side of the camera a speech segment comes from: `near` (the author filming) or `far` (on camera).

The author talks from behind the camera most of the time ("closer", "you're out of
frame"); music covers that, so it is allowed. Only the person ON camera talking is a
reject (`speech_on_camera`). Two cheap cues, combined per segment:

1. Loudness (raw audio, the 16 kHz mono WAV Whisper reads). `level_dbfs` is the 90th
   percentile of 50 ms frame levels inside the segment (robust to pauses between
   words); `rms_dbfs` is the plain RMS over the segment, kept for the record.
   The operator's voice is the loudest on the Walk, so the level is compared with
   the Walk reference (median of the three loudest segment levels; normalised per
   Walk, not per clip) and with the clip's noise floor (10th percentile of frame
   levels). Quiet relative to the Walk and close to the floor -> far.
2. Face and mouth (proxy, tools/vision-score --landmarks --faces-only at 5 fps).
   A big face (max_face_h > FACE_BIG) during the segment raises `far`; no face at
   all lowers it (nobody can be seen talking). Mouth openness = inner-lip gap /
   face-box height of the largest face; its spread over the segment is the
   strongest on-camera cue, but only trusted when the face is big enough for the
   landmarks to be stable (weight ramps from FACE_TRUST_LO to FACE_TRUST_HI).

Each cue is evidence in [-1, 1] (+ = far); missing evidence is 0. p_far is a
logistic of the weighted sum. `side_confidence` = |2 p_far - 1| (0 = coin flip,
1 = certain), so "far with confidence >= 0.5" means p_far >= 0.75.

Not used: reverb / dryness (direct-to-reverberant ratio needs more than a WAV and a
guess); speaker identity.
"""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np

FRAME_S = 0.05
FACE_FPS = 5.0
FACE_BIG = 0.12            # face height (share of frame height) that counts as "on camera, close"
FACE_SMALL = 0.03          # below this a detected face is too small to matter
FACE_TRUST_LO = 0.05       # mouth landmarks ignored below this face height ...
FACE_TRUST_HI = 0.12       # ... and fully trusted above it
MIN_MOUTH_FRAMES = 2
MIN_CONF = 0.5             # far segments at/above this confidence are speech_on_camera
REF_TOP_N = 3

# evidence scales (dB / mouth spread); tuned on the Potsdam Walk, see docs/research/shotlog-run.md
REL_MID_DB = -16.0         # level this far under the Walk reference is neutral
REL_SPAN_DB = 9.0          # +-1 evidence at REL_MID_DB -+ REL_SPAN_DB
SNR_MID_DB = 14.0          # level over the clip noise floor that is neutral
SNR_SPAN_DB = 8.0
MOUTH_MID = 0.012          # std of mouth_open that is neutral
MOUTH_SPAN = 0.008
W_REL, W_SNR, W_FACE, W_MOUTH = 0.6, 0.4, 0.6, 1.2
GAIN = 2.0


def _clamp(x: float, lo: float = -1.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


# ----------------------------------------------------------------------------
# Audio levels


def frame_db(samples: np.ndarray, sr: int, frame_s: float = FRAME_S) -> np.ndarray:
    """dBFS per frame_s frame (float samples in -1..1)."""
    hop = max(1, int(round(sr * frame_s)))
    n = len(samples) // hop
    if n == 0:
        return np.array([10 * math.log10(float(np.mean(samples ** 2)) + 1e-12)]) if len(samples) else np.array([-120.0])
    fr = samples[: n * hop].reshape(n, hop).astype(np.float64)
    return 10 * np.log10(np.mean(fr ** 2, axis=1) + 1e-12)


def noise_floor_db(db: np.ndarray) -> float:
    return round(float(np.percentile(db, 10)), 1)


def segment_levels(samples: np.ndarray, sr: int, start: float, end: float, db: np.ndarray | None = None,
                   frame_s: float = FRAME_S) -> tuple[float, float]:
    """(rms_dbfs over [start, end], level_dbfs = p90 of frame levels inside it)."""
    a = max(0, int(start * sr))
    b = max(a + 1, int(end * sr))
    seg = samples[a:b].astype(np.float64)
    rms = 10 * math.log10(float(np.mean(seg ** 2)) + 1e-12) if len(seg) else -120.0
    db = frame_db(samples, sr, frame_s) if db is None else db
    fa = min(int(start / frame_s), len(db) - 1)
    fb = max(fa + 1, int(math.ceil(end / frame_s)))
    level = float(np.percentile(db[fa:fb], 90))
    return round(rms, 1), round(level, 1)


def add_levels(segments: list[dict], samples: np.ndarray, sr: int) -> float:
    """Write rms_dbfs and level_dbfs into each segment (in place); returns the clip noise floor."""
    db = frame_db(samples, sr)
    for s in segments:
        s["rms_dbfs"], s["level_dbfs"] = segment_levels(samples, sr, s["start"], s["end"], db)
    return noise_floor_db(db)


def walk_reference(levels: Iterable[float | None], top_n: int = REF_TOP_N) -> float | None:
    """Median of the top_n loudest segment levels on the Walk (the operator's voice)."""
    lv = sorted((float(x) for x in levels if x is not None), reverse=True)
    if not lv:
        return None
    return round(float(np.median(lv[:top_n])), 1)


# ----------------------------------------------------------------------------
# Face and mouth


def face_stats(frames: Sequence[dict], start: float, end: float, margin: float = 0.1) -> dict:
    """Face size and mouth movement over the frames inside [start - margin, end + margin]."""
    inside = [f for f in frames if f.get("t") is not None and start - margin <= f["t"] <= end + margin]
    face_h = [float(f.get("max_face_h") or 0.0) for f in inside]
    mouth = [float(f["mouth_open"]) for f in inside if f.get("mouth_open") is not None]
    with_face = [h for h in face_h if h > 0]
    return {
        "face_frames": f"{len(with_face)}/{len(inside)}",
        "max_face_h": round(max(face_h), 3) if face_h else None,
        "median_face_h": round(float(np.median(with_face)), 3) if with_face else 0.0 if inside else None,
        "mouth_open_var": round(float(np.var(mouth)), 6) if len(mouth) >= MIN_MOUTH_FRAMES else None,
        "mouth_open_std": round(float(np.std(mouth)), 4) if len(mouth) >= MIN_MOUTH_FRAMES else None,
    }


# ----------------------------------------------------------------------------
# Classification


def evidence(seg: dict, noise_floor: float | None, walk_ref: float | None) -> dict:
    """Per-cue evidence in [-1, 1] (+ = far / on camera); None where the cue is missing."""
    level = seg.get("level_dbfs")
    rel = None if level is None or walk_ref is None else level - walk_ref
    snr = None if level is None or noise_floor is None else level - noise_floor
    e_rel = None if rel is None else _clamp((REL_MID_DB - rel) / REL_SPAN_DB)
    e_snr = None if snr is None else _clamp((SNR_MID_DB - snr) / SNR_SPAN_DB)

    fh = seg.get("max_face_h")
    if fh is None:
        e_face = None
    elif fh < FACE_SMALL:
        e_face = -1.0  # nobody visible to be talking
    else:
        e_face = _clamp((fh - FACE_SMALL) / (FACE_BIG - FACE_SMALL), 0.0, 1.0)

    std = seg.get("mouth_open_std")
    med = seg.get("median_face_h") or 0.0
    trust = _clamp((med - FACE_TRUST_LO) / (FACE_TRUST_HI - FACE_TRUST_LO), 0.0, 1.0)
    e_mouth = None if std is None or trust == 0 else _clamp((std - MOUTH_MID) / MOUTH_SPAN)
    return {"rel_db": None if rel is None else round(rel, 1), "snr_db": None if snr is None else round(snr, 1),
            "e_rel": e_rel, "e_snr": e_snr, "e_face": e_face, "e_mouth": e_mouth, "mouth_trust": round(trust, 2)}


def p_far(ev: dict) -> float:
    def w(key, weight, scale=1.0):
        v = ev.get(key)
        return 0.0 if v is None else weight * scale * v

    score = w("e_rel", W_REL) + w("e_snr", W_SNR) + w("e_face", W_FACE) + w("e_mouth", W_MOUTH, ev.get("mouth_trust", 1.0))
    return 1 / (1 + math.exp(-GAIN * score))


def classify(seg: dict, noise_floor: float | None, walk_ref: float | None) -> dict:
    """{side, side_confidence, p_far, rel_db, snr_db} for one segment with levels and face stats."""
    ev = evidence(seg, noise_floor, walk_ref)
    p = p_far(ev)
    return {
        "side": "far" if p >= 0.5 else "near",
        "side_confidence": round(abs(2 * p - 1), 2),
        "p_far": round(p, 2),
        "rel_db": ev["rel_db"],
        "snr_db": ev["snr_db"],
    }


def is_on_camera(seg: dict, min_conf: float = MIN_CONF) -> bool:
    return seg.get("side") == "far" and (seg.get("side_confidence") or 0.0) >= min_conf
