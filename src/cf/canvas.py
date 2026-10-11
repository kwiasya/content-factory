"""The output canvas: size and fps from ``style.json``, the reference-space scale, render bitrate.

``style.json`` ``canvas`` gives the active default output pixels (2160x3840). ``canvases``
holds named presets (``portrait``, ``landscape``), each with its own size, reference width
and, where they differ from the top-level ones, ``safe_zone``, ``overlay_positions`` and
``slots``. Every other pixel number in style.json is in the preset's reference space
(1080 wide for portrait, 1920 for landscape); ``Canvas.scale`` turns it into canvas pixels.

``resolve(style, spec)`` takes ``None`` (the active default), a preset name or ``'WxH'``
(the size with the geometry of the preset of the same aspect ratio). ``for_reel`` applies
the precedence the tools use: CLI ``--canvas`` > the Script's ``canvas`` > style.json
``canvas``. Pure, no Resolve.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

REFERENCE_WIDTH = 1080
DEFAULT_CANVAS = (2160, 3840, 30)
SUPERSCALE_OFF = 1
SUPERSCALE_2X = 2
UPSCALE_MODES = ("2x-enhanced", "2x")


@dataclass(frozen=True)
class Canvas:
    width: int
    height: int
    fps: int
    reference_width: int = REFERENCE_WIDTH
    # Geometry from the style.json canvases preset; not part of equality (a Canvas is its size,
    # fps and reference width) and unhashable dicts stay out of the hash.
    preset: str | None = field(default=None, compare=False)  # name in style.json canvases
    safe_zone: dict | None = field(default=None, compare=False)  # reference px; None = style.json's
    overlay_positions: dict | None = field(default=None, compare=False)  # reference px; None = style.json's
    slots: dict | None = field(default=None, compare=False)  # reference px; None = overlays/src/slots.json

    @property
    def landscape(self) -> bool:
        return self.width > self.height

    @property
    def scale(self) -> float:
        """Canvas pixels per reference pixel (2.0 at 2160 wide)."""
        return self.width / self.reference_width

    @property
    def name(self) -> str:
        return f"{self.width}x{self.height}"

    def px(self, reference_px: float) -> int:
        """A reference-space length in canvas pixels."""
        return round(reference_px * self.scale)


def parse_size(text: str) -> tuple[int, int]:
    """``'1080x1920'`` -> ``(1080, 1920)``; raises ValueError otherwise."""
    m = re.fullmatch(r"\s*(\d+)\s*[xX×]\s*(\d+)\s*", text or "")
    if not m:
        raise ValueError(f"canvas must look like 2160x3840, got {text!r}")
    w, h = int(m.group(1)), int(m.group(2))
    if w <= 0 or h <= 0 or w % 2 or h % 2:
        raise ValueError(f"canvas {w}x{h}: width and height must be positive and even")
    return w, h


def presets(style: dict) -> dict[str, dict]:
    """``style.json`` ``canvases`` without its ``_doc`` keys."""
    return {k: v for k, v in (style.get("canvases") or {}).items() if not k.startswith("_") and isinstance(v, dict)}


def _from_preset(style: dict, name: str | None, c: dict, size: tuple[int, int] | None = None) -> Canvas:
    base = style.get("canvas") or {}
    w, h = size or (int(c.get("width", DEFAULT_CANVAS[0])), int(c.get("height", DEFAULT_CANVAS[1])))
    # A WxH of the same aspect (e.g. 1080x1920) keeps the preset's reference space: scale 1.
    ref = int(c.get("reference_width", base.get("reference_width", REFERENCE_WIDTH)))
    return Canvas(w, h, int(c.get("fps", base.get("fps", DEFAULT_CANVAS[2]))), ref, name,
                  c.get("safe_zone"), c.get("overlay_positions"), c.get("slots"))


def _same_aspect(a: tuple[int, int], b: tuple[int, int]) -> bool:
    return a[0] * b[1] == a[1] * b[0]


def _default_preset(style: dict) -> tuple[str | None, dict]:
    """The preset the active ``canvas`` is (same size), else (None, ``canvas``)."""
    c = style.get("canvas") or {}
    size = (int(c.get("width", DEFAULT_CANVAS[0])), int(c.get("height", DEFAULT_CANVAS[1])))
    for name, p in presets(style).items():
        if (int(p.get("width", 0)), int(p.get("height", 0))) == size:
            return name, {**c, **p}
    return None, c


def resolve(style: dict, spec: str | None = None) -> Canvas:
    """The canvas for ``spec``: None = style.json ``canvas`` (the active default); a name from
    ``canvases`` (``'landscape'``); or ``'WxH'``, which takes the geometry (fps, reference width,
    safe zone, positions) of the preset with the same aspect ratio, the active one first.
    Raises ValueError for an unknown name or an aspect no preset has."""
    spec = (spec or "").strip()
    if not spec:
        name, c = _default_preset(style)
        return _from_preset(style, name, c)
    table = presets(style)
    if spec in table:
        return _from_preset(style, spec, table[spec])
    if not any(ch.isdigit() for ch in spec):
        raise ValueError(f"unknown canvas {spec!r}; style.json canvases has {sorted(table)} (or give WxH)")
    size = parse_size(spec)
    name, c = _default_preset(style)
    cs = (int(c.get("width", DEFAULT_CANVAS[0])), int(c.get("height", DEFAULT_CANVAS[1])))
    if _same_aspect(size, cs):
        return _from_preset(style, name, c, size)
    for pname, p in table.items():
        if _same_aspect(size, (int(p["width"]), int(p["height"]))):
            return _from_preset(style, pname, p, size)
    have = ", ".join(f"{k} {v.get('width')}x{v.get('height')}" for k, v in table.items())
    raise ValueError(f"canvas {spec}: no style.json canvases preset has that aspect ratio (has {have})")


def from_style(style: dict, override: str | None = None) -> Canvas:
    """The canvas of ``style.json``, or ``override`` (a preset name or 'WxH'); see ``resolve``."""
    return resolve(style, override)


def for_reel(style: dict, script_canvas: str | None = None, cli: str | None = None) -> Canvas:
    """Precedence: CLI ``--canvas`` > the Script's ``canvas`` > style.json ``canvas``."""
    return resolve(style, cli or script_canvas)


