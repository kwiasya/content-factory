"""Reframe: a canvas-shaped window cut out of a source wider than the canvas (pure, no Resolve).

A landscape Clip (16:9) on the vertical canvas (9:16) is scaled so the source height fills
the canvas height ("fit height"), and the window slides along the source:

- ``follow`` (the default, ``style.json`` ``reframe.default``): a static window placed on the
  person by ``cf.follow`` (person detector on the proxy, the window that holds the whole person in
  the most frames, ties toward the end of the shot). It never leaves the source and has no Tilt.
- ``smart`` (off by default: it leaves black bands): Resolve Studio Smart Reframe (``TimelineItem.SmartReframe()``) pans the window
  to follow the subject. It only works after the fit-height zoom is set; on a fit-width
  (letterboxed) item it completes and changes nothing (probe, 2026-10-11).
- ``center``: the middle of the source, ``Pan`` 0.
- ``pan``: a fixed window at ``x`` (-1 = left edge of the source, 1 = right edge).
  ``x_end`` is recorded but not animated: the scripting API cannot keyframe Inspector
  properties (no keyframe call in the 21.1.1 stub), so cf.build applies a static pan at ``x``.

Inspector units (probe 2026-10-11, Resolve 21.1.1): ``ZoomX``/``ZoomY`` multiply the scale
the timeline's input scaling (``timelineInputResMismatchBehavior``) already applied; ``Pan``
is in canvas pixels and positive moves the image right, so showing the left part of the
source needs a positive Pan.

The math, for a source ``W x H`` on a canvas ``w x h`` with extra ``zoom`` z >= 1:

- scale s (canvas px per source px) = ``h / H * z``; the source is ``W*s`` canvas px wide.
- ZoomX = ``s / base``, where base is what Resolve applies at ZoomX 1: ``scaleToFit``
  min(w/W, h/H), ``scaleToCrop`` max(w/W, h/H), ``centerCrop`` 1.
- window in source px = ``w/s x h/s``; Pan range = ``+-(W*s - w)/2``; Pan = ``-x * range``.

DJI 3840x2160 on 2160x3840: s = 1.778, ZoomX = 3.160, window 1215x2160, Pan range +-2333.
iPhone 1920x1080: s = 3.556, ZoomX = 3.160, window 607x1080, same Pan range.
"""

from __future__ import annotations

import math
from dataclasses import asdict, dataclass

MODES = ("follow", "smart", "center", "pan")
DEFAULT_MODE = "follow"
MISMATCH_BASE = ("scaleToFit", "scaleToCrop", "centerCrop")
ASPECT_TOL = 0.01  # relative; 1920x1088 still counts as 16:9


@dataclass(frozen=True)
class Reframe:
    """A shot's ``reframe`` object from the Script."""
    mode: str
    x: float | None = None
    x_end: float | None = None
    zoom: float = 1.0

    def to_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def aspect_relation(src_w: float, src_h: float, canvas_w: float, canvas_h: float) -> str:
    """``'wider'``, ``'narrower'`` or ``'same'``: the source's aspect against the canvas's."""
    r = (src_w / src_h) / (canvas_w / canvas_h)
    if r > 1 + ASPECT_TOL:
        return "wider"
    if r < 1 - ASPECT_TOL:
        return "narrower"
    return "same"


def default_reframe(src_w: float | None, src_h: float | None, canvas_w: float, canvas_h: float,
                    mode: str = DEFAULT_MODE) -> Reframe | None:
    """``mode`` (``follow`` by default) for a source wider than the canvas (landscape on portrait), else None."""
    if not src_w or not src_h:
        return None
    return Reframe(mode) if aspect_relation(src_w, src_h, canvas_w, canvas_h) == "wider" else None


def default_mode(style: dict | None) -> str:
    """``style.json`` ``reframe.default`` (``follow`` when missing)."""
    m = ((style or {}).get("reframe") or {}).get("default") or DEFAULT_MODE
    if m not in MODES:
        raise ValueError(f"style.json reframe.default {m!r} not in {MODES}")
    return m


def base_scale(src_w: float, src_h: float, canvas_w: float, canvas_h: float, mismatch: str) -> float:
    """Canvas px per source px that Resolve applies at ZoomX 1 for the timeline's input scaling."""
    if mismatch == "scaleToFit":
        return min(canvas_w / src_w, canvas_h / src_h)
    if mismatch == "scaleToCrop":
        return max(canvas_w / src_w, canvas_h / src_h)
    if mismatch == "centerCrop":
        return 1.0
    raise ValueError(f"timelineInputResMismatchBehavior {mismatch!r}: reframe supports {MISMATCH_BASE}")


