"""Build the Look as a 3D LUT (.cube) from a JSON look spec.

    python -m cf.look build <spec.json> -o <file.cube> [--size 33]
    python -m cf.look preview <spec.json> <still.png> -o <out.png>
    python -m cf.look measure <still.png> [<still.png> ...] [--skin x,y,w,h]
    python -m cf.look grid <out.png> --rows s01,s05 --col "no look=<dir>" --col "warm=<dir>" ...

The LUT works in the timeline space of a cf project (docs/resolve-rules.md "Exact
strings"): DaVinci Wide Gamut / DaVinci Intermediate in and out. Each lattice point is
decoded from DaVinci Intermediate to linear, converted from DWG to linear Rec.709
primaries (negative values allowed, nothing is clipped), graded, converted back and
re-encoded. In a cf project the LUT sits in the post-clip graph of the ``cf-look`` color
group, after each clip's node-1 HLG normalization (cf.build, docs/research/look-experiment.md).

The grade, in order, on linear light (``apply_look``):

1. exposure trim (stops);
2. filmic contrast in log2 around a pivot (0.18): slope ``amount`` at the pivot that
   relaxes back to 1 over ``toe_stops`` below and ``shoulder_stops`` above, so shadows get
   deeper by at most ``(amount-1)*toe_stops`` stops and never clip to zero. ``per_channel``
   blends a hue-preserving (luminance ratio) curve with a per-channel one;
3. saturation around luminance: base gain, vibrance (more gain for low-saturation
   colors), roll-off toward ``highlight_floor`` x gain in highlights and toward 1 in the
   noise floor, a skin band (hue window) that keeps only ``1 - protect`` of the change, and
   optional hue bands that scale the gain (e.g. calmer yellow-green foliage);
4. split toning: multiplicative (log-offset) push toward a hue in the highlights and
   another in the shadows, luminance-neutral;
5. highlight shoulder (off unless ``shoulder.compress`` > 0): above ``knee`` stops over the
   pivot the log2 slope of a norm eases from 1 down to ``1 - compress`` over ``width`` stops,
   and RGB is scaled by the norm's ratio, so hue and saturation are kept. The norm blends
   luminance and max(RGB) (``max_weight``); max(RGB) also pulls back saturated projection
   colours whose one channel would otherwise reach the output DRT's ceiling;
6. black lift ("milk"): ``lift`` linear added at black, mid grey kept;
7. gamut guard: colors pushed outside DWG are desaturated toward their luminance, then
   the result is re-encoded and clamped to the LUT range.

``preview`` applies the same grade to an 8-bit Rec.709 still as an approximation: it
decodes gamma 2.4 to display light and treats that as linear. The real judgement is a
Resolve still, because Resolve applies the LUT before its output tone map.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

# -- DaVinci Intermediate (Blackmagic "DaVinci Wide Gamut Intermediate" white paper) -----
DI_A = 0.0075
DI_B = 7.0
DI_C = 0.07329248
DI_M = 10.44426855
DI_LIN_CUT = 0.00262409
DI_LOG_CUT = 0.02740668


def di_decode(x: np.ndarray) -> np.ndarray:
    """DaVinci Intermediate code value -> scene linear."""
    x = np.asarray(x, dtype=np.float64)
    return np.where(x <= DI_LOG_CUT, x / DI_M, np.exp2(x / DI_C - DI_B) - DI_A)


def di_encode(lin: np.ndarray) -> np.ndarray:
    """Scene linear -> DaVinci Intermediate code value."""
    lin = np.asarray(lin, dtype=np.float64)
    safe = np.maximum(lin + DI_A, 1e-12)
    return np.where(lin <= DI_LIN_CUT, lin * DI_M, (np.log2(safe) + DI_B) * DI_C)


# -- primaries -------------------------------------------------------------------------------
def rgb_to_xyz(primaries: tuple[tuple[float, float], ...], white: tuple[float, float]) -> np.ndarray:
    """3x3 RGB->XYZ matrix from xy chromaticities (SMPTE RP 177)."""
    def xyz(xy: tuple[float, float]) -> np.ndarray:
        x, y = xy
        return np.array([x / y, 1.0, (1 - x - y) / y])
    p = np.stack([xyz(c) for c in primaries], axis=1)
    s = np.linalg.solve(p, xyz(white))
    return p * s


D65 = (0.3127, 0.3290)
DWG_TO_XYZ = rgb_to_xyz(((0.8000, 0.3130), (0.1682, 0.9877), (0.0790, -0.1155)), D65)
REC709_TO_XYZ = rgb_to_xyz(((0.640, 0.330), (0.300, 0.600), (0.150, 0.060)), D65)
DWG_TO_709 = np.linalg.solve(REC709_TO_XYZ, DWG_TO_XYZ)
REC709_TO_DWG = np.linalg.inv(DWG_TO_709)
LUMA_709 = REC709_TO_XYZ[1]          # 0.2126 0.7152 0.0722
LUMA_DWG = DWG_TO_XYZ[1]


# -- spec ------------------------------------------------------------------------------------
@dataclass
class Contrast:
    amount: float = 1.0          # slope in log2 at the pivot (1 = no change)
    pivot: float = 0.18          # linear mid grey
    toe_stops: float = 2.5       # how far below the pivot the extra slope relaxes
    shoulder_stops: float = 3.0  # how far above
    per_channel: float = 0.0     # 0 = hue-preserving (luminance ratio), 1 = per channel


@dataclass
class Skin:
    hue: float = 22.0      # HSV hue (degrees) of the skin band centre
    width: float = 16.0    # half width of the band (full effect inside, cosine falloff to 2x)
    protect: float = 0.0   # 0..1: share of the saturation change taken away from skin


@dataclass
class HueBand:
    hue: float = 75.0      # HSV hue (degrees) of the band centre
    width: float = 20.0    # half width (full effect inside, cosine falloff to 2x)
    gain: float = 1.0      # multiplier on the saturation gain inside the band


@dataclass
class Saturation:
    amount: float = 1.0
    vibrance: float = 0.0          # extra gain at zero saturation, fading to 0 at full saturation
    highlight_start: float = 1.5   # stops over the pivot where the highlight roll-off begins
    highlight_end: float = 4.5     # stops over the pivot where it is complete
    highlight_floor: float = 1.0   # multiplier on the gain in full highlights (< 1 desaturates)
    shadow_start: float = -4.0     # stops under the pivot where the gain starts to fade to 1
    shadow_end: float = -7.0
    skin: Skin = field(default_factory=Skin)
    bands: list[HueBand] = field(default_factory=list)  # e.g. tame yellow-green foliage


@dataclass
class Tone:
    hue: float = 0.0
    strength: float = 0.0  # stops of push on the most affected channel at full weight


@dataclass
class SplitTone:
    highlights: Tone = field(default_factory=lambda: Tone(38.0, 0.0))
    shadows: Tone = field(default_factory=lambda: Tone(190.0, 0.0))
    balance: float = 0.0        # stops: moves the shadow/highlight crossover from the pivot
    highlight_range: float = 3.0
    shadow_range: float = 4.0


@dataclass
class Shoulder:
    knee: float = 2.0         # stops over the pivot where the compression starts
    compress: float = 0.0     # 0..<1: how much the log2 slope drops far above the knee (0 = off)
    width: float = 1.5        # stops over which the slope eases from 1 to 1 - compress
    max_weight: float = 1.0   # norm = (1 - w) * luminance + w * max(RGB)


@dataclass
class LookSpec:
    name: str = "identity"
    description: str = ""
    exposure: float = 0.0
    contrast: Contrast = field(default_factory=Contrast)
    saturation: Saturation = field(default_factory=Saturation)
    split_tone: SplitTone = field(default_factory=SplitTone)
    shoulder: Shoulder = field(default_factory=Shoulder)
    black_lift: float = 0.0    # linear light added at black (mid grey kept)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "LookSpec":
        def take(klass: type, data: dict | None, nested: dict[str, type] | None = None) -> Any:
            data = dict(data or {})
            known = set(klass.__dataclass_fields__)
            unknown = set(data) - known
            if unknown:
                raise ValueError(f"{klass.__name__}: unknown keys {sorted(unknown)}")
            for k, sub in (nested or {}).items():
                if k in data:
                    data[k] = sub(data[k])
            return klass(**data)

        sat = lambda s: take(Saturation, s, {"skin": lambda k: take(Skin, k),  # noqa: E731
                                             "bands": lambda bs: [take(HueBand, b) for b in bs]})
        split = lambda s: take(SplitTone, s, {"highlights": lambda t: take(Tone, t),  # noqa: E731
                                              "shadows": lambda t: take(Tone, t)})
        return take(cls, {k: v for k, v in d.items() if not k.startswith("_")},
                    {"contrast": lambda c: take(Contrast, c), "saturation": sat, "split_tone": split,
                     "shoulder": lambda sh: take(Shoulder, sh)})


def load_spec(path: str | Path) -> LookSpec:
    return LookSpec.from_dict(json.loads(Path(path).read_text()))


# -- grade -----------------------------------------------------------------------------------
def _smoothstep(e0: float, e1: float, x: np.ndarray) -> np.ndarray:
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _luma(rgb: np.ndarray, w: np.ndarray = LUMA_709) -> np.ndarray:
    return rgb @ w


def _curve(v: np.ndarray, c: Contrast) -> np.ndarray:
    """Filmic contrast on linear values: f(x) = x + (a-1) s tanh(x/s) in log2 around the pivot.

    Monotonic for any a > 0 (slope between min(1, a) and max(1, a)); values <= 0 get the
    toe's asymptotic gain so the curve stays continuous through black.
    """
    a = c.amount
    if abs(a - 1.0) < 1e-12:
        return v
    pos = v > 1e-10
    x = np.log2(np.where(pos, v, 1.0) / c.pivot)
    s = np.where(x < 0, c.toe_stops, c.shoulder_stops)
    y = x + (a - 1.0) * s * np.tanh(x / s)
    black_gain = 2.0 ** (-(a - 1.0) * c.toe_stops)
    return np.where(pos, c.pivot * np.exp2(y), v * black_gain)


def _shoulder_ratio(n: np.ndarray, sh: Shoulder, pivot: float) -> np.ndarray:
    """Gain for a norm ``n``: 1 at and below the knee, then log2 slope 1 -> 1 - compress.

    y = x - c (d - w tanh(d / w)) with d = x - knee (log2 stops over the pivot): continuous
    with continuous slope at the knee, monotonic for c < 1.
    """
    pos = n > 1e-10
    x = np.log2(np.where(pos, n, 1.0) / pivot)
    d = np.maximum(x - sh.knee, 0.0)
    drop = sh.compress * (d - sh.width * np.tanh(d / sh.width))
    return np.where(pos, np.exp2(-drop), 1.0)


def _hsv_hue_sat(rgb_lin: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """HSV hue (degrees) and saturation of display-encoded (gamma 1/2.4) Rec.709 values."""
    e = np.clip(rgb_lin, 0.0, None) ** (1 / 2.4)
    mx, mn = e.max(-1), e.min(-1)
    d = mx - mn
    sat = np.where(mx > 1e-9, d / np.maximum(mx, 1e-9), 0.0)
    r, g, b = e[..., 0], e[..., 1], e[..., 2]
    dd = np.maximum(d, 1e-12)
    h = np.where(mx == r, ((g - b) / dd) % 6, np.where(mx == g, (b - r) / dd + 2, (r - g) / dd + 4)) * 60.0
    return np.where(d > 1e-9, h, 0.0), sat


def _hue_window(h: np.ndarray, center: float, width: float) -> np.ndarray:
    dist = np.abs((h - center + 180.0) % 360.0 - 180.0)
    t = np.clip((dist - width) / max(width, 1e-6), 0.0, 1.0)  # 0 inside, 1 at 2x width
    return 0.5 * (1 + np.cos(np.pi * t))


def _tone_vector(hue: float) -> np.ndarray:
    """Luminance-neutral chroma direction (Rec.709 linear) toward an HSV hue; max |v| = 1."""
    h = (hue % 360) / 60.0
    x = 1 - abs(h % 2 - 1)
    rgb = [(1, x, 0), (x, 1, 0), (0, 1, x), (0, x, 1), (x, 0, 1), (1, 0, x)][int(h) % 6]
    v = np.array(rgb, dtype=np.float64)
    v = v - v @ LUMA_709
    return v / np.abs(v).max()


def apply_look(rgb: np.ndarray, spec: LookSpec) -> np.ndarray:
    """Grade linear light with Rec.709 primaries (any shape (..., 3); negatives allowed)."""
    rgb = np.asarray(rgb, dtype=np.float64) * (2.0 ** spec.exposure)

    # 2. contrast
    c = spec.contrast
    if abs(c.amount - 1.0) > 1e-12:
        y = _luma(rgb)
        ratio = np.where(np.abs(y) > 1e-10, _curve(y, c) / np.where(np.abs(y) > 1e-10, y, 1.0), 1.0)
        hue_kept = rgb * ratio[..., None]
        per_chan = _curve(rgb, c)
        rgb = hue_kept + c.per_channel * (per_chan - hue_kept)

    # 3. saturation
    s = spec.saturation
    y = _luma(rgb)
    stops = np.log2(np.maximum(y, 1e-10) / c.pivot)
    hue, hsv_s = _hsv_hue_sat(rgb)
    gain = s.amount * (1.0 + s.vibrance * (1.0 - np.clip(hsv_s, 0.0, 1.0)))
    gain = gain * (1.0 + (s.highlight_floor - 1.0) * _smoothstep(s.highlight_start, s.highlight_end, stops))
    gain = gain + (1.0 - gain) * _smoothstep(s.shadow_start, s.shadow_end, stops)
    if s.skin.protect > 0:
        w = (_hue_window(hue, s.skin.hue, s.skin.width) * _smoothstep(0.06, 0.18, hsv_s)
             * (1.0 - _smoothstep(0.75, 0.95, hsv_s)))
        gain = 1.0 + (gain - 1.0) * (1.0 - s.skin.protect * w)
    for band in s.bands:
        w = _hue_window(hue, band.hue, band.width) * _smoothstep(0.04, 0.15, hsv_s)
        gain = gain * (1.0 + (band.gain - 1.0) * w)
    rgb = y[..., None] + gain[..., None] * (rgb - y[..., None])

    # 4. split toning (log offsets weighted by distance from the crossover)
    st = spec.split_tone
    if st.highlights.strength or st.shadows.strength:
        y = _luma(rgb)
        stops = np.log2(np.maximum(y, 1e-10) / c.pivot) - st.balance
        wh = _smoothstep(0.0, st.highlight_range, stops)
        ws = _smoothstep(0.0, st.shadow_range, -stops)
        push = (st.highlights.strength * wh[..., None] * _tone_vector(st.highlights.hue)
                + st.shadows.strength * ws[..., None] * _tone_vector(st.shadows.hue))
        rgb = rgb * np.exp2(push)

    # 5. highlight shoulder on a luminance / max(RGB) norm (ratios kept)
    sh = spec.shoulder
    if sh.compress > 0:
        norm = (1.0 - sh.max_weight) * _luma(rgb) + sh.max_weight * rgb.max(-1)
        rgb = rgb * _shoulder_ratio(norm, sh, c.pivot)[..., None]

    # 6. black lift, mid grey fixed
    if spec.black_lift:
        rgb = spec.black_lift + rgb * (1.0 - spec.black_lift / c.pivot)
    return rgb


def gamut_guard(rgb: np.ndarray, luma_w: np.ndarray) -> np.ndarray:
    """Desaturate toward luminance just enough that no channel is negative (hue kept)."""
    y = _luma(rgb, luma_w)[..., None]
    mn = rgb.min(-1, keepdims=True)
    # Only where a channel went clearly negative and luminance is positive; points with
    # non-positive luminance (e.g. pure DWG blue) are left for the final clamp.
    fix = (mn < -1e-7) & (y > 0)
    t = np.where(fix, y / np.maximum(y - mn, 1e-12), 1.0)
    return y + t * (rgb - y)


def apply_dwg_di(code: np.ndarray, spec: LookSpec) -> np.ndarray:
    """The LUT transform: DWG/DaVinci Intermediate code values in and out."""
    lin = di_decode(code)
    out709 = apply_look(lin @ DWG_TO_709.T, spec)
    out = gamut_guard(out709 @ REC709_TO_DWG.T, LUMA_DWG)
    return np.clip(di_encode(out), 0.0, 1.0)


def apply_rec709_display(code: np.ndarray, spec: LookSpec) -> np.ndarray:
    """Preview approximation on Rec.709 gamma 2.4 code values (0..1), see module doc."""
    lin = np.clip(np.asarray(code, dtype=np.float64), 0.0, 1.0) ** 2.4
    out = gamut_guard(apply_look(lin, spec), LUMA_709)
    return np.clip(out, 0.0, 1.0) ** (1 / 2.4)


# -- LUT file ----------------------------------------------------------------------------------
def lattice(size: int) -> np.ndarray:
    """(size, size, size, 3) grid indexed [b, g, r] (red fastest when flattened)."""
    g = np.linspace(0.0, 1.0, size)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")
    return np.stack([r, gg, b], axis=-1)


def build_lut(spec: LookSpec, size: int = 33, transform=apply_dwg_di) -> np.ndarray:
    return transform(lattice(size), spec)


def write_cube(path: str | Path, lut: np.ndarray, title: str, comments: list[str] | None = None) -> Path:
    size = lut.shape[0]
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {c}" for c in (comments or [])]
    lines += [f'TITLE "{title}"', f"LUT_3D_SIZE {size}", "DOMAIN_MIN 0.0 0.0 0.0", "DOMAIN_MAX 1.0 1.0 1.0"]
    flat = lut.reshape(-1, 3)
    body = "\n".join(f"{r:.6f} {g:.6f} {b:.6f}" for r, g, b in flat)
    path.write_text("\n".join(lines) + "\n" + body + "\n")
    return path


def read_cube(path: str | Path) -> np.ndarray:
    size = None
    rows: list[list[float]] = []
    for line in Path(path).read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("LUT_3D_SIZE"):
            size = int(line.split()[1])
        elif line[0].isdigit() or line[0] in "-.":
            rows.append([float(v) for v in line.split()])
    if size is None or len(rows) != size ** 3:
        raise ValueError(f"{path}: LUT_3D_SIZE {size} but {len(rows)} rows")
    return np.asarray(rows).reshape(size, size, size, 3)


def apply_lut(img: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Trilinear lookup of float RGB (..., 3) in 0..1 through a [b, g, r]-indexed LUT."""
    n = lut.shape[0]
    p = np.clip(img, 0.0, 1.0) * (n - 1)
    i0 = np.minimum(np.floor(p).astype(int), n - 2)
    f = p - i0
    out = np.zeros(img.shape, dtype=np.float64)
    for db in (0, 1):
        wb = f[..., 2] if db else 1 - f[..., 2]
        for dg in (0, 1):
            wg = f[..., 1] if dg else 1 - f[..., 1]
            for dr in (0, 1):
                wr = f[..., 0] if dr else 1 - f[..., 0]
                out += (wb * wg * wr)[..., None] * lut[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    return out


# -- measurement -------------------------------------------------------------------------------
def read_rgb(path: str | Path) -> np.ndarray:
    import cv2  # noqa: PLC0415

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        raise FileNotFoundError(path)
    return bgr[..., ::-1].copy()


def measure(rgb8: np.ndarray, skin_box: tuple[int, int, int, int] | None = None) -> dict:
    """Mean Rec.709 luma, Lab chroma, HSV S, clip % and (optionally) a skin box's HSV hue."""
    import cv2  # noqa: PLC0415

    a = rgb8.astype(np.float64)
    y = a @ LUMA_709
    lab = cv2.cvtColor(rgb8.astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)
    chroma = np.hypot(lab[..., 1], lab[..., 2])
    _, hs = _hsv_hue_sat((a / 255.0) ** 2.4)
    out = {"mean_luma": round(float(y.mean()), 1),
           "p02_luma": round(float(np.percentile(y, 2)), 1),
           "p98_luma": round(float(np.percentile(y, 98)), 1),
           "mean_chroma_lab": round(float(chroma.mean()), 1),
           "mean_hsv_s": round(float(hs.mean()), 3),
           "pct_luma_ge_235": round(float((y >= 235).mean() * 100), 2),
           "pct_luma_le_16": round(float((y <= 16).mean() * 100), 2),
           "pct_channel_ge_254": round(float((a.max(-1) >= 254).mean() * 100), 2)}
    if skin_box:
        x, yy, w, h = skin_box
        patch = a[yy:yy + h, x:x + w].reshape(-1, 3)
        mean = patch.mean(0)
        hue, sat = _hsv_hue_sat((mean[None] / 255.0) ** 2.4)
        plab = cv2.cvtColor(patch[None].astype(np.float32) / 255.0, cv2.COLOR_RGB2LAB)[0].mean(0)
        out["skin"] = {"box": list(skin_box), "mean_rgb": [round(float(v), 1) for v in mean],
                       "hsv_hue": round(float(hue[0]), 1), "hsv_s": round(float(sat[0]), 3),
                       "lab_hue": round(float(np.degrees(np.arctan2(plab[2], plab[1]))), 1),
                       "lab_chroma": round(float(np.hypot(plab[1], plab[2])), 1),
                       "natural": bool(15.0 <= hue[0] <= 35.0)}
    return out


# -- comparison grid ---------------------------------------------------------------------------
def grid(rows: list[str], cols: list[tuple[str, Path]], out: Path, cell_w: int = 270) -> Path:
    """rows = shot ids, cols = (label, still folder); writes a labelled PNG grid."""
    import cv2  # noqa: PLC0415

    cell_h = round(cell_w * 1920 / 1080)
    head, side, gap = 44, 64, 6
    W = side + len(cols) * (cell_w + gap)
    H = head + len(rows) * (cell_h + gap)
    canvas = np.full((H, W, 3), 18, np.uint8)
    font = cv2.FONT_HERSHEY_SIMPLEX
    for j, (label, _) in enumerate(cols):
        x = side + j * (cell_w + gap)
        cv2.putText(canvas, label, (x + 8, 30), font, 0.75, (235, 235, 235), 2, cv2.LINE_AA)
    for i, shot in enumerate(rows):
        y = head + i * (cell_h + gap)
        cv2.putText(canvas, shot, (8, y + 30), font, 0.75, (235, 235, 235), 2, cv2.LINE_AA)
        for j, (_, folder) in enumerate(cols):
            x = side + j * (cell_w + gap)
            f = Path(folder) / f"{shot}.png"
            if f.exists():
                im = cv2.resize(read_rgb(f), (cell_w, cell_h), interpolation=cv2.INTER_AREA)
                canvas[y:y + cell_h, x:x + cell_w] = im
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), canvas[..., ::-1])
    return out


