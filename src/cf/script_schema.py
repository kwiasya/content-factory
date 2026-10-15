"""Script (cf-script/1) data model, loader and validator for the writing rules.

Field reference and rules: ``docs/script-schema.md``. The validator checks only
what can be checked mechanically; the rest of the writing rules stay with the
writer. Overlay and caption rules apply only when those fields are present
(a first-pass Script may have ``overlay: null`` everywhere and no Track).

CLI::

    python -m cf.script_schema validate <script.json> [--manifest m.json] [--style style.json]
                                        [--shared-root PATH] [--db PATH] [--no-library]

exits 1 and prints one violation per line when the Script breaks a rule; warnings print as
``- WARN …`` and never fail. Shot ``assets`` (Library cues) are checked against the Library
(``cf.assets.context``: the Video folder's root, else the shared root, and factory.db, read-only); a Script
without cues never opens the store.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any

from cf import frames
from cf import reframe as rf
from cf.reframe import Reframe

if TYPE_CHECKING:
    from cf.assets import AssetContext

SCHEMA = "cf-script/1"
FORMATS = ("pov", "listicle", "levels", "day_in_the_life", "reveal", "contrast")
HOOK_TYPES = ("visual_payoff", "pov", "list", "contrast", "question", "curiosity")
ROLES = ("hook", "build", "payoff", "loop")
OVERLAY_TYPES = ("place", "fact", "line")
TRANSITIONS = ("cut", "dissolve", "dip")
ENDINGS = ("loop_seamless", "loop_match", "reveal_last", "question_overlay")

HOOK_WORDS = (5, 8)
OVERLAY_MAX_WORDS = 8
SHOT_MIN_S = 1.5
SHOT_MAX_S = 5.0
TOTAL_TOLERANCE_S = 3.0
TARGET_MAX_S = 90
MAX_HASHTAGS = 5
DEFAULT_FPS = 30.0  # timeline fps; the seam tolerance falls back to it without a manifest
DEFAULT_CANVAS = (2160, 3840)  # style.json canvas when no style is given
EPS = 1e-6

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STYLE = REPO_ROOT / "style.json"


class ScriptError(ValueError):
    """The file is not a structurally readable Script."""


@dataclass
class Overlay:
    text: str
    type: str
    span: int = 1  # shots it covers: this one and the next span-1 (one label across a place's shots)
    preset: str | None = None  # overlays/src/presets.ts name; None = style.json typography.preset
    anchor: str | dict | None = None  # slot name, or {"anchor", "x", "y", "align"?} in reference px
    in_frames: int | None = None  # fade-in frames for this overlay (0 = cuts on); None = style.animation
    out_frames: int | None = None  # fade-out frames (0 = cuts off); None = style.animation


CUE_KEYS = ("ref", "at_s", "dur_s", "pos", "db")


@dataclass
class AssetCue:
    """One Library Asset placed in a shot: ``at_s`` timeline seconds from the shot's start."""
    ref: str
    at_s: float
    dur_s: float | None = None
    pos: str | None = None
    db: float | None = None
    extra: tuple[str, ...] = ()


@dataclass
class Shot:
    id: str
    clip: str
    in_s: float
    out_s: float
    role: str
    speed: float = 1.0
    overlay: Overlay | None = None
    transition: str = "cut"
    beat_index: int | None = None
    fade_in_s: float = 0.0
    fade_out_s: float = 0.0
    reframe: Reframe | None = None  # None: the default for the clip (smart for landscape on portrait)
    assets: list[AssetCue] = field(default_factory=list)

    @property
    def duration_s(self) -> float:
        """Duration on the timeline (source span divided by speed)."""
        return (self.out_s - self.in_s) / self.speed if self.speed else float("inf")


@dataclass
class Hook:
    type: str
    text: str | None  # None: an explicit text-free Reel (music only); every shot overlay must then be null
    clip: str


@dataclass
class Script:
    walk: str
    concept: str
    format: str
    target_length_s: float
    hook: Hook
    shots: list[Shot]
    ending: str
    schema: str = SCHEMA
    audience: str | None = None
    cta: str | None = None
    caption: str | None = None
    hashtags: list[str] = field(default_factory=list)
    location_tag: str | None = None
    alt_text: str | None = None
    track: str | None = None
    track_in_s: float | None = None
    track_fade_out_s: float | None = None
    metrics: dict | None = None
    canvas: str | None = None  # style.json canvases name ('landscape') or 'WxH'; None = style.json canvas
    overlay_min_hold_s: float | None = None  # replaces style.animation.min_hold_s for this Script

    @property
    def total_s(self) -> float:
        return sum(s.duration_s for s in self.shots)


# -- loading -------------------------------------------------------------------
def _num(d: dict, key: str, where: str, default: Any = None) -> float:
    v = d.get(key, default)
    if v is None:
        raise ScriptError(f"{where}: missing {key!r}")
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ScriptError(f"{where}: {key!r} must be a number, got {v!r}")
    return float(v)