@dataclass(frozen=True)
class ReframePlan:
    """What cf.build writes to one V1 item, and what the window covers."""
    mode: str
    source: str                 # "display" WxH of the source
    canvas: str                 # WxH
    mismatch: str               # the timeline's input scaling
    x: float | None
    x_end: float | None
    zoom: float                 # extra zoom over fit height
    scale: float                # canvas px per source px (fit height x zoom)
    base_scale: float           # what Resolve applies at ZoomX 1
    zoom_x: float               # Inspector ZoomX (= ZoomY, ganged)
    pan: float                  # Inspector Pan, canvas px, at the start of the shot
    pan_end: float | None       # Pan for x_end (not applied: no keyframe API)
    pan_range: float            # |Pan| at x = +-1
    window_w: float             # source px visible
    window_h: float
    window_x0: float            # left edge of the window in source px (at Pan, before Smart Reframe)
    default: bool               # True when the Script had no reframe and the default applied
    notes: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        d = asdict(self)
        d["notes"] = list(self.notes)
        return d


def pan_for_x(x: float, pan_range: float) -> float:
    """Inspector Pan for window position ``x`` (-1 left edge, 0 centre, 1 right edge)."""
    p = -float(x) * pan_range
    return 0.0 if p == 0 else p


def plan_reframe(reframe: Reframe, src_w: float, src_h: float, canvas_w: float, canvas_h: float,
                 mismatch: str = "scaleToFit", default: bool = False) -> ReframePlan:
    """Zoom and Pan for one shot. Raises ValueError for a source that is not wider than the canvas."""
    if reframe.mode not in MODES:
        raise ValueError(f"reframe mode {reframe.mode!r} not in {MODES}")
    rel = aspect_relation(src_w, src_h, canvas_w, canvas_h)
    if rel != "wider":
        raise ValueError(f"reframe needs a source wider than the canvas: {src_w:g}x{src_h:g} is {rel} "
                         f"than {canvas_w:g}x{canvas_h:g}")
    zoom = float(reframe.zoom or 1.0)
    if zoom < 1.0:
        raise ValueError(f"reframe zoom must be >= 1, got {zoom:g}")
    s = canvas_h / src_h * zoom
    base = base_scale(src_w, src_h, canvas_w, canvas_h, mismatch)
    pan_range = (src_w * s - canvas_w) / 2
    notes: list[str] = []
    if reframe.mode == "follow" and reframe.x is None:
        raise ValueError("reframe mode 'follow' needs the window position from cf.follow (x)")
    x = reframe.x if reframe.mode in ("pan", "follow") else None
    pan = pan_for_x(x, pan_range) if x is not None else 0.0
    pan_end = None
    if reframe.mode == "pan" and reframe.x_end is not None:
        pan_end = pan_for_x(reframe.x_end, pan_range)
        if abs(reframe.x_end - (x or 0.0)) > 1e-9:
            notes.append(f"x_end {reframe.x_end:g} not animated: the API cannot keyframe Pan; static pan at x {x:g}")
    if reframe.mode == "smart":
        notes.append("Pan 0 is written; Smart Reframe then keyframes Pan (keyframes do not show in GetProperties)")
    window_w, window_h = canvas_w / s, canvas_h / s
    # Pan p moves the image right by p canvas px, i.e. the window left by p / s source px.
    window_x0 = (src_w - window_w) / 2 - pan / s
    return ReframePlan(
        mode=reframe.mode, source=f"{src_w:g}x{src_h:g}", canvas=f"{canvas_w:g}x{canvas_h:g}", mismatch=mismatch,
        x=x, x_end=reframe.x_end if reframe.mode == "pan" else None, zoom=zoom, scale=round(s, 6),
        base_scale=round(base, 6), zoom_x=s / base, pan=round(pan, 4),
        pan_end=None if pan_end is None else round(pan_end, 4), pan_range=round(pan_range, 4),
        window_w=round(window_w, 2), window_h=round(window_h, 2), window_x0=round(window_x0, 2),
        default=default, notes=tuple(notes))


