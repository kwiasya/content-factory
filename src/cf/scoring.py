"""Score 1 s bins and choose candidate segments for a Shot log.

Pure functions over per-second arrays (tested in tests/test_shotlog.py):
  bin_flags        why a bin is unusable (empty list = usable)
  components       aes / sharp / stability / exposure in 0..1 per bin
  quality          0.35*aes + 0.25*sharp + 0.2*stability + 0.2*exposure,
                   aes weight redistributed when aes is None
  select_windows   slide 2-5 s windows of usable bins, greedy top-N non-overlapping
  reject_runs      merge consecutive unusable bins into rejects with `why`
  motion_tag, light_tag, pace_label
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Sequence

import numpy as np

WEIGHTS = {"aes": 0.35, "sharp": 0.25, "stability": 0.2, "exposure": 0.2}

MOTION_VOCAB = ("locked", "push_in", "pull_back", "drift", "pan_left", "pan_right", "forward_walk", "handheld")
LIGHT_VOCAB = ("golden_hour", "overcast", "blue_hour", "night", "interior")


@dataclass(frozen=True)
class Params:
    shake_px: float = 6.0          # usable needs shake_px <= this (px @1080 short side)
    blur_worst_pct: float = 80.0   # bins at/above this clip percentile of blur ...
    blur_rel: float = 1.10         # ... and above this x clip median are "worst 20%"
    blur_good: float = 3.0         # blurdetect value mapped to sharp = 1
    blur_bad: float = 8.0          # blurdetect value mapped to sharp = 0
    clip_hi_pct: float = 2.0       # usable needs clip_hi_pct <= this
    scd_spike: float = 10.0        # scdet score treated as a hard change / glitch
    luma_target: float = 0.45
    min_len: int = 2
    max_len: int = 5
    top_n: int = 3
    len_bonus: float = 0.01        # per extra second over min_len
    consistency_bonus: float = 0.05

    def as_dict(self) -> dict:
        return asdict(self)


DEFAULT = Params()


def _clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, x))


def _num(v, default=0.0) -> float:
    return default if v is None or (isinstance(v, float) and math.isnan(v)) else float(v)


# ----------------------------------------------------------------------------
# Per-bin usability and components


def blur_bad_mask(blur: Sequence[float | None], p: Params = DEFAULT) -> list[bool]:
    """Bins in the clip's worst (100 - blur_worst_pct)% of blur, and clearly worse than its median.

    The relative guard keeps a uniformly sharp clip from losing a fifth of its seconds.
    """
    vals = np.array([np.nan if v is None else v for v in blur], dtype=float)
    ok = ~np.isnan(vals)
    if ok.sum() < 3:
        return [False] * len(vals)
    cut = np.percentile(vals[ok], p.blur_worst_pct)
    med = np.median(vals[ok])
    return [bool(ok[i] and vals[i] >= cut and vals[i] > p.blur_rel * med) for i in range(len(vals))]


def bin_flags(ps: dict, p: Params = DEFAULT) -> list[list[str]]:
    n = len(ps["luma_mean"])
    blur_bad = blur_bad_mask(ps["blur"], p)
    out = []
    for i in range(n):
        why = []
        shake = ps["shake_px"][i]
        if shake is not None and shake > p.shake_px:
            why.append(f"shake_px>{p.shake_px:g}")
        if blur_bad[i]:
            why.append("blur_worst20%")
        if _num(ps["clip_hi_pct"][i]) > p.clip_hi_pct:
            why.append(f"clip_hi>{p.clip_hi_pct:g}%")
        if _num(ps["scd_score"][i]) > p.scd_spike:
            why.append("scd_spike")
        out.append(why)
    return out


def exposure_score(luma: float, clip_hi: float, clip_lo: float, p: Params = DEFAULT) -> float:
    level = _clamp(1 - abs(luma - p.luma_target) / 0.4)
    return level * (1 - _clamp(clip_hi / 5.0)) * (1 - 0.5 * _clamp(clip_lo / 20.0))


def components(ps: dict, p: Params = DEFAULT) -> list[dict]:
    n = len(ps["luma_mean"])
    aes = ps.get("aes") or [None] * n
    out = []
    for i in range(n):
        a = aes[i]
        blur = ps["blur"][i]
        shake = ps["shake_px"][i]
        out.append(
            {
                "aes": None if a is None else _clamp((a + 1) / 2),
                "sharp": None if blur is None else _clamp((p.blur_bad - blur) / (p.blur_bad - p.blur_good)),
                "stability": None if shake is None else _clamp(1 - shake / (2 * p.shake_px)),
                "exposure": exposure_score(_num(ps["luma_mean"][i], p.luma_target), _num(ps["clip_hi_pct"][i]), _num(ps["clip_lo_pct"][i]), p),
            }
        )
    return out


def quality(comp: dict) -> float:
    """Weighted sum; weights of missing (None) components are spread over the present ones."""
    present = {k: w for k, w in WEIGHTS.items() if comp.get(k) is not None}
    total = sum(present.values())
    if not total:
        return 0.0
    return sum(comp[k] * w for k, w in present.items()) / total


# ----------------------------------------------------------------------------
# Windows


def select_windows(
    q: Sequence[float],
    usable: Sequence[bool],
    types: Sequence[str | None] | None = None,
    p: Params = DEFAULT,
    duration_s: float | None = None,
) -> list[dict]:
    """Slide min_len..max_len s windows over usable bins; greedy pick top_n non-overlapping.

    Score = mean quality + len_bonus*(len-min_len) + consistency_bonus*(share of the
    dominant motion type). Returns [{in_s, out_s, score, mean_q, bins}] by score desc.
    """
    n = len(q)
    types = list(types) if types is not None else [None] * n
    cands = []
    for length in range(p.min_len, p.max_len + 1):
        for s in range(0, n - length + 1):
            if not all(usable[s : s + length]):
                continue
            mq = float(np.mean(q[s : s + length]))
            ts = [t for t in types[s : s + length] if t]
            consist = Counter(ts).most_common(1)[0][1] / length if ts else 0.0
            score = mq + p.len_bonus * (length - p.min_len) + p.consistency_bonus * consist
            cands.append((score, mq, s, length))
    cands.sort(key=lambda c: (-c[0], c[2], -c[3]))
    taken = [False] * n
    picked = []
    for score, mq, s, length in cands:
        if any(taken[s : s + length]):
            continue
        for i in range(s, s + length):
            taken[i] = True
        out_s = float(s + length)
        if duration_s is not None:
            out_s = min(out_s, round(duration_s, 3))
        picked.append({"in_s": float(s), "out_s": out_s, "score": round(score, 4), "mean_q": round(mq, 4), "bins": (s, s + length)})
        if len(picked) >= p.top_n:
            break
    return picked


def reject_runs(flags: Sequence[Sequence[str]], duration_s: float | None = None) -> list[dict]:
    runs = []
    i, n = 0, len(flags)
    while i < n:
        if not flags[i]:
            i += 1
            continue
        j = i
        why: list[str] = []
        while j < n and flags[j]:
            for w in flags[j]:
                if w not in why:
                    why.append(w)
            j += 1
        out_s = float(j) if duration_s is None else min(float(j), round(duration_s, 3))
        runs.append({"in_s": float(i), "out_s": out_s, "why": why})
        i = j
    return runs


# ----------------------------------------------------------------------------
# Tags


def pace_label(speed: float | None) -> str:
    if speed is None:
        return "unknown"
    if speed < 0.05:
        return "slow"
    if speed < 0.15:
        return "medium"
    return "fast"


def motion_tag(motions: Sequence[dict | None], shake: Sequence[float | None], p: Params = DEFAULT) -> str:
    """Segment motion tag from the per-second types (vocabulary MOTION_VOCAB)."""
    types = [m["type"] for m in motions if m]
    if not types:
        return "drift"
    dominant, count = Counter(types).most_common(1)[0]
    if count / len(types) < 0.5:
        dominant = "drift" if "handheld" not in types else "handheld"
    mean_shake = float(np.mean([s for s in shake if s is not None] or [0.0]))
    if dominant == "forward_walk":
        speeds = [m["speed"] for m in motions if m and m.get("speed") is not None]
        # a steady, slow forward move reads as a push-in
        if mean_shake < p.shake_px / 3 and speeds and float(np.median(speeds)) < 0.05:
            return "push_in"
    return dominant


def direction_word(m: dict | None) -> str:
    t = (m or {}).get("type")
    return {
        "pan_left": "left", "pan_right": "right", "forward_walk": "forward", "pull_back": "back",
        "locked": "static",
    }.get(t, "none")


def solar_elevation(when: datetime, lat: float, lon: float) -> float:
    """Approximate solar elevation in degrees (NOAA formulas, ~0.5 deg accuracy)."""
    utc = when.astimezone(timezone.utc)
    doy = utc.timetuple().tm_yday
    hour = utc.hour + utc.minute / 60 + utc.second / 3600
    g = 2 * math.pi / 365 * (doy - 1 + (hour - 12) / 24)
    eqtime = 229.18 * (0.000075 + 0.001868 * math.cos(g) - 0.032077 * math.sin(g) - 0.014615 * math.cos(2 * g) - 0.040849 * math.sin(2 * g))
    decl = (0.006918 - 0.399912 * math.cos(g) + 0.070257 * math.sin(g) - 0.006758 * math.cos(2 * g)
            + 0.000907 * math.sin(2 * g) - 0.002697 * math.cos(3 * g) + 0.00148 * math.sin(3 * g))
    tst = hour * 60 + eqtime + 4 * lon
    ha = math.radians(tst / 4 - 180)
    la = math.radians(lat)
    cz = math.sin(la) * math.sin(decl) + math.cos(la) * math.cos(decl) * math.cos(ha)
    return 90 - math.degrees(math.acos(max(-1.0, min(1.0, cz))))


def guess_location(created: datetime, gps: dict | None, default_lat: float = 50.0) -> tuple[float, float, bool]:
    """(lat, lon, from_gps). Without GPS: longitude from the UTC offset (minus 1 h of
    northern summer time for Apr-Oct), latitude default_lat."""
    if gps and gps.get("lat") is not None and gps.get("lon") is not None:
        return float(gps["lat"]), float(gps["lon"]), True
    off = created.utcoffset()
    hours = off.total_seconds() / 3600 if off is not None else 0.0
    if 4 <= created.month <= 10 and hours >= 1:
        hours -= 1
    return default_lat, hours * 15.0, False


def light_tag(
    luma: float,
    sat: float,
    warmth: float,
    contrast: float,
    created: str | None,
    gps: dict | None = None,
) -> dict:
    """Heuristic light class. Returns {tag (LIGHT_VOCAB or None), confidence, basis, sun_elev}.

    tag None means none of the vocabulary fits (e.g. plain daylight).
    """
    elev = None
    from_gps = False
    if created:
        try:
            dt = datetime.fromisoformat(created)
            if dt.tzinfo is not None:
                lat, lon, from_gps = guess_location(dt, gps)
                elev = solar_elevation(dt, lat, lon)
        except ValueError:
            elev = None
    loc_conf = 0.0 if elev is None else (0.1 if from_gps else 0.0)

    def res(tag, conf, basis):
        return {"tag": tag, "confidence": round(_clamp(conf + (loc_conf if elev is not None else 0)), 2), "basis": basis,
                "sun_elev": None if elev is None else round(elev, 1)}

    if elev is not None:
        if elev < -6:
            if luma > 0.35:
                return res("interior", 0.35, f"sun {elev:.0f} deg below horizon but frame is bright")
            return res("night", 0.7, f"sun {elev:.0f} deg")
        if elev < 0:
            if warmth > 0.1:
                return res("golden_hour", 0.45, f"sun {elev:.1f} deg, warm cast {warmth:.2f}")
            return res("blue_hour", 0.6, f"sun {elev:.1f} deg")
        if elev < 12:
            if sat < 0.1 and contrast < 0.35:
                return res("overcast", 0.45, f"sun {elev:.1f} deg but flat, desaturated frame")
            return res("golden_hour", 0.55 + (0.1 if warmth > 0.1 else 0.0), f"sun {elev:.1f} deg, warmth {warmth:.2f}")
        # daytime
        if luma < 0.22 and sat < 0.12:
            return res("interior", 0.3, f"daytime (sun {elev:.0f} deg) but dark, desaturated frame")
        if sat < 0.12 and contrast < 0.4:
            return res("overcast", 0.45, f"daytime, low saturation {sat:.2f} and contrast {contrast:.2f}")
        return res(None, 0.5, f"daylight (sun {elev:.0f} deg); not in light vocabulary")
    # pixels only
    if luma < 0.15:
        return res("night", 0.35, f"no time; very dark frame (luma {luma:.2f})")
    if warmth > 0.15 and sat > 0.2:
        return res("golden_hour", 0.25, f"no time; warm saturated frame")
    if sat < 0.1 and contrast < 0.35:
        return res("overcast", 0.3, f"no time; flat desaturated frame")
    return res(None, 0.2, "no time; no light class fits")
