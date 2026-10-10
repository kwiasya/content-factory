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

SCHEMA = "cf-script/1"
FORMATS = ("pov", "listicle", "levels", "day_in_the_life", "reveal", "contrast")
HOOK_TYPES = ("visual_payoff", "pov", "list", "contrast", "question", "curiosity")
ROLES = ("hook", "build", "payoff", "loop")
OVERLAY_TYPES = ("place", "fact", "line")
TRANSITIONS = ("cut", "dissolve", "dip")
ENDINGS = ("loop_match", "reveal_last", "question_overlay")

HOOK_WORDS = (5, 8)
OVERLAY_MAX_WORDS = 8
SHOT_MIN_S = 1.5
SHOT_MAX_S = 5.0
TOTAL_TOLERANCE_S = 3.0
TARGET_MAX_S = 90
MAX_HASHTAGS = 5
EPS = 1e-6

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_STYLE = REPO_ROOT / "style.json"


class ScriptError(ValueError):
    """The file is not a structurally readable Script."""


@dataclass
class Overlay:
    text: str
    type: str


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
    metrics: dict | None = None

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
        overlay = Overlay(text=_str(ov, "text", f"{where}.overlay"), type=_str(ov, "type", f"{where}.overlay"))
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
        metrics=d.get("metrics"),
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
    return len(text.split())


def validate(script: Script, manifest: dict | None = None, style: dict | None = None) -> list[str]:
    """Return the list of rule violations (empty when the Script is valid)."""
    v: list[str] = []
    style = style or {}
    shot_s = (style.get("pacing") or {}).get("shot_s") or {}
    shot_min = float(shot_s.get("min", SHOT_MIN_S))
    payoff_max = max(SHOT_MAX_S, float(shot_s.get("payoff_max", SHOT_MAX_S)))
    min_hold = float((style.get("animation") or {}).get("min_hold_s", 2.0))
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
            if d < min_hold - EPS:
                v.append(f"{w}: overlay holds {d:.2f} s, must hold >= {min_hold:g} s")

    total = script.total_s
    if abs(total - script.target_length_s) > TOTAL_TOLERANCE_S + EPS:
        v.append(f"total: shots add up to {total:.2f} s, target is {script.target_length_s:g} "
                 f"+/- {TOTAL_TOLERANCE_S:g} s")

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