def zoom_to_hide_band(band_px: float, canvas_len: float, zoom: float = 1.0, step: float = 0.05) -> float | None:
    """Extra zoom that would hide a Smart Reframe black band, or None when no zoom can.

    Smart Reframe moves the window to keep the subject centred and does not stop at the
    source edge, so a subject off the vertical centre leaves ``band_px`` canvas px of black at
    extra zoom ``zoom``. Its move is a fixed distance in source px, i.e. proportional to the
    zoom in canvas px (probe, 2026-10-11: 455 px at 1.0, 235 at 1.15, 15 at 1.3), while the
    margin is ``(z - 1) * canvas_len / 2``; so the move per unit zoom is
    ``t = ((zoom - 1) * canvas_len / 2 + band_px) / zoom`` and z >= 1 / (1 - 2t / canvas_len).
    Rounded up to ``step``.
    """
    if band_px <= 0:
        return zoom
    t = ((zoom - 1) * canvas_len / 2 + band_px) / zoom
    if 2 * t >= canvas_len:
        return None
    z = 1 / (1 - 2 * t / canvas_len)
    return round(math.ceil(z / step - 1e-9) * step, 4)


def from_shot(raw: object, where: str = "reframe") -> Reframe | None:
    """Parse a Script shot's ``reframe`` value (dict or None); raises ValueError on bad structure."""
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError(f"{where}: must be an object or null")
    unknown = sorted(set(raw) - {"mode", "x", "x_end", "zoom"})
    if unknown:
        raise ValueError(f"{where}: unknown keys {unknown}")
    mode = raw.get("mode")
    if not isinstance(mode, str):
        raise ValueError(f"{where}: 'mode' must be a string, got {mode!r}")
    vals = {}
    for k in ("x", "x_end", "zoom"):
        v = raw.get(k)
        if v is not None and (isinstance(v, bool) or not isinstance(v, (int, float))):
            raise ValueError(f"{where}: {k!r} must be a number, got {v!r}")
        vals[k] = None if v is None else float(v)
    return Reframe(mode=mode, x=vals["x"], x_end=vals["x_end"], zoom=1.0 if vals["zoom"] is None else vals["zoom"])


def problems(reframe: Reframe | None, src_w: float | None, src_h: float | None,
             canvas_w: float, canvas_h: float) -> list[str]:
    """Validator rules for one shot's explicit ``reframe`` (empty list = fine).

    The source size is the manifest's display size; without it only the field rules run.
    """
    if reframe is None:
        return []
    v: list[str] = []
    if reframe.mode not in MODES:
        v.append(f"reframe.mode {reframe.mode!r} not in {MODES}")
    if reframe.mode == "pan":
        if reframe.x is None:
            v.append("reframe mode 'pan' requires 'x' (-1 = left edge, 1 = right edge of the source)")
    elif reframe.mode == "follow":
        for k in ("x", "x_end"):
            if getattr(reframe, k) is not None:
                v.append(f"reframe.{k} is not set by hand for mode 'follow' (the build places the window "
                         f"on the person); use mode 'pan' for a fixed x")
    else:
        for k in ("x", "x_end"):
            if getattr(reframe, k) is not None:
                v.append(f"reframe.{k} is only for mode 'pan' (mode is {reframe.mode!r})")
    for k in ("x", "x_end"):
        val = getattr(reframe, k)
        if val is not None and not -1.0 <= val <= 1.0:
            v.append(f"reframe.{k} {val:g} must be in -1..1")
    if reframe.zoom < 1.0:
        v.append(f"reframe.zoom {reframe.zoom:g} must be >= 1")
    if src_w and src_h:
        rel = aspect_relation(src_w, src_h, canvas_w, canvas_h)
        if rel == "same":
            v.append(f"reframe set, but the clip ({src_w:g}x{src_h:g}) has the canvas's aspect "
                     f"({canvas_w:g}x{canvas_h:g}); reframe is only for clips whose aspect differs")
        elif rel == "narrower":
            v.append(f"reframe needs a clip wider than the canvas; {src_w:g}x{src_h:g} is narrower than "
                     f"{canvas_w:g}x{canvas_h:g}")
    return v


def display_size(clip: dict | None) -> tuple[int | None, int | None]:
    """Manifest display size (rotation applied), else the coded size, else (None, None)."""
    if not clip:
        return None, None
    w = clip.get("display_width") or clip.get("width")
    h = clip.get("display_height") or clip.get("height")
    return (int(w) if w else None), (int(h) if h else None)


def effective(reframe: Reframe | None, clip: dict | None, canvas_w: float, canvas_h: float,
              mode: str = DEFAULT_MODE) -> tuple[Reframe | None, bool]:
    """The reframe a shot gets: the Script's, else the default (``mode``) for its clip. Returns (reframe, is_default)."""
    if reframe is not None:
        return reframe, False
    w, h = display_size(clip)
    d = default_reframe(w, h, canvas_w, canvas_h, mode)
    return d, d is not None