def _opt_num(d: dict, key: str, where: str) -> float | None:
    v = d.get(key)
    if v is None:
        return None
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        raise ScriptError(f"{where}: {key!r} must be a number or null, got {v!r}")
    return float(v)


def _str(d: dict, key: str, where: str, required: bool = True) -> str | None:
    v = d.get(key)
    if v is None:
        if required:
            raise ScriptError(f"{where}: missing {key!r}")
        return None
    if not isinstance(v, str):
        raise ScriptError(f"{where}: {key!r} must be a string, got {v!r}")
    return v


def cue_from_dict(d: Any, where: str) -> AssetCue:
    if not isinstance(d, dict):
        raise ScriptError(f"{where}: must be an object")
    return AssetCue(ref=_str(d, "ref", where), at_s=_num(d, "at_s", where), dur_s=_opt_num(d, "dur_s", where),
                    pos=_str(d, "pos", where, required=False), db=_opt_num(d, "db", where),
                    extra=tuple(k for k in d if k not in CUE_KEYS))


def shot_from_dict(d: dict, index: int) -> Shot:
    where = f"shots[{index}]"
    if not isinstance(d, dict):
        raise ScriptError(f"{where}: must be an object")
    ov = d.get("overlay")
    overlay = None
    if ov is not None:
        if not isinstance(ov, dict):
            raise ScriptError(f"{where}.overlay: must be an object or null")
        span = ov.get("span", 1)
        if isinstance(span, bool) or not isinstance(span, int) or span < 1:
            raise ScriptError(f"{where}.overlay: 'span' must be an int >= 1, got {span!r}")
        preset = ov.get("preset")
        if preset is not None and (not isinstance(preset, str) or not preset.strip()):
            raise ScriptError(f"{where}.overlay: 'preset' must be a non-empty string, got {preset!r}")
        anchor = ov.get("anchor")
        if anchor is not None and not isinstance(anchor, (str, dict)):
            raise ScriptError(f"{where}.overlay: 'anchor' must be a slot name or an object, got {anchor!r}")
        fades = {}
        for k in ("in_frames", "out_frames"):
            f = ov.get(k)
            if f is not None and (isinstance(f, bool) or not isinstance(f, int) or f < 0):
                raise ScriptError(f"{where}.overlay: {k!r} must be an int >= 0, got {f!r}")
            fades[k] = f
        overlay = Overlay(text=_str(ov, "text", f"{where}.overlay"), type=_str(ov, "type", f"{where}.overlay"),
                          span=span, preset=preset, anchor=anchor, **fades)
    try:
        reframe = rf.from_shot(d.get("reframe"), f"{where}.reframe")
    except ValueError as exc:
        raise ScriptError(str(exc)) from exc
    cues = d.get("assets")
    if cues is not None and not isinstance(cues, list):
        raise ScriptError(f"{where}: 'assets' must be a list of cues or null, got {cues!r}")
    beat = d.get("beat_index")
    if beat is not None and (isinstance(beat, bool) or not isinstance(beat, int)):
        raise ScriptError(f"{where}: 'beat_index' must be an int or null, got {beat!r}")
    return Shot(
        id=_str(d, "id", where, required=False) or f"s{index + 1:02d}",
        clip=_str(d, "clip", where),
        in_s=_num(d, "in_s", where),
        out_s=_num(d, "out_s", where),
        role=_str(d, "role", where),
        speed=_num(d, "speed", where, 1.0),
        overlay=overlay,
        transition=_str(d, "transition", where, required=False) or "cut",
        beat_index=beat,
        fade_in_s=_num(d, "fade_in_s", where, 0.0),
        fade_out_s=_num(d, "fade_out_s", where, 0.0),
        reframe=reframe,
        assets=[cue_from_dict(c, f"{where}.assets[{k}]") for k, c in enumerate(cues or [])],
    )


def from_dict(d: dict) -> Script:
    """Build a Script from parsed JSON; raises ScriptError on structural problems only."""
    if not isinstance(d, dict):
        raise ScriptError("script must be a JSON object")
    hook = d.get("hook")
    if not isinstance(hook, dict):
        raise ScriptError("missing 'hook' object")
    shots = d.get("shots")
    if not isinstance(shots, list) or not shots:
        raise ScriptError("'shots' must be a non-empty list")
    tags = d.get("hashtags") or []
    if not isinstance(tags, list) or not all(isinstance(t, str) for t in tags):
        raise ScriptError("'hashtags' must be a list of strings")
    return Script(
        schema=_str(d, "schema", "script"),
        walk=_str(d, "walk", "script"),
        concept=_str(d, "concept", "script"),
        format=_str(d, "format", "script"),
        target_length_s=_num(d, "target_length_s", "script"),
        hook=Hook(type=_str(hook, "type", "hook"),
                  text=None if "text" in hook and hook["text"] is None else _str(hook, "text", "hook"),
                  clip=_str(hook, "clip", "hook")),
        shots=[shot_from_dict(s, i) for i, s in enumerate(shots)],
        ending=_str(d, "ending", "script"),
        audience=_str(d, "audience", "script", required=False),
        cta=_str(d, "cta", "script", required=False),
        caption=_str(d, "caption", "script", required=False),
        hashtags=list(tags),
        location_tag=_str(d, "location_tag", "script", required=False),
        alt_text=_str(d, "alt_text", "script", required=False),
        track=_str(d, "track", "script", required=False),
        track_in_s=_opt_num(d, "track_in_s", "script"),
        track_fade_out_s=_opt_num(d, "track_fade_out_s", "script"),
        metrics=d.get("metrics"),
        canvas=_str(d, "canvas", "script", required=False),
        overlay_min_hold_s=_opt_num(d, "overlay_min_hold_s", "script"),
    )