# -- CLI ---------------------------------------------------------------------------------------
def _box(s: str | None) -> tuple[int, int, int, int] | None:
    return tuple(int(v) for v in s.split(",")) if s else None  # type: ignore[return-value]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.look", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build", help="write the DWG/DaVinci Intermediate .cube for a spec")
    b.add_argument("spec")
    b.add_argument("-o", "--out", required=True)
    b.add_argument("--size", type=int, default=33, choices=(17, 33, 65))
    p = sub.add_parser("preview", help="apply the look to a Rec.709 still (approximation)")
    p.add_argument("spec")
    p.add_argument("still")
    p.add_argument("-o", "--out", required=True)
    m = sub.add_parser("measure", help="luma / chroma / clipping (and skin hue) of stills")
    m.add_argument("stills", nargs="+")
    m.add_argument("--skin", help="x,y,w,h box for the skin hue check")
    g = sub.add_parser("grid", help="labelled comparison grid of still folders")
    g.add_argument("out")
    g.add_argument("--rows", required=True, help="comma-separated shot ids, e.g. s01,s05")
    g.add_argument("--col", action="append", required=True, help="label=folder (repeatable)")
    g.add_argument("--cell", type=int, default=270)
    a = ap.parse_args(argv)

    if a.cmd == "build":
        spec = load_spec(a.spec)
        lut = build_lut(spec, a.size)
        write_cube(a.out, lut, f"cf look {spec.name}",
                   [f"cf.look {spec.name}: {spec.description}",
                    "input and output: DaVinci Wide Gamut / DaVinci Intermediate (timeline space)",
                    f"spec: {Path(a.spec).name}"])
        print(f"{a.out}: {a.size}^3, {spec.name}")
    elif a.cmd == "preview":
        import cv2  # noqa: PLC0415

        spec = load_spec(a.spec)
        rgb = read_rgb(a.still).astype(np.float64) / 255.0
        out = apply_rec709_display(rgb, spec)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(a.out, np.round(out * 255).astype(np.uint8)[..., ::-1])
        print(f"{a.out} (Rec.709 approximation of {spec.name}; judge with Resolve stills)")
    elif a.cmd == "measure":
        for s in a.stills:
            print(json.dumps({"still": s, **measure(read_rgb(s), _box(a.skin))}))
    elif a.cmd == "grid":
        cols = [(c.split("=", 1)[0], Path(c.split("=", 1)[1]).expanduser()) for c in a.col]
        print(grid(a.rows.split(","), cols, Path(a.out).expanduser(), a.cell))
    return 0


if __name__ == "__main__":
    sys.exit(main())