def spec_of(cli: str | None, script_canvas: str | None) -> str | None:
    """The canvas spec that wins (for reports): CLI, else the Script's, else None (the default)."""
    return cli or script_canvas or None


def safe_zone(style: dict, canvas: Canvas) -> dict:
    """The canvas's safe zone in reference pixels (its preset's, else style.json ``safe_zone``)."""
    return canvas.safe_zone if canvas.safe_zone is not None else (style.get("safe_zone") or {})


def overlay_positions(style: dict, canvas: Canvas) -> dict:
    """Overlay positions in reference pixels (the preset's, else style.json ``overlay_positions``)."""
    return canvas.overlay_positions if canvas.overlay_positions is not None else \
        (style.get("overlay_positions") or {})


def reference_size(canvas: Canvas) -> tuple[float, float]:
    """The canvas in reference pixels (1080x1920 portrait, 1920x1080 landscape at 4K)."""
    return canvas.width / canvas.scale, canvas.height / canvas.scale


def overlay_style(style: dict, canvas: Canvas) -> dict:
    """``style`` as the overlay renderer sees it on ``canvas``: ``canvas`` replaced by the
    resolved one and the preset's ``safe_zone`` / ``overlay_positions`` / ``slots`` swapped in
    (the same merge overlays/render.mjs does; this is the Python twin used by tests)."""
    out = dict(style)
    out["canvas"] = {"width": canvas.width, "height": canvas.height, "fps": canvas.fps,
                     "reference_width": canvas.reference_width, **({"preset": canvas.preset} if canvas.preset else {})}
    out["safe_zone"] = safe_zone(style, canvas)
    out["overlay_positions"] = overlay_positions(style, canvas)
    if canvas.slots is not None:
        out["slots"] = canvas.slots
    if canvas.overlay_positions is not None:
        out["role_placement"] = "overlay_positions"
    return out


