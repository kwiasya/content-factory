"""Script (cf-script/1) data model, loader and validator for the writing rules.

Field reference and rules: ``docs/script-schema.md``. The validator checks only
what can be checked mechanically; the rest of the writing rules stay with the
writer. Overlay and caption rules apply only when those fields are present
(a first-pass Script may have ``overlay: null`` everywhere and no Track).

CLI::

    python -m cf.script_schema validate <script.json> [--manifest m.json] [--style style.json]

exits 1 and prints one violation per line when the Script breaks a rule.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from cf import frames
from cf import reframe as rf
from cf.reframe import Reframe

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

    @property
    def duration_s(self) -> float:
        """Duration on the timeline (source span divided by speed)."""
        return (self.out_s - self.in_s) / self.speed if self.speed else float("inf")


@dataclass
class Hook:
    type: str
    text: str
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
    return None if d.get(key) is None else _num(d, key, where)


def _str(d: dict, key: str, where: str, required: bool = True) -> str | None:
    v = d.get(key)
    if v is None:
        if required:
            raise ScriptError(f"{where}: missing {key!r}")
        return None
    if not isinstance(v, str):
        raise ScriptError(f"{where}: {key!r} must be a string, got {v!r}")
    return v


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
        overlay = Overlay(text=_str(ov, "text", f"{where}.overlay"), type=_str(ov, "type", f"{where}.overlay"),
                          span=span)
    try:
        reframe = rf.from_shot(d.get("reframe"), f"{where}.reframe")
    except ValueError as exc:
        raise ScriptError(str(exc)) from exc
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
        hook=Hook(type=_str(hook, "type", "hook"), text=_str(hook, "text", "hook"), clip=_str(hook, "clip", "hook")),
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


def overlay_cover(shots: list[Shot]) -> dict[int, int]:
    """Shot index -> index of the earlier shot whose spanning overlay covers it (span > 1 only)."""
    cover: dict[int, int] = {}
    for i, s in enumerate(shots):
        if s.overlay is not None and s.overlay.span > 1:
            for j in range(i + 1, min(i + s.overlay.span, len(shots))):
                cover.setdefault(j, i)
    return cover


def validate(script: Script, manifest: dict | None = None, style: dict | None = None) -> list[str]:
    """Return the list of rule violations (empty when the Script is valid)."""
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
    args = ap.parse_args(argv)
    try:
        script = load(args.script)
    except (ScriptError, OSError) as exc:
        print(f"INVALID {args.script}\n- {exc}")
        return 1
    problems = validate(script, load_json(args.manifest), load_json(args.style))
    if problems:
        print(f"INVALID {args.script} ({len(problems)} violations)")
        for p in problems:
            print(f"- {p}")
        return 1
    print(f"OK {args.script}: {len(script.shots)} shots, {script.total_s:.2f} s "
          f"(target {script.target_length_s:g} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