def load(path: str | Path) -> Script:
    try:
        data = json.loads(Path(path).expanduser().read_text())
    except json.JSONDecodeError as exc:
        raise ScriptError(f"{path}: not valid JSON: {exc}") from exc
    return from_dict(data)


def load_json(path: str | Path | None) -> dict | None:
    return json.loads(Path(path).expanduser().read_text()) if path else None


def manifest_clips(manifest: dict | None) -> dict[str, dict]:
    """Clip id (file name) -> manifest entry."""
    return {c["file"]: c for c in (manifest or {}).get("clips", [])}


# -- validation ----------------------------------------------------------------
def words(text: str) -> int:
    """Words in ``text``; a token with no letter or digit (an emoji, a dash) is not a word."""
    return sum(1 for t in text.split() if any(ch.isalnum() for ch in t))


ANCHOR_TYPES = ("center", "middle-left", "top-right", "top-left", "top-center", "bottom-left", "bottom-center")
OVERLAYS_SRC = REPO_ROOT / "overlays" / "src"


def known_presets(presets_ts: Path = OVERLAYS_SRC / "presets.ts") -> set[str] | None:
    """Preset names in ``overlays/src/presets.ts`` (the same scan render.mjs does); None if absent."""
    try:
        src = presets_ts.read_text(encoding="utf-8")
    except OSError:
        return None
    return {"legacy", *re.findall(r'^  "([a-z0-9-]+)": \{$', src, flags=re.M)}