def scaled_safe_zone(style: dict, canvas: Canvas) -> dict:
    """The canvas's safe zone in canvas pixels (the style keeps it in reference pixels)."""
    z = safe_zone(style, canvas)
    out = {k: canvas.px(z[k]) for k in ("top", "bottom", "left", "right") if k in z}
    rail = z.get("right_rail")
    if rail:
        out["right_rail"] = {"width": canvas.px(rail["width"]), "from_y": canvas.px(rail["from_y"])}
    return out


def render_bitrate_kbps(style: dict, canvas: Canvas) -> int:
    """``style.render.bitrate_mbps['WxH']`` as the kbit/s value SetRenderSettings ``VideoQuality`` takes."""
    table = (style.get("render") or {}).get("bitrate_mbps") or {}
    if isinstance(table, (int, float)):
        return int(round(float(table) * 1000))
    if canvas.name not in table:
        raise ValueError(f"style.json render.bitrate_mbps has no entry for {canvas.name} "
                         f"(has {sorted(table)})")
    return int(round(float(table[canvas.name]) * 1000))


def render_codec(style: dict) -> tuple[str, str]:
    r = style.get("render") or {}
    return str(r.get("format", "mp4")), str(r.get("codec", "H264"))


def preset_name(canvas: Canvas) -> str:
    return f"cf-instagram-{canvas.name}"


@dataclass(frozen=True)
class Upscale:
    """What cf.build writes to one clip's ``Super Scale`` (1 = off, 2 = 2x)."""
    clip: str
    display_height: int | None
    super_scale: int
    enhanced: bool
    sharpness: float | None
    noise_reduction: float | None
    reason: str

    def set_args(self) -> tuple:
        """Arguments after the property name for ``MediaPoolItem.SetClipProperty('Super Scale', ...)``.

        '2x Enhanced' only exists in the 4-argument form (README "Clip properties with
        enumerated values"); the 2-argument form gives plain 2x.
        """
        if self.enhanced:
            return (self.super_scale, float(self.sharpness), float(self.noise_reduction))
        return (self.super_scale,)


def upscale_plan(clips: dict[str, dict], canvas: Canvas, style: dict, enabled: bool = True) -> list[Upscale]:
    """Super Scale per clip: 2x (plain or Enhanced, ``style.upscale.mode``) where the clip's
    display height is below the canvas.

    ``clips`` is the manifest's file -> clip dict (``display_height``, else ``height``).
    Clips at or above the canvas height, clips of unknown size and every clip when
    ``enabled`` is False get 1 (off), written explicitly because the property lives on
    the media pool item and survives rebuilds.
    """
    cfg = style.get("upscale") or {}
    mode = cfg.get("mode", "2x")
    if mode not in UPSCALE_MODES:
        raise ValueError(f"style.json upscale.mode must be one of {UPSCALE_MODES}, got {mode!r}")
    sharp = float(cfg.get("sharpness", 0.5))
    nr = float(cfg.get("noise_reduction", 0.25))
    for name, v in (("sharpness", sharp), ("noise_reduction", nr)):
        if not 0.0 <= v <= 1.0:
            raise ValueError(f"style.json upscale.{name} must be in 0..1, got {v}")
    out = []
    for name, c in clips.items():
        h = c.get("display_height") or c.get("height")
        h = int(h) if h else None
        if not enabled:
            out.append(Upscale(name, h, SUPERSCALE_OFF, False, None, None, "--no-superscale"))
        elif h is None:
            out.append(Upscale(name, h, SUPERSCALE_OFF, False, None, None, "display height unknown"))
        elif h >= canvas.height:
            out.append(Upscale(name, h, SUPERSCALE_OFF, False, None, None, f"{h} >= canvas {canvas.height}"))
        else:
            enhanced = mode == "2x-enhanced"
            out.append(Upscale(name, h, SUPERSCALE_2X, enhanced, sharp if enhanced else None,
                               nr if enhanced else None, f"{h} < canvas {canvas.height}"))
    return out
