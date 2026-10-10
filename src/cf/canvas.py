"""The output canvas: size and fps from ``style.json``, the reference-space scale, render bitrate.

``style.json`` ``canvas`` gives the output pixels (2160x3840 by default). Every other pixel
number in style.json (``safe_zone``, ``overlay_positions``, font sizes) is in a 1080-wide
reference space (``canvas.reference_width``); ``Canvas.scale`` turns it into canvas pixels.
``cf.build`` and ``cf.render`` accept ``--canvas WxH`` to override the size for a
comparison render (the fps always comes from style.json). Pure, no Resolve.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

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


def from_style(style: dict, override: str | None = None) -> Canvas:
    """The canvas of ``style.json``, or ``override`` ('WxH') with the style's fps and reference width."""
    c = style.get("canvas") or {}
    w, h, fps = int(c.get("width", DEFAULT_CANVAS[0])), int(c.get("height", DEFAULT_CANVAS[1])), \
        int(c.get("fps", DEFAULT_CANVAS[2]))
    if override:
        w, h = parse_size(override)
    return Canvas(w, h, fps, int(c.get("reference_width", REFERENCE_WIDTH)))


def scaled_safe_zone(style: dict, canvas: Canvas) -> dict:
    """``style.safe_zone`` in canvas pixels (the style keeps it in reference pixels)."""
    z = style.get("safe_zone") or {}
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