def known_slots(style: dict, canvas: str | None = None) -> set[str] | None:
    """Slot names an overlay ``anchor`` may name: the canvas preset's ``slots`` or ``overlays/src/slots.json``."""
    table = None
    if canvas:
        table = ((style.get("canvases") or {}).get(canvas) or {}).get("slots")
    if table is None:
        table = style.get("slots")
    if table is None:
        try:
            table = json.loads((OVERLAYS_SRC / "slots.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
    return {k for k in table if not k.startswith("_")}


def overlay_anchor_problems(anchor: Any, slots: set[str] | None) -> list[str]:
    """Problems with an overlay ``anchor``: a known slot name, or an explicit
    ``{"anchor", "x", "y", "align"?}`` in reference px (the shape overlays/render.mjs accepts)."""
    if anchor is None:
        return []
    if isinstance(anchor, str):
        if slots is not None and anchor not in slots:
            return [f"overlay.anchor {anchor!r} is not a slot (known: {', '.join(sorted(slots))})"]
        return []
    out = []
    extra = sorted(set(anchor) - {"anchor", "x", "y", "align"})
    if extra:
        out.append(f"overlay.anchor has unknown keys {extra}")
    if anchor.get("anchor") not in ANCHOR_TYPES:
        out.append(f"overlay.anchor.anchor {anchor.get('anchor')!r} not in {ANCHOR_TYPES}")
    num = lambda x: isinstance(x, (int, float)) and not isinstance(x, bool)  # noqa: E731
    if not num(anchor.get("y")):
        out.append(f"overlay.anchor.y must be a number (reference px), got {anchor.get('y')!r}")
    a = str(anchor.get("anchor") or "")
    if "x" in anchor and not num(anchor["x"]) or (a.endswith(("-left", "-right")) and not num(anchor.get("x"))):
        out.append(f"overlay.anchor.x must be a number (reference px) for {a!r}, got {anchor.get('x')!r}")
    if anchor.get("align") not in (None, "left", "center", "right"):
        out.append(f"overlay.anchor.align {anchor['align']!r} not in ('left', 'center', 'right')")
    return out


def overlay_cover(shots: list[Shot]) -> dict[int, int]:
    """Shot index -> index of the earlier shot whose spanning overlay covers it (span > 1 only)."""
    cover: dict[int, int] = {}
    for i, s in enumerate(shots):
        if s.overlay is not None and s.overlay.span > 1:
            for j in range(i + 1, min(i + s.overlay.span, len(shots))):
                cover.setdefault(j, i)
    return cover


@dataclass
class Findings:
    problems: list[str]
    warnings: list[str]


def has_cues(script: Script) -> bool:
    return any(s.assets for s in script.shots)


def check(script: Script, manifest: dict | None = None, style: dict | None = None,
          assets: "AssetContext | None" = None, *, cues: bool = True) -> Findings:
    """Violations and warnings; the Asset cue rules run only when the Script has cues and ``cues`` is true
    (false: a build that leaves the cues out checks the rest of the Script only)."""
    problems = _problems(script, manifest, style)
    if not cues or not has_cues(script):
        return Findings(problems, [])
    f = asset_findings(script, assets, style or {}, manifest)
    return Findings(problems + f.problems, f.warnings)


def validate(script: Script, manifest: dict | None = None, style: dict | None = None,
             assets: "AssetContext | None" = None) -> list[str]:
    """Return the list of rule violations (empty when the Script is valid)."""
    return check(script, manifest, style, assets).problems


def _problems(script: Script, manifest: dict | None = None, style: dict | None = None) -> list[str]:
    v: list[str] = []
    style = style or {}
    shot_s = (style.get("pacing") or {}).get("shot_s") or {}
    shot_min = float(shot_s.get("min", SHOT_MIN_S))
    payoff_max = max(SHOT_MAX_S, float(shot_s.get("payoff_max", SHOT_MAX_S)))
    min_hold = float((style.get("animation") or {}).get("min_hold_s", 2.0))
    if script.overlay_min_hold_s is not None:
        if script.overlay_min_hold_s <= 0:
            v.append(f"overlay_min_hold_s: must be > 0, got {script.overlay_min_hold_s:g}")
        else:
            min_hold = script.overlay_min_hold_s
    try:
        canvas_w, canvas_h = canvas_size(style, script.canvas)
    except ValueError as exc:
        v.append(f"canvas: {exc}")
        canvas_w, canvas_h = canvas_size(style)
    clips = manifest_clips(manifest)
    presets = known_presets()
    slots = known_slots(style, script.canvas)

    if script.schema != SCHEMA:
        v.append(f"schema: expected {SCHEMA!r}, got {script.schema!r}")
    if manifest and manifest.get("walk") and script.walk != manifest["walk"]:
        v.append(f"walk: {script.walk!r} does not match the manifest's {manifest['walk']!r}")
    if not script.concept.strip():
        v.append("concept: empty")
    if script.format not in FORMATS:
        v.append(f"format: {script.format!r} not in {FORMATS}")
    if script.ending not in ENDINGS:
        v.append(f"ending: {script.ending!r} not in {ENDINGS}")
    if not 0 < script.target_length_s <= TARGET_MAX_S:
        v.append(f"target_length_s: {script.target_length_s:g} must be in (0, {TARGET_MAX_S}]")

    # Hook.
    if script.hook.type not in HOOK_TYPES:
        v.append(f"hook.type: {script.hook.type!r} not in {HOOK_TYPES}")
    if script.hook.text is None:
        # An explicit text-free Reel (music only): no overlay anywhere.
        texted = [s.id for s in script.shots if s.overlay is not None]
        if texted:
            v.append(f"hook.text: null marks a text-free Reel, but {', '.join(texted)} carry an overlay; "
                     "set every overlay to null or give the hook a text")
    else:
        n = words(script.hook.text)
        if not HOOK_WORDS[0] <= n <= HOOK_WORDS[1]:
            v.append(f"hook.text: {n} words, must be {HOOK_WORDS[0]}-{HOOK_WORDS[1]}: {script.hook.text!r}")
    if clips and script.hook.clip not in clips:
        v.append(f"hook.clip: {script.hook.clip!r} not in the manifest")
    if script.shots and script.shots[0].clip != script.hook.clip:
        v.append(f"hook.clip: {script.hook.clip!r} must be the first shot's clip "
                 f"(first shot is {script.shots[0].clip!r})")

    # Shots.
    seen: set[str] = set()
    covered = overlay_cover(script.shots)
    for i, s in enumerate(script.shots):
        w = f"shots[{i}] ({s.id})"
        if s.id in seen:
            v.append(f"{w}: duplicate shot id")
        seen.add(s.id)
        if s.role not in ROLES:
            v.append(f"{w}: role {s.role!r} not in {ROLES}")
        if s.transition not in TRANSITIONS:
            v.append(f"{w}: transition {s.transition!r} not in {TRANSITIONS}")
        if s.speed <= 0:
            v.append(f"{w}: speed must be > 0, got {s.speed:g}")
            continue
        if s.in_s < 0 or s.out_s <= s.in_s:
            v.append(f"{w}: need 0 <= in_s < out_s, got in_s={s.in_s:g} out_s={s.out_s:g}")
        if clips:
            c = clips.get(s.clip)
            if c is None:
                v.append(f"{w}: clip {s.clip!r} not in the manifest")
            elif s.out_s > float(c["duration_s"]) + EPS:
                v.append(f"{w}: out_s={s.out_s:g} is past the end of {s.clip} ({float(c['duration_s']):g} s)")
        src_w, src_h = rf.display_size(clips.get(s.clip))
        v.extend(f"{w}: {p}" for p in rf.problems(s.reframe, src_w, src_h, canvas_w, canvas_h))
        if s.reframe is None and src_w and src_h and \
                rf.aspect_relation(src_w, src_h, canvas_w, canvas_h) == "narrower":
            v.append(f"{w}: clip {s.clip} ({src_w}x{src_h}) is narrower than the {canvas_w}x{canvas_h} canvas: "
                     "it would leave black bands at the sides (no fill exists); use a clip of the canvas "
                     "aspect or wider")
        for h in (s.reframe.hold_s if s.reframe else ()):
            if not s.in_s - EPS <= h <= s.out_s + EPS:
                v.append(f"{w}: reframe.hold_s {h:g} is outside the shot ({s.in_s:g}-{s.out_s:g} s)")
        d = s.duration_s
        hi = payoff_max if s.role == "payoff" else SHOT_MAX_S
        if d < shot_min - EPS or d > hi + EPS:
            v.append(f"{w}: lasts {d:.2f} s on the timeline, must be {shot_min:g}-{hi:g} s"
                     + ("" if s.role == "payoff" else " (only payoff may be longer)"))
        if s.fade_in_s < 0 or s.fade_out_s < 0 or s.fade_in_s + s.fade_out_s > d + EPS:
            v.append(f"{w}: fades {s.fade_in_s:g}+{s.fade_out_s:g} s do not fit a {d:.2f} s shot")
        if s.overlay is not None:
            if s.overlay.type not in OVERLAY_TYPES:
                v.append(f"{w}: overlay.type {s.overlay.type!r} not in {OVERLAY_TYPES}")
            if s.overlay.preset is not None and presets is not None and s.overlay.preset not in presets:
                v.append(f"{w}: overlay.preset {s.overlay.preset!r} not in overlays/src/presets.ts "
                         f"(known: {', '.join(sorted(presets))})")
            v.extend(f"{w}: {p}" for p in overlay_anchor_problems(s.overlay.anchor, slots))
            ow = words(s.overlay.text)
            if ow == 0 or ow > OVERLAY_MAX_WORDS:
                v.append(f"{w}: overlay has {ow} words, must be 1-{OVERLAY_MAX_WORDS}: {s.overlay.text!r}")
            span = s.overlay.span
            last = i + span - 1
            if last >= len(script.shots):
                v.append(f"{w}: overlay span {span} runs past the last shot ({len(script.shots) - i} shot(s) left)")
            elif span > 1 and script.ending == "loop_seamless" and last == len(script.shots) - 1 \
                    and s.overlay.type != "line":
                v.append(f"{w}: overlay span {span} reaches the loop's last shot {script.shots[-1].id}; "
                         "only a 'line' overlay may run into it (it ends on the last frame and hands over "
                         "to the hook at frame 0)")
            held = sum(x.duration_s for x in script.shots[i:last + 1])
            if held < min_hold - EPS:
                v.append(f"{w}: overlay holds {held:.2f} s"
                         + (f" over {span} shots" if span > 1 else "") + f", must hold >= {min_hold:g} s")
        if covered.get(i) is not None and s.overlay is not None:
            v.append(f"{w}: has its own overlay inside the span of {script.shots[covered[i]].id}'s overlay")

    if script.ending == "loop_seamless":
        v.extend(loop_seamless_problems(script, clips, style))

    total = script.total_s
    if abs(total - script.target_length_s) > TOTAL_TOLERANCE_S + EPS:
        v.append(f"total: shots add up to {total:.2f} s, target is {script.target_length_s:g} "
                 f"+/- {TOTAL_TOLERANCE_S:g} s")

    # Track.
    for key in ("track_in_s", "track_fade_out_s"):
        val = getattr(script, key)
        if val is not None and val < 0:
            v.append(f"{key}: must be >= 0, got {val:g}")
        if val is not None and not script.track:
            v.append(f"{key}: set without a track")

    # Publishing fields.
    if len(script.hashtags) > MAX_HASHTAGS:
        v.append(f"hashtags: {len(script.hashtags)}, at most {MAX_HASHTAGS}")
    if not (script.location_tag or "").strip():
        v.append("location_tag: must always be set")
    if script.caption is not None:
        if not script.caption.strip():
            v.append("caption: empty")
        elif script.cta and script.cta.strip() not in script.caption:
            v.append("caption: must end with the CTA (cta text not found in the caption)")
    return v


def loop_seamless_problems(script: Script, clips: dict[str, dict], style: dict) -> list[str]:
    """``ending: loop_seamless``: the last shot runs into the first one's first source frame.

    One continuous action from one Clip is split at a seam P: the last shot plays O->P and
    the first shot P->Q, both at speed 1.0, so when the Reel loops the last frame is
    followed by the next source frame. Checked in frames as Resolve places them (``cf.frames``):
    the Clip's fps from the manifest (else the timeline's), the timeline's from ``canvas.fps``.
    """
    v: list[str] = []
    if len(script.shots) < 2:
        return ["ending loop_seamless: needs at least 2 shots (the last one runs into the first)"]
    first, last = script.shots[0], script.shots[-1]
    w = f"ending loop_seamless ({last.id} -> {first.id})"
    if last.clip != first.clip:
        v.append(f"{w}: the last shot's clip {last.clip!r} must be the first shot's clip {first.clip!r}")
    tl_fps = float((style.get("canvas") or {}).get("fps") or DEFAULT_FPS)
    fps = float((clips.get(first.clip) or {}).get("fps") or tl_fps)
    # In frames, as Resolve places them (cf.frames): the run-up, continued one timeline frame,
    # shows the hook's first source frame. At equal rates that is out_s == in_s; at 29.97 on 30
    # the run-up starts one source frame later than the seconds say.
    seam = frames.first_frame(first.in_s, fps)
    start = frames.first_frame(last.in_s, fps)
    n = frames.snap_frames((last.out_s - last.in_s) / (last.speed or 1.0), tl_fps)
    nxt = frames.next_frame(start, n, fps, tl_fps)
    if nxt != seam:
        want = frames.run_up_start(seam, n, fps, tl_fps)
        want_in = float(want / frames.exact_fps(fps))
        v.append(f"{w}: the last shot must run into the first shot's first source frame {seam} "
                 f"({first.in_s:g} s at {fps:g} fps): from frame {start} ({last.in_s:g} s) its {n} timeline "
                 f"frames at {tl_fps:g} fps continue at frame {nxt} ({'skips' if nxt < seam else 'repeats'} "
                 f"{abs(seam - nxt)}); start it at frame {want} (in_s {want_in:.4f}, out_s "
                 f"{want_in + n / tl_fps:.4f})")
    for s in (first, last):
        if abs(s.speed - 1.0) > EPS:
            v.append(f"{w}: {s.id} speed must be 1.0, got {s.speed:g}")
    if first.transition != "cut":
        v.append(f"{w}: {first.id} transition must be 'cut' (Instagram loops without black), "
                 f"got {first.transition!r}")
    if first.fade_in_s > EPS:
        v.append(f"{w}: {first.id} fade_in_s must be 0, got {first.fade_in_s:g}")
    if last.fade_out_s > EPS:
        v.append(f"{w}: {last.id} fade_out_s must be 0, got {last.fade_out_s:g}")
    if last.overlay is not None and last.overlay.type != "line":
        v.append(f"{w}: {last.id} may only carry a 'line' overlay: it ends on the last frame and hands "
                 f"over to the hook at frame 0; a {last.overlay.type!r} overlay would vanish at the seam "
                 f"({last.overlay.text!r})")
    # The window must not jump at the seam: same reframe (explicit or the clip's default), and a
    # pan ends where the first shot's pan starts.
    try:
        cw, ch = canvas_size(style, script.canvas)
    except ValueError:
        cw, ch = canvas_size(style)
    dm = rf.default_mode(style)
    a, _ = rf.effective(last.reframe, clips.get(last.clip), cw, ch, dm)
    b, _ = rf.effective(first.reframe, clips.get(first.clip), cw, ch, dm)
    if a is not None or b is not None:
        a_end = (a.x_end if a.x_end is not None else a.x) if a else None
        if (a.mode if a else None) != (b.mode if b else None) or (a and b and abs(a.zoom - b.zoom) > EPS) or \
                (a and a.mode == "pan" and (a_end is None or b.x is None or abs(a_end - b.x) > EPS)):
            v.append(f"{w}: the window would jump at the seam: {last.id} reframe "
                     f"{a.to_dict() if a else None} must end where {first.id} reframe "
                     f"{b.to_dict() if b else None} starts (same mode and zoom; a pan's end x = the first x)")
    return v


def _cue_fps(style: dict, script: Script) -> float:
    try:
        from cf.canvas import resolve  # noqa: PLC0415

        return float(resolve(style, script.canvas).fps)
    except ValueError:
        return float((style.get("canvas") or {}).get("fps") or DEFAULT_FPS)


def shot_starts_frames(script: Script, manifest: dict | None, fps: float) -> tuple[list[int], int]:
    """Each shot's first timeline frame and the Reel's length in frames, laid back to back as the build lays
    them without cuts.json (a clip's fps from the manifest, else the timeline's)."""
    clips = manifest_clips(manifest)
    starts, t = [], 0
    for s in script.shots:
        starts.append(t)
        try:
            cfps = float((clips.get(s.clip) or {}).get("fps") or fps)
        except (TypeError, ValueError):
            cfps = fps
        t += frames.shot_frames(s.in_s, s.out_s, s.speed, cfps if cfps > 0 else fps, fps) if s.speed > 0 else 0
    return starts, t


def asset_findings(script: Script, ctx: "AssetContext | None", style: dict,
                   manifest: dict | None = None) -> Findings:
    """The Asset cue rules (docs/script-schema.md, Assets); ``ctx`` None means no Library was loaded. A cue's
    span and the Reel's end are in timeline frames, snapped as the build snaps them."""
    from cf import assets as ca  # noqa: PLC0415

    problems: list[str] = []
    warnings: list[str] = []
    cfg = ca.settings(style)
    fps = _cue_fps(style, script)
    frame = 1.0 / fps
    cues = [(i, s, k, c) for i, s in enumerate(script.shots) for k, c in enumerate(s.assets)]
    for i, s, k, c in cues:
        for key in c.extra:
            problems.append(f"shots[{i}] ({s.id}).assets[{k}]: unknown key {key!r} "
                            f"(known: {', '.join(CUE_KEYS)})")
    library = ctx.library if ctx is not None else None
    if library is None:
        why = ctx.library_problem if ctx is not None else "no Library context was loaded (--no-library)"
        hint = ("index a Pack with python -m cf.library index, or pass --shared-root/--db"
                if ctx is None or ctx.cli else "index a Pack with /index-pack")
        problems.append(f"assets: {len(cues)} cue(s) need the Library: {why} ({hint})")
        return Findings(problems, warnings)
    unlocked: dict[str, set[str]] = {}
    for ref, files in ctx.md_refs.items():
        try:
            hit = ca.lookup(library, ref)
        except ca.BadRef:
            hit = None
        if hit is not None:
            unlocked.setdefault(hit.id, set()).update(files)
    starts, total_f = shot_starts_frames(script, manifest, fps)
    clear_f = round(float(cfg["loop_clear_s"]) * fps)
    spans: dict[str, list[tuple[float, float, str]]] = {kind: [] for kind in ca.CUE_TRACKS}
    for i, s, k, c in cues:
        w = f"shots[{i}] ({s.id}).assets[{k}] ({c.ref})"
        try:
            a = ca.lookup(library, c.ref)
        except ca.BadRef:
            problems.append(f"{w}: not an Asset ref (expected @<category>/<name>)")
            continue
        if a is None:
            near = ca.nearest_refs(library, c.ref, 5)
            problems.append(f"{w}: no such Asset; nearest: {', '.join(near) if near else 'none'}")
            continue
        kind = ca.lane_kind(a)
        if kind is None:
            problems.append(f"{w}: {a.ref} is a {a.category} Asset; cues place {', '.join(ca.PLACEABLE)}")
            continue
        if a.rights == "unknown":
            short = a.category == "sfx" and ca.finite(a.duration_s) and a.duration_s < float(cfg["sfx_free_max_s"])
            if short:
                warnings.append(f"{w}: unknown rights; allowed: a sound effect under {cfg['sfx_free_max_s']:g} s")
            elif a.id in unlocked:
                warnings.append(f"{w}: unknown rights; allowed: the Author referenced it in "
                                f"{', '.join(sorted(unlocked[a.id]))}")
            else:
                problems.append(f"{w}: unknown rights: use it only after the Author references it in the Video's "
                                "md files (brief.md, notes.md, …) or marks its rights own/free in Library")
        place = ca.placement(a)
        if place.problem:
            problems.append(f"{w}: {place.problem}")
            continue
        if place.note:
            warnings.append(f"{w}: {place.note}")
        sound = ca.has_sound(a, place)
        if sound and ca.loudness(a) is None:
            problems.append(f"{w}: loudness not measured: run python -m cf.library index {a.pack} "
                            "(without --no-loudness)")
        if c.pos is not None:
            if kind == "audio":
                problems.append(f"{w}: pos is for pictures; {a.ref} is a sound")
            elif c.pos not in ca.POS_PRESETS:
                problems.append(f"{w}: pos {c.pos!r} is not one of {', '.join(ca.POS_PRESETS)}")
        if c.db is not None:
            lo, hi = ca.CUE_DB_RANGE
            if not sound:
                problems.append(f"{w}: db on a silent picture ({a.ref} has no sound)")
            elif not lo <= c.db <= hi:
                problems.append(f"{w}: db {c.db:g} must be in [{lo:g}, {hi:g}]")
        d = s.duration_s
        if not 0 <= c.at_s < d - EPS:
            problems.append(f"{w}: at_s {c.at_s:g} must be in [0, {d:g}) (timeline seconds from the shot's start)")
            continue
        dur = c.dur_s if c.dur_s is not None else ca.default_dur_s(a, place, style)
        if dur is None:
            problems.append(f"{w}: the Asset's length is unknown: give dur_s")
            continue
        if dur < frame - EPS:
            problems.append(f"{w}: dur_s {dur:g} must be at least one frame ({frame:.3f} s)")
            continue
        if place.still:
            if dur > float(cfg["still_max_s"]) + EPS:
                problems.append(f"{w}: dur_s {dur:g} is longer than a still may stay ({cfg['still_max_s']:g} s)")
        elif ca.finite(a.duration_s) and dur > a.duration_s + frame + EPS:
            problems.append(f"{w}: dur_s {dur:g} is longer than the Asset ({a.duration_s:g} s)")
        at_f, dur_f = frames.cue_frames(c.at_s, dur, fps)
        begin_f = starts[i] + at_f
        end_f = begin_f + dur_f
        begin, end = begin_f / fps, end_f / fps
        if end_f > total_f:
            problems.append(f"{w}: runs {(end_f - total_f) / fps:.2f} s past the end of the Reel "
                            f"({end_f - total_f} frame(s) at {fps:g} fps)")
        if kind == "video" and script.ending == "loop_seamless" and end_f > total_f - clear_f:
            problems.append(f"{w}: a sticker or picture on screen at the loop seam jumps away when the Reel "
                            f"loops: end it ≥ {cfg['loop_clear_s']:g} s before the end "
                            f"(at_s + dur_s ≤ {round((total_f - clear_f - starts[i]) / fps, 3):g})")
        label = f"{s.id} {c.ref}"
        if kind == "video":
            spans["video"].append((begin, end, label))
        if sound:
            spans["audio"].append((begin, end, label))
    for kind, rows in spans.items():
        problems.extend(f"{len(group)} {kind} cues overlap at {at:.2f} s ({', '.join(group)}); "
                        f"at most {len(ca.CUE_TRACKS[kind])}" for at, group in overlaps(rows, len(ca.CUE_TRACKS[kind])))
    return Findings(problems, warnings)


def overlaps(spans: list[tuple[float, float, str]], limit: int) -> list[tuple[float, list[str]]]:
    """Instants where more than ``limit`` spans are open: ``(time, labels by start)``, each set once."""
    out: list[tuple[float, list[str]]] = []
    seen: set[tuple[str, ...]] = set()
    ordered = sorted(spans, key=lambda x: (x[0], x[2]))
    for begin, _, _ in ordered:
        active = [x for x in ordered if x[0] <= begin + EPS and x[1] > begin + EPS]
        if len(active) > limit:
            key = tuple(x[2] for x in active)
            if key not in seen:
                seen.add(key)
                out.append((begin, list(key)))
    return out


def canvas_size(style: dict | None, spec: str | None = None) -> tuple[int, int]:
    """Width and height of the canvas ``spec`` (the Script's ``canvas``: a style.json
    ``canvases`` name or 'WxH'), else of style.json ``canvas`` (2160x3840 when missing).
    Raises ValueError for a spec ``cf.canvas.resolve`` does not know."""
    if spec:
        from cf.canvas import resolve  # noqa: PLC0415

        c = resolve(style or {}, spec)
        return c.width, c.height
    c = (style or {}).get("canvas") or {}
    return int(c.get("width", DEFAULT_CANVAS[0])), int(c.get("height", DEFAULT_CANVAS[1]))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.script_schema", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    va = sub.add_parser("validate", help="check a script.json against the writing rules")
    va.add_argument("script")
    va.add_argument("--manifest", help="the Walk's clip_manifest.json (enables clip and range checks)")
    va.add_argument("--style", default=str(DEFAULT_STYLE), help="style.json (default: repo style.json)")
    va.add_argument("--shared-root", dest="shared_root",
                    help="shared root holding the Library (default: the Video folder's root, else CF_SHARED_ROOT)")
    va.add_argument("--footage-root", dest="shared_root", help=argparse.SUPPRESS)
    va.add_argument("--db", help="factory.db for the Library (default: CF_FACTORY_DB, else <shared root>/factory.db)")
    va.add_argument("--no-library", action="store_true", help="do not load the Library (cues then fail)")
    args = ap.parse_args(argv)
    try:
        script = load(args.script)
    except (ScriptError, OSError) as exc:
        print(f"INVALID {args.script}\n- {exc}")
        return 1
    ctx = None
    if has_cues(script) and not args.no_library:
        from cf.assets import context  # noqa: PLC0415

        ctx = context(Path(args.script).expanduser().resolve(),
                      root=Path(args.shared_root).expanduser() if args.shared_root else None,
                      db_path=Path(args.db).expanduser() if args.db else None)
    f = check(script, load_json(args.manifest), load_json(args.style), ctx)
    if f.problems:
        print(f"INVALID {args.script} ({len(f.problems)} violations)")
        for p in f.problems:
            print(f"- {p}")
    else:
        print(f"OK {args.script}: {len(script.shots)} shots, {script.total_s:.2f} s "
              f"(target {script.target_length_s:g} s)")
    for w in f.warnings:
        print(f"- WARN {w}")
    return 1 if f.problems else 0


if __name__ == "__main__":
    sys.exit(main())
