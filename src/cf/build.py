"""Build a Reel's timeline in DaVinci Resolve Studio from its script.json.

    python -m cf.build <reel_dir> [--footage <footage_dir>] [--project-name NAME] [--no-stills]
                       [--look <file.cube>|none] [--stills-only [--stills-dir DIR]] [--script FILE]
                       [--no-track] [--ambience-db DB] [--canvas WxH] [--no-superscale]
                       [--deliver sdr|hdr-hlg] [--hlg-normalize cdl|none] [--overlay-nits N]
                       [--grade-drx <dir>] [--hdr-source apple-sdr|resolve]
                       [--shared-root PATH] [--db PATH] [--no-assets]
    python -m cf.build <reel_dir> --overlay-specs [--canvas WxH]

Rules: ``docs/resolve-rules.md``; contract: ``.claude/skills/build-reel/SKILL.md``;
decision to rebuild rather than patch: ``docs/adr/0001-timeline-rebuilt-from-plan.md``.
Every write is read back; the read-back report goes to ``<reel_dir>/build-report.json``
and the exit code is non-zero on any mismatch.

The Look LUT (``style.json`` ``look.lut`` or ``--look``) goes on node 1 of the post-clip
graph of the project's ``cf-look`` color group, and every V1 item joins that group: the
API cannot add a node 2 to a clip (docs/research/look-experiment.md). ``--stills-only``
keeps the existing timeline, (re)applies the Look and exports the stills, without a rebuild.

``--grade-drx <dir>`` re-applies a hand grade saved per shot as DRX (``<shot>.drx`` or the
``<shot>_<n>.<n>.<n>.drx`` that ``GalleryStillAlbum.ExportStills`` writes, e.g.
``reels/reel-01/author-grade/``) with ``ApplyGradeFromDRX`` on every V1 item, after the HLG
CDL and the Look. It replaces each clip's whole grade (node 1 included), so build with the
options the grade was made on: ``<dir>/grade.json`` ``build`` lists them, and a difference
is reported as a note. The group's post-clip Look LUT is not touched by it.

Record frames come from ``<reel_dir>/cuts.json`` when it exists (``beat-grid`` writes it);
otherwise shots are laid back to back, each snapped down to whole timeline frames.
With ``script.track`` set (and no ``--no-track``), the Track WAV goes on A2 "music" from
the timeline start for the picture's length, source in-point ``script.track_in_s`` (default
``intro_end`` from the ``beats.json`` next to the Track), 0 dB, ``track_fade_out_s`` fade
(default 0.6 s); the A1 ambience sits at ``style.audio.ambience_db``. ``cuts.json``
``beat_markers`` become timeline markers (downbeats Blue, other beats Cyan).

HDR source (``--hdr-source``, default ``style.json`` ``color.hdr_source`` = ``apple-sdr``): an
HDR clip (iPhone HLG / Dolby Vision) is imported as its Apple SDR mezzanine
``<footage>/mezz/<stem>.mov`` (``cf.mezz``, ``tools/apple-sdr``: AVFoundation's own HDR -> SDR tone
mapping, what QuickTime and Photos show) tagged ``Rec.709 Gamma 2.4``, which passes through the
timeline unchanged; it gets no HLG CDL (docs/adr/0011-hdr-clips-through-apple-tone-mapping.md).
Its stills are checked against the mezzanine frame (mean luma within ``MEZZ_STILL_TOLERANCE``).
``resolve`` imports the HLG file and lets Resolve convert it (below). ``--deliver hdr-hlg``
always uses ``resolve``. SDR clips are imported as they are either way.

Delivery (``--deliver``): ``sdr`` (default) outputs Rec.709 Gamma 2.4 and puts the HLG
normalization CDL (``--hlg-normalize cdl``, -1.02 stop) on node 1 of every HLG item;
``--hlg-normalize none`` leaves it off (Resolve's own BT.2408 HLG -> 709 conversion, one stop
brighter). ``hdr-hlg`` outputs Rec.2100 HLG for an HDR render (``cf.render --hdr``): no CDL
and no Look unless ``--look`` names one, so the pictures stay as the source HLG; the SDR
overlays are placed at HDR graphics white (``color_settings``, ``HDR_OVERLAY``;
docs/research/hdr-hlg-delivery.md).

Overlays: ``--overlay-specs`` writes one ``overlays/render.mjs`` spec per shot overlay to
``overlays/specs/<shot>.json`` (length = its spanned shots in whole timeline frames; the
overlay's ``preset``, ``anchor`` and ``in_frames``/``out_frames`` pass through) and prints the
render commands, without touching Resolve. The build places ``overlays/<shot>.mov`` on V2.

The project and timeline resolution come from ``--canvas`` (a ``style.json`` ``canvases``
name or WxH, e.g. ``1080x1920`` for a comparison build), else the Script's ``canvas``
(``landscape`` = 3840x2160), else ``style.json`` ``canvas`` (2160x3840); ``cf.canvas.for_reel``. Source clips whose display height
is below the canvas height get Resolve Studio Super Scale (``style.json`` ``upscale``:
plain 2x by default, ``2x-enhanced`` optional; ``cf.canvas.upscale_plan``);
``--no-superscale`` turns it off on every clip. Stills are exported at the canvas size and
downscaled to the proxy size for the luma comparison.

Reframe (``cf.reframe``): a V1 item whose source is wider than the canvas (a landscape clip
on the vertical canvas; on a landscape canvas a 16:9 clip has the canvas aspect and is not reframed) gets the Script's ``reframe`` (default ``style.json`` ``reframe.default``,
``follow``: a static window on the person from ``cf.follow``, computed on the proxies before Resolve
is touched): ``ZoomX``/``ZoomY`` (ganged) so the source height fills the canvas, then ``Pan`` (0
for ``center``/``smart``, the window position for ``pan``/``follow``), each read back. Every still
with more than 8 px of black at an edge fails the build. ``smart`` (opt-in) runs ``SmartReframe()`` and polls
``GetSmartReframeStatus()``. The Smart Reframe keyframes do not show in ``GetProperties()``
(Pan reads 0), so the still is its read-back. ``x_end`` is not animated (no keyframe API).

Asset cues (``shots[].assets``, ``docs/script-schema.md`` Assets): the Library is loaded read-only
(``cf.assets.context``; ``--shared-root`` / ``--db``) only for a Script with cues. Sounds go on A3
"sfx" (A4 when two overlap) at the level of ``plan_cues`` (6 LU under the Track's measured loudness
over the part used, else under the target loudness), pictures on V4 "assets" (V5) from the file
``cf.assets.placement`` picks, with the ``pos`` transform (ZoomX ganged, Pan, Tilt); a meme's sound
shares its cue on an A lane. Every item and value is read back, and each picture cue gets a still
``stills/cue-<cue>.png`` (``--stills-only`` takes the cue plan from the last build-report.json).
``--no-assets`` builds without them (their rules skipped, no Library opened). A cue-less Script
creates the same tracks as before and never opens factory.db. The Pack is only read (Resolve imports by path).
A Video folder (``videos/<slug>/`` with video.json) builds from ``<local root>/<script.footage>`` when
``--footage`` is absent.

The planning part (``plan_shots``, ``overlay_specs``, ``plan_track``, ``beat_marker_plan``, ``append_infos``,
``source_end``, ``plan_reframes``, ``plan_cues``, ``sfx_volume``) is pure and has no Resolve dependency, so it is unit-tested
in ``tests/test_build_plan.py`` and ``tests/test_reframe.py``.
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

from cf import follow as fw
from cf import frames
from cf import hdr as hdr_mod
from cf import mezz as mezz_mod
from cf import reframe as rf
from cf.canvas import Canvas, for_reel, scaled_safe_zone, spec_of, upscale_plan
from cf.script_schema import Script, check, has_cues, load, load_json, manifest_clips, validate

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = REPO_ROOT / "style.json"

# docs/resolve-rules.md "Exact strings". Resolution and fps first. The frame rate can only
# be written at project level while the project has no timelines; the resolution can be
# changed later, and timelines without custom settings follow it (probe, 2026-10-11).
PROJECT_SETTINGS_ORDER = (
    "timelineResolutionWidth", "timelineResolutionHeight", "timelineFrameRate",
    "colorScienceMode", "separateColorSpaceAndGamma", "isAutoColorManage",
    "colorSpaceTimeline", "colorSpaceOutput", "inputDRT", "outputDRT",
    "timelineWorkingLuminanceMode", "useInverseDRT",
)
COLOR_SETTINGS = {
    "colorScienceMode": "davinciYRGBColorManagedv2",
    "separateColorSpaceAndGamma": "0",
    "isAutoColorManage": "0",
    "colorSpaceTimeline": "DaVinci WG/Intermediate",
    "colorSpaceOutput": "Rec.709 Gamma 2.4",
    "inputDRT": "DaVinci",
    "outputDRT": "DaVinci",
    # HDR 1000 working luminance: HLG highlights reach the output DRT unclipped, and the
    # inverse DRT lifts SDR clips into it so they round-trip unchanged
    # (docs/research/color-hlg-experiment.md).
    "timelineWorkingLuminanceMode": "HDR 1000",
    "useInverseDRT": "1",
}
# Node-1 CDL on every HLG item (docs/research/color-hlg-experiment.md). Resolve's
# BT.2408 HLG conversion puts HLG reference white at 203 nits, twice SDR white, so the
# SDR render comes out a stop too bright and flat. Offset -0.0749 in DaVinci
# Intermediate is -1.02 stops (log2(203/100) x 0.07329); Saturation 1.25 makes up for the
# DRT's highlight desaturation. The Look DRX must leave node 1 free for this.
# Look LUT: Resolve only loads LUTs from its LUT folder tree; ours live in a sub-folder.
RESOLVE_LUT_DIR = Path("/Library/Application Support/Blackmagic Design/DaVinci Resolve/LUT")
LUT_SUBDIR = "content-factory"
LOOK_GROUP = "cf-look"
HLG_NORMALIZE_CDL = {"NodeIndex": "1", "Slope": "1 1 1", "Offset": "-0.0749 -0.0749 -0.0749",
                     "Power": "1 1 1", "Saturation": "1.25"}
# Delivery modes (--deliver). hdr-hlg changes only the output side: the same HDR 1000
# working space, the source HLG clips without the CDL, and a Rec.2100 HLG output.
DELIVERIES = ("sdr", "hdr-hlg")
HLG_NORMALIZE_MODES = ("cdl", "none")
# The output string matches the clips' input string: HLG in and out then round-trips through
# the HDR 1000 timeline within 1 code value; 'Rec.2100 HLG' out rolled off the top and sat
# 7 code values low (docs/research/hdr-hlg-delivery.md).
HDR_HLG_SETTINGS = {"colorSpaceOutput": "Rec.2020 HLG ARIB STD-B67"}
# A still of a shot from an Apple SDR mezzanine vs the mezzanine frame, both at the proxy size:
# Resolve passes Rec.709 Gamma 2.4 through unchanged, so more than this is a colour change.
MEZZ_STILL_TOLERANCE = 3.0


def color_settings(deliver: str = "sdr") -> dict[str, str]:
    """Project color settings for a delivery mode (written in PROJECT_SETTINGS_ORDER)."""
    if deliver not in DELIVERIES:
        raise ValueError(f"deliver must be one of {DELIVERIES}, got {deliver!r}")
    return {**COLOR_SETTINGS, **(HDR_HLG_SETTINGS if deliver == "hdr-hlg" else {})}


def hlg_cdl(deliver: str = "sdr", hlg_normalize: str = "cdl") -> dict | None:
    """The node-1 CDL for HLG items, or None: only an SDR delivery with ``cdl`` gets it."""
    if hlg_normalize not in HLG_NORMALIZE_MODES:
        raise ValueError(f"hlg_normalize must be one of {HLG_NORMALIZE_MODES}, got {hlg_normalize!r}")
    if deliver == "hdr-hlg" or hlg_normalize == "none":
        return None
    return HLG_NORMALIZE_CDL


TRANSITION_TYPES = {"dissolve": "Cross Dissolve", "dip": "Dip To Color Dissolve"}
# Shot markers by role; Blue is kept for downbeat markers, Cyan for the other beats.
ROLE_MARKER_COLOR = {"hook": "Red", "build": "Green", "payoff": "Yellow", "loop": "Purple"}
DOWNBEAT_MARKER_COLOR = "Blue"
BEAT_MARKER_COLOR = "Cyan"
VIDEO_TRACK_NAMES = {1: "shots", 2: "overlays", 3: "overlays 2"}
AUDIO_TRACK_NAMES = {1: "ambience", 2: "music"}
DEFAULT_TRACK_FADE_OUT_S = 0.6
SMART_REFRAME_TIMEOUT_S = 600
SMART_REFRAME_DONE = ("Complete", "Failed", "Cancelled")
BLACK_BAND_TOLERANCE_PX = 8  # rows/columns of pure black at any edge of any still before the build fails


class BuildError(RuntimeError):
    pass


# -- pure planning ---------------------------------------------------------------
@dataclass
class PlannedShot:
    id: str
    clip: str
    path: str
    role: str
    speed: float
    transition: str
    overlay_text: str | None
    clip_fps: float
    record_offset: int          # timeline frames from the timeline start
    record_frame: int           # absolute (timeline start + offset)
    duration: int               # timeline frames
    src_start: int              # source frame at the clip's own fps
    src_end: float              # exclusive; the range appended at 100 % speed
    src_end_after_speed: float  # exclusive; the source range once SetSpeed applies
    fade_in: int = 0
    fade_out: int = 0
    overlay_span: int = 1       # shots the overlay covers, this one first (script overlay.span)
    overlay_frames: int = 0     # V2 length: from this shot's record frame to the end of the last spanned shot

    @property
    def record_end(self) -> int:
        return self.record_frame + self.duration


def _frac(x: float) -> Fraction:
    return Fraction(x).limit_denominator(1001)


def source_end(src_start: int, duration: int, clip_fps: float, timeline_fps: float, speed: float = 1.0) -> float:
    """Exclusive ``endFrame`` that makes Resolve lay exactly ``duration`` timeline frames.

    Resolve converts the source span to timeline frames with
    ``floor((endFrame - startFrame) * timeline_fps / clip_fps)`` and accepts a float
    ``endFrame``. An exact integer span stays an int; a fractional one gets +0.001 so
    float error cannot floor it one frame short.
    """
    span = Fraction(duration) * _frac(speed) * frames.exact_fps(clip_fps) / frames.exact_fps(timeline_fps)
    if span.denominator == 1:
        return src_start + int(span)
    return round(src_start + float(span) + 0.001, 4)


# FRAME_EPS, snap_frames and the source-frame model live in cf.frames (shared with the validator).
FRAME_EPS = frames.FRAME_EPS
snap_frames = frames.snap_frames


def plan_shots(script: Script, manifest: dict, start_frame: int, fps: float = 30,
               cuts: dict | None = None, clip_fps: dict[str, float] | None = None,
               raw_dir: str | Path | None = None) -> tuple[list[PlannedShot], list[str]]:
    """Turn a Script (+ optional cuts.json) into timeline positions and source ranges.

    Record positions come from ``cuts.json`` when given (its ``fps`` must equal the
    timeline's). Otherwise the shots are laid back to back: each shot's timeline
    duration is snapped DOWN to whole frames (shorten, never extend past ``out_s``),
    and the next shot starts at the previous record frame plus that snapped duration.
    The source in-point is the first whole source frame at or after ``in_s`` (or the
    cut's ``src_in_s``). Source frames are at each clip's own fps: ``clip_fps``
    (Resolve's ``FPS`` clip property) wins over the manifest, because Resolve reads
    59.94 fps iPhone clips as 60.
    """
    clips = manifest_clips(manifest)
    notes: list[str] = []
    cut_by_id: dict[str, dict] = {}
    if cuts is not None:
        cfps_cuts = cuts.get("fps")
        if cfps_cuts is not None and abs(float(cfps_cuts) - float(fps)) > 1e-6:
            raise BuildError(f"cuts.json is at {cfps_cuts} fps, the timeline at {fps:g}")
        cut_by_id = {c["id"]: c for c in cuts.get("shots", [])}
        missing = [s.id for s in script.shots if s.id not in cut_by_id]
        if missing:
            raise BuildError(f"cuts.json has no entry for shots {missing}")
        extra = sorted(set(cut_by_id) - {s.id for s in script.shots})
        if extra:
            notes.append(f"cuts.json has entries for shots not in the script: {extra}")
        notes.append("record offsets and durations from cuts.json")
    else:
        notes.append("no cuts.json: shots laid back to back from in_s/out_s at "
                     f"{fps:g} fps, each snapped down to whole frames")
    out: list[PlannedShot] = []
    next_off = 0
    for s in script.shots:
        c = clips.get(s.clip)
        if c is None:
            raise BuildError(f"shot {s.id}: clip {s.clip!r} not in the manifest")
        cfps = float((clip_fps or {}).get(s.clip) or c["fps"])
        cut = cut_by_id.get(s.id)
        in_s = float(cut["src_in_s"]) if cut is not None and cut.get("src_in_s") is not None else s.in_s
        out_s = float(cut["src_out_s"]) if cut is not None and cut.get("src_out_s") is not None else s.out_s
        if cut is not None and abs(in_s - s.in_s) > 1.0 / cfps + 1e-6:
            notes.append(f"{s.id}: cuts.json src_in_s {in_s:g} differs from the script's in_s {s.in_s:g}")
        src_start = frames.first_frame(in_s, cfps)
        fit = frames.shot_frames(in_s, out_s, s.speed, cfps, fps)
        if cut is not None:
            off = int(cut["record_frame_offset"])
            dur = int(cut["duration_frames"])
            if dur > fit:
                notes.append(f"{s.id}: cuts.json asks {dur} frames, {dur - fit} more than "
                             f"{in_s:g}-{out_s:g} s holds; the source runs past out_s")
        else:
            off, dur = next_off, fit
        next_off = off + dur
        path = str(Path(raw_dir) / s.clip) if raw_dir else c.get("path") or s.clip
        out.append(PlannedShot(
            id=s.id, clip=s.clip, path=path, role=s.role, speed=s.speed, transition=s.transition,
            overlay_text=s.overlay.text if s.overlay else None, clip_fps=cfps,
            record_offset=off, record_frame=start_frame + off, duration=dur, src_start=src_start,
            src_end=source_end(src_start, dur, cfps, fps),
            src_end_after_speed=source_end(src_start, dur, cfps, fps, s.speed),
            fade_in=round(s.fade_in_s * fps), fade_out=round(s.fade_out_s * fps),
        ))
        nb = c.get("nb_frames")
        if nb and out[-1].src_end_after_speed > int(nb) + 1:
            notes.append(f"{s.id}: source range ends at {out[-1].src_end_after_speed:g}, "
                         f"past the clip's {nb} frames")
    for a, b in zip(out, out[1:]):
        if b.record_offset < a.record_offset + a.duration:
            raise BuildError(f"shots {a.id} and {b.id} overlap on V1")
    for i, (s, p) in enumerate(zip(script.shots, out)):
        if s.overlay is None:
            continue
        span = max(1, int(s.overlay.span))
        last = min(i + span, len(out)) - 1
        if i + span > len(out):
            notes.append(f"{p.id}: overlay span {span} runs past the last shot; it ends with {out[last].id}")
        p.overlay_span = last - i + 1
        p.overlay_frames = out[last].record_end - p.record_frame
    if script.ending == "loop_seamless" and len(out) > 1:
        first, last = out[0], out[-1]
        if first.clip == last.clip and abs(first.speed - 1) < 1e-9 and abs(last.speed - 1) < 1e-9:
            # The seam is derived from frames: the run-up starts where its next frame is the
            # hook's first one, as Resolve places source frames (cf.frames; at 29.97 on 30 this
            # is one source frame later than the seconds say).
            want = frames.run_up_start(first.src_start, last.duration, last.clip_fps, fps)
            if want != last.src_start:
                notes.append(f"{last.id}: in-point source frame {last.src_start} -> {want}, so its next frame is "
                             f"{first.id}'s first ({first.src_start}) at {last.clip_fps:g} fps on {fps:g}")
                last.src_start = want
                last.src_end = source_end(want, last.duration, last.clip_fps, fps)
                last.src_end_after_speed = last.src_end
    return out, notes


def overlay_specs(script: Script, shots: list[PlannedShot], fps: float, style_path: str | Path,
                  canvas: str | None = None) -> dict[str, dict]:
    """One ``overlays/render.mjs`` spec per shot overlay, keyed by shot id (file ``overlays/<id>.mov``).

    ``duration_s`` is the overlay's planned length (its spanned shots) in whole timeline frames.
    A ``line`` overlay on the first shot that carries the hook text renders as ``type: hook``.
    The overlay's ``preset`` (else style.json ``typography.preset``), ``anchor`` (slot name or
    explicit ``{anchor, x, y, align}`` in reference px), ``in_frames``/``out_frames`` and
    ``canvas`` (the canvas spec, e.g. ``landscape``) are written only when set.
    """
    out: dict[str, dict] = {}
    for i, (s, p) in enumerate(zip(script.shots, shots)):
        o = s.overlay
        if o is None:
            continue
        is_hook = i == 0 and script.hook.text is not None and o.text.strip() == script.hook.text.strip()
        spec: dict[str, Any] = {"text": o.text, "type": "hook" if is_hook else o.type,
                                "duration_s": round((p.overlay_frames or p.duration) / fps, 6),
                                "style_path": str(style_path)}
        for k in ("preset", "anchor", "in_frames", "out_frames"):
            if getattr(o, k) is not None:
                spec[k] = getattr(o, k)
        if canvas:
            spec["canvas"] = canvas
        out[p.id] = spec
    return out


def write_overlay_specs(reel_dir: Path, footage_dir: Path, script_path: Path, canvas: str | None = None) -> int:
    """``--overlay-specs``: write ``overlays/specs/<shot>.json`` and print the render commands."""
    style = load_json(STYLE_PATH)
    manifest = load_json(footage_dir / "clip_manifest.json")
    script = load(script_path)
    problems = validate(script, manifest, style)
    if problems:
        print("script.json does not validate:\n- " + "\n- ".join(problems), file=sys.stderr)
        return 1
    cuts_path = reel_dir / "cuts.json"
    cuts = load_json(cuts_path) if cuts_path.exists() else None
    cv = for_reel(style, script.canvas, canvas)
    # Durations from the manifest fps; the build re-checks every overlay's frames against Resolve's plan.
    shots, _ = plan_shots(script, manifest, 0, cv.fps, cuts)
    specs = overlay_specs(script, shots, cv.fps, STYLE_PATH, spec_of(canvas, script.canvas))
    spec_dir = reel_dir / "overlays" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    renderer = REPO_ROOT / "overlays" / "render.mjs"
    for sid, spec in specs.items():
        f = spec_dir / f"{sid}.json"
        f.write_text(json.dumps(spec, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"node {renderer} --spec {f} --out {reel_dir / 'overlays' / f'{sid}.mov'}")
    print(f"{len(specs)} spec(s) in {spec_dir}", file=sys.stderr)
    return 0


def loop_seam(shots: list[PlannedShot], fps: float = 30) -> dict:
    """The seam of a ``loop_seamless`` Reel in source frames of the shared clip (cf.frames model).

    ``gap_frames`` = the first shot's first source frame minus the frame the last shot would show
    one timeline frame after its end: 0 is seamless, 1 skips a frame, -1 repeats one.
    """
    first, last = shots[0], shots[-1]
    nxt = frames.next_frame(last.src_start, last.duration, last.clip_fps, fps)
    gap = first.src_start - nxt
    return {"clip": first.clip, "same_clip": first.clip == last.clip, "last_src_start": last.src_start,
            "last_frames": last.duration,
            "last_shown_frame": frames.shown(last.src_start, last.duration - 1, last.clip_fps, fps),
            "next_frame": nxt, "first_src_start": first.src_start, "gap_frames": gap,
            "ok": first.clip == last.clip and gap == 0}


def append_infos(shots: list[PlannedShot], items: dict[str, Any], media_type: int,
                 track_index: int = 1) -> list[dict]:
    """``AppendToTimeline`` clip infos: source frames at clip fps, exclusive end, absolute record."""
    return [{"mediaPoolItem": items.get(s.clip, s.clip), "startFrame": s.src_start, "endFrame": s.src_end,
             "mediaType": media_type, "trackIndex": track_index, "recordFrame": s.record_frame}
            for s in shots]


def effective_reframes(script: Script, manifest: dict, canvas_w: int, canvas_h: int,
                       default_mode: str = rf.DEFAULT_MODE) -> dict[str, tuple[rf.Reframe | None, bool]]:
    """Shot id -> (the reframe it gets, whether it is the default)."""
    clips = manifest_clips(manifest)
    return {s.id: rf.effective(s.reframe, clips.get(s.clip), canvas_w, canvas_h, default_mode) for s in script.shots}


def follow_groups(script: Script, eff: dict[str, tuple[rf.Reframe | None, bool]]) -> list[list[str]]:
    """Shots that share ONE follow window: each follow shot alone, except the loop seam.

    With ``ending: loop_seamless`` and the first and last shot both ``follow`` on the same clip
    at the same zoom, the two are one group (one window over the union of both ranges), so the
    picture does not jump at the seam.
    """
    ids = [s.id for s in script.shots if (eff[s.id][0] is not None and eff[s.id][0].mode == "follow")]
    groups = [[i] for i in ids]
    first, last = script.shots[0], script.shots[-1]
    if (script.ending == "loop_seamless" and len(script.shots) > 1 and first.id in ids and last.id in ids
            and first.clip == last.clip and abs(eff[first.id][0].zoom - eff[last.id][0].zoom) < 1e-9):
        groups = [g for g in groups if g[0] not in (first.id, last.id)] + [[last.id, first.id]]
    return groups


def plan_reframes(script: Script, manifest: dict, canvas_w: int, canvas_h: int,
                  mismatch: str = "scaleToFit", default_mode: str = rf.DEFAULT_MODE,
                  follow_x: dict[str, float] | None = None) -> dict[str, rf.ReframePlan | None]:
    """Shot id -> the reframe cf.build writes (None: the item keeps Resolve's fit).

    A shot's ``reframe`` wins; without one, a clip wider than the canvas gets ``default_mode``
    (``style.json`` ``reframe.default``, ``follow``). A ``follow`` shot takes its window position
    from ``follow_x`` (``cf.follow``). The source size is the manifest's display size.
    ``mismatch`` is the timeline's ``timelineInputResMismatchBehavior``.
    """
    clips = manifest_clips(manifest)
    eff = effective_reframes(script, manifest, canvas_w, canvas_h, default_mode)
    out: dict[str, rf.ReframePlan | None] = {}
    for s in script.shots:
        c = clips.get(s.clip)
        want, is_default = eff[s.id]
        if want is None:
            out[s.id] = None
            continue
        if want.mode == "follow":
            if s.id not in (follow_x or {}):
                raise BuildError(f"shot {s.id}: follow needs a window from cf.follow (no person analysis ran)")
            want = rf.Reframe("follow", x=float(follow_x[s.id]), zoom=want.zoom)
        w, h = rf.display_size(c)
        if not w or not h:
            raise BuildError(f"shot {s.id}: reframe needs the clip's size, the manifest has none for {s.clip}")
        try:
            out[s.id] = rf.plan_reframe(want, w, h, canvas_w, canvas_h, mismatch, default=is_default)
        except ValueError as exc:
            raise BuildError(f"shot {s.id}: {exc}") from exc
    return out


@dataclass
class PlannedTrack:
    path: str
    in_s: float                 # what was asked (Script track_in_s, or beats.json intro_end)
    in_source: str              # where in_s came from
    src_start: int              # source frame at timeline fps (Resolve reads a WAV at the project fps)
    src_end: int                # exclusive
    record_frame: int           # absolute; the timeline start
    duration: int               # timeline frames = the picture's length
    fade_out: int               # frames


def plan_track(script: Script, reel_dir: str | Path, start_frame: int, duration: int, fps: float = 30,
               beats: dict | None = None, default_fade_out_s: float = 0.6) -> tuple[PlannedTrack, list[str]]:
    """Where the Track goes: A2 from the timeline start, for the picture's duration.

    The source in-point is ``script.track_in_s``, else ``beats.json`` ``intro_end``, else 0.
    Resolve reads a WAV at the project frame rate and rounds a fractional ``startFrame``
    (smoke, 2026-10-10: 63.6 became 64), so the in-point is snapped to a whole frame here
    and the snap is reported.
    """
    notes: list[str] = []
    if not script.track:
        raise BuildError("the script has no track")
    path = Path(script.track).expanduser()
    if not path.is_absolute():
        path = Path(reel_dir) / path
    if script.track_in_s is not None:
        in_s, source = float(script.track_in_s), "script track_in_s"
    elif beats and beats.get("intro_end") is not None:
        in_s, source = float(beats["intro_end"]), "beats.json intro_end"
    else:
        in_s, source = 0.0, "default 0 (no track_in_s, no beats.json intro_end)"
        notes.append("Track starts at 0 s: no track_in_s in the script and no intro_end in beats.json")
    src_start = round(in_s * fps)
    if abs(src_start / fps - in_s) > 1e-6:
        notes.append(f"Track in-point {in_s:g} s snapped to frame {src_start} ({src_start / fps:.4f} s)")
    fade_s = script.track_fade_out_s if script.track_fade_out_s is not None else default_fade_out_s
    fade = min(round(fade_s * fps), duration)
    if beats and beats.get("duration_s") and (src_start + duration) / fps > float(beats["duration_s"]) + 1e-6:
        raise BuildError(f"Track too short: needs {(src_start + duration) / fps:.2f} s, has {beats['duration_s']} s")
    return PlannedTrack(path=str(path), in_s=in_s, in_source=source, src_start=src_start,
                        src_end=src_start + duration, record_frame=start_frame, duration=duration,
                        fade_out=fade), notes


@dataclass
class PlannedCue:
    cue: str                    # "s03.1": shot id + 1-based cue index; a meme's picture and sound share it
    shot: str
    ref: str                    # as written
    canonical: str
    asset_id: str
    category: str
    lane: str                   # "A3" | "A4" | "V4" | "V5"
    track_type: str             # "audio" | "video"
    track_index: int
    media_type: int             # 2 audio, 1 video
    path: str                   # absolute file to import
    variant: str                # original | alpha | keyed | converted | png | still
    file_fps: float | None
    record_offset: int          # timeline frames from the timeline start
    record_frame: int           # absolute
    duration: int               # timeline frames
    src_start: int
    src_end: float              # exclusive
    volume_db: float | None = None
    level: dict | None = None
    transform: dict | None = None

    @property
    def record_end(self) -> int:
        return self.record_frame + self.duration


def reference_level(style: dict, track_lufs: float | None) -> tuple[float, str]:
    """What a sound cue's level is set against: the placed Track's loudness, else the target loudness."""
    if track_lufs is not None:
        return float(track_lufs), "track"
    return float((style.get("audio") or {}).get("target_lufs", -14)), "style.audio.target_lufs"


def sfx_volume(reference_lufs: float, loudness: dict, cue_db: float | None, style: dict) -> dict:
    """AudioVolume of a sound cue: ``below_track_db`` under the reference, plus the cue's ``db``, capped by the
    true peak and clamped to ``gain_range_db``."""
    from cf import assets as ca  # noqa: PLC0415

    cfg = ca.settings(style)
    below = float(cfg["sfx_below_track_db"])
    lo, hi = (float(x) for x in cfg["gain_range_db"])
    peak = float((style.get("audio") or {}).get("true_peak_dbtp", -1))
    raw = reference_lufs + below - float(loudness["i"]) + float(cue_db or 0)
    tp = loudness.get("tp")
    vol, capped = raw, None
    if ca.finite(tp) and peak - float(tp) < vol:
        vol, capped = peak - float(tp), "true_peak"
    if vol > hi or vol < lo:
        vol, capped = min(max(vol, lo), hi), "range"
    return {"reference_lufs": reference_lufs, "below_track_db": below, "asset_lufs": loudness["i"],
            "asset_tp": tp, "method": loudness.get("method"), "cue_db": cue_db, "raw_db": round(raw, 2),
            "volume_db": round(vol, 1) + 0.0, "capped": capped}


def plan_cues(script: Script, shots: list[PlannedShot], library: Any, *, fps: float, canvas: Canvas,
              style: dict, reference_lufs: float, reference_source: str, mismatch: str = "scaleToFit",
              file_fps: dict[str, float] | None = None) -> tuple[list[PlannedCue], list[str]]:
    """Asset cues at absolute record frames from their shot's planned record frame, on A3/A4 and V4/V5."""
    from cf import assets as ca  # noqa: PLC0415

    todo = [(s, p, k, c) for s, p in zip(script.shots, shots) for k, c in enumerate(s.assets)]
    if not todo:
        return [], []
    if library is None:
        raise BuildError(f"{len(todo)} Asset cue(s) need the Library, and none could be loaded")
    cfg = ca.settings(style)
    notes: list[str] = []
    out: list[PlannedCue] = []
    end = shots[-1].record_end
    clear = round(float(cfg["loop_clear_s"]) * fps)
    for s, p, k, c in todo:
        cue = f"{s.id}.{k + 1}"
        try:
            a = ca.lookup(library, c.ref)
        except ca.BadRef as exc:
            raise BuildError(f"cue {cue}: {c.ref!r} is not an Asset ref") from exc
        if a is None:
            raise BuildError(f"cue {cue}: no Asset {c.ref}")
        kind = ca.lane_kind(a)
        if kind is None:
            raise BuildError(f"cue {cue}: {a.ref} is a {a.category} Asset, not placeable")
        place = ca.placement(a)
        if place.problem or place.path is None:
            raise BuildError(f"cue {cue} ({c.ref}): {place.problem}")
        if place.note:
            notes.append(f"cue {cue} ({c.ref}): {place.note}")
        dur_s = c.dur_s if c.dur_s is not None else ca.default_dur_s(a, place, style)
        at, duration = frames.cue_frames(c.at_s, dur_s or 0.0, fps)
        if duration < 1:
            raise BuildError(f"cue {cue} ({c.ref}): {dur_s!r} s is shorter than one frame")
        start = p.record_frame - p.record_offset
        offset = p.record_offset + at
        if offset + start + duration > end:
            raise BuildError(f"cue {cue} ({c.ref}): ends at +{offset + duration}, past the end of the Reel "
                             f"(+{end - start})")
        path = str(place.path)
        ffps = float((file_fps or {}).get(path) or place.fps or 0) or None
        src_end: float = duration if place.still or ffps is None else source_end(0, duration, ffps, fps)
        common = dict(cue=cue, shot=s.id, ref=c.ref, canonical=a.ref, asset_id=a.id, category=a.category,
                      path=path, variant=place.role, file_fps=None if place.still else ffps,
                      record_offset=offset, record_frame=start + offset, duration=duration, src_start=0)
        if kind == "video":
            pos = c.pos or cfg["default_pos"].get(a.category) or "center"
            if not (place.width and place.height):
                raise BuildError(f"cue {cue} ({c.ref}): the placed file's size is unknown")
            tr = ca.transform(place.width, place.height, ca.pos_box(style, canvas, pos), canvas.width,
                              canvas.height, mismatch)
            out.append(PlannedCue(lane="", track_type="video", track_index=0, media_type=1, src_end=src_end,
                                  transform={"pos": pos, **tr}, **common))
            if script.ending == "loop_seamless" and start + offset + duration > end - clear:
                notes.append(f"cue {cue} ({c.ref}): on screen within {clear} frames of the loop seam "
                             f"(ends at +{offset + duration} of +{end - start})")
        if ca.has_sound(a, place):
            level = {**sfx_volume(reference_lufs, ca.loudness(a), c.db, style), "reference_source": reference_source}
            if level["capped"]:
                notes.append(f"cue {cue} ({c.ref}): level {level['raw_db']:g} dB capped by "
                             f"{level['capped'].replace('_', ' ')} to {level['volume_db']:g} dB")
            if level.get("method") == "padded":
                notes.append(f"cue {cue} ({c.ref}): loudness measured padded (a very short sound reads lower "
                             "than it feels); adjust with db if it is too loud")
            out.append(PlannedCue(lane="", track_type="audio", track_index=0, media_type=2,
                                  src_end=src_end if kind == "video" else duration, volume_db=level["volume_db"],
                                  level=level, **common))
    for track_type, lanes in ca.CUE_TRACKS.items():
        free_at = {idx: None for idx in lanes}
        for c in sorted((c for c in out if c.track_type == track_type), key=lambda c: (c.record_frame, c.cue)):
            idx = next((i for i in lanes if free_at[i] is None or free_at[i] <= c.record_frame), None)
            if idx is None:
                raise BuildError(f"cue {c.cue} ({c.ref}): a third {track_type} cue at once at +{c.record_offset} "
                                 f"(at most {len(lanes)})")
            free_at[idx] = c.record_end
            c.track_index = idx
            c.lane = f"{track_type[0].upper()}{idx}"
    return out, notes


def cue_plan_from_report(report: dict) -> list[PlannedCue]:
    """The cue plan a build wrote to build-report.json (``cue_plan``); [] when absent or unreadable."""
    try:
        return [PlannedCue(**row) for row in report.get("cue_plan") or []]
    except TypeError:
        return []


def cue_tracks(cues: list[PlannedCue], base_audio: int = 1) -> dict[str, int]:
    """Track counts once the cues are placed (V1–V3 always exist; A1, plus A2 with a Track)."""
    v = max([len(VIDEO_TRACK_NAMES), *(c.track_index for c in cues if c.track_type == "video")])
    a = max([base_audio, *(c.track_index for c in cues if c.track_type == "audio")])
    return {"video": v, "audio": a}


def cue_append_infos(cues: list[PlannedCue], items: dict[str, Any]) -> list[dict]:
    return [{"mediaPoolItem": items.get(c.path, c.path), "startFrame": c.src_start, "endFrame": c.src_end,
             "mediaType": c.media_type, "trackIndex": c.track_index, "recordFrame": c.record_frame} for c in cues]


def default_footage_dir(reel_dir: Path, script: Script) -> Path:
    """The Footage of a legacy ``<footage>/reels/<reel>/``; of a Video folder ``<F>/videos/<slug>/``, ``<F>/<footage>``."""
    reel_dir = Path(reel_dir)
    if reel_dir.parent.name != "reels" and (reel_dir / "video.json").is_file():
        return reel_dir.parent.parent / script.footage
    return reel_dir.parent.parent


def measure_track_lufs(path: str | Path, in_s: float, dur_s: float) -> float:
    """Integrated loudness of the part of the Track the Reel uses (ffmpeg loudnorm, first pass)."""
    import subprocess  # noqa: PLC0415

    from cf.render_check import FFMPEG, parse_loudnorm  # noqa: PLC0415

    res = subprocess.run([FFMPEG, "-hide_banner", "-nostdin", "-ss", f"{in_s:.3f}", "-t", f"{dur_s:.3f}", "-i",
                          str(path), "-af", "loudnorm=print_format=json", "-f", "null", "-"],
                         capture_output=True, text=True, check=False)
    data = parse_loudnorm(res.stderr)
    return float(data["input_i"])


def beat_marker_plan(cuts: dict | None, duration: int) -> list[dict]:
    """``cuts.json`` ``beat_markers`` inside [0, duration): ``{frame, downbeat, beat_index}``."""
    out = []
    for m in (cuts or {}).get("beat_markers", []):
        f = int(m["frame"])
        if 0 <= f < duration:
            out.append({"frame": f, "downbeat": bool(m.get("downbeat")), "beat_index": m.get("beat_index"),
                        "t": m.get("t")})
    return out


def file_frames(path: str | Path) -> int | None:
    """Video frame count of a file from ffprobe (``nb_frames``), or None."""
    import subprocess  # noqa: PLC0415

    res = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True, check=False)
    try:
        return int(res.stdout.strip().split(",")[0])
    except ValueError:
        return None


def timecode(frame: int, fps: int) -> str:
    """Absolute frame -> non-drop timecode HH:MM:SS:FF."""
    ff = frame % fps
    s = frame // fps
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{ff:02d}"


def luma_stats(rgb: Any) -> dict:
    """Mean Rec.709 luma (0-255) and % of pixels with luma >= 235 of an 8-bit RGB array."""
    import numpy as np  # noqa: PLC0415

    a = np.asarray(rgb, dtype=np.float64)
    y = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return {"mean_luma": round(float(y.mean()), 1), "pct_ge_235": round(float((y >= 235).mean() * 100), 2)}


def still_stats(path: Path, compare_size: tuple[int, int] | None = None) -> dict:
    """Size of a still, its luma stats, and (with ``compare_size`` = proxy (w, h)) the stats
    of the still downscaled to that size (area average), which is what is compared with the
    proxy frame: a 2160x3840 still and a 540x960 proxy are then measured on the same grid."""
    import cv2  # noqa: PLC0415

    bgr = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if bgr is None:
        return {}
    h, w = bgr.shape[:2]
    out = {"width": w, "height": h, **luma_stats(bgr[..., ::-1])}
    if compare_size and (w, h) != tuple(compare_size):
        small = cv2.resize(bgr, tuple(compare_size), interpolation=cv2.INTER_AREA)
        out["at_proxy_size"] = {"width": compare_size[0], "height": compare_size[1], **luma_stats(small[..., ::-1])}
    return out


def proxy_frame(proxy: Path, t: float) -> Any:
    """The proxy frame at source time ``t`` as an RGB uint8 array, or None."""
    import subprocess  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    res = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", str(proxy), "-frames:v", "1",
                          "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=False)
    if res.returncode or not res.stdout:
        return None
    probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                            "stream=width,height", "-of", "csv=p=0", str(proxy)], capture_output=True, text=True)
    try:
        # First line only: for a proxy with a data stream (DJI) ffprobe prints the stream twice.
        w, h = (int(x) for x in probe.stdout.strip().splitlines()[0].split(",")[:2])
        return np.frombuffer(res.stdout, np.uint8).reshape(h, w, 3)
    except ValueError:
        return None


def scaled_frame(src: Path, t: float, size: tuple[int, int]) -> Any:
    """The frame of ``src`` at time ``t`` (ffmpeg, rotation applied), area-scaled to ``size``
    = (w, h), as an RGB uint8 array, or None. Used for the Apple SDR mezzanine, on the proxy grid."""
    import subprocess  # noqa: PLC0415

    import numpy as np  # noqa: PLC0415

    w, h = size
    res = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.4f}", "-i", str(src), "-frames:v", "1",
                          "-vf", f"scale={w}:{h}:flags=area", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
                         capture_output=True, check=False)
    if res.returncode or len(res.stdout) != w * h * 3:
        return None
    return np.frombuffer(res.stdout, np.uint8).reshape(h, w, 3)


def proxy_frame_stats(proxy: Path, t: float, frame: Any = None, crop: tuple[float, float] | None = None) -> dict | None:
    """Luma stats of the proxy frame at source time ``t`` (the proxies are the tone-map reference).

    ``crop`` = (left, width) as fractions of the frame width: the stats of that column band,
    i.e. of the reframe window, so a reframed still is compared with what it shows.
    """
    rgb = frame if frame is not None else proxy_frame(proxy, t)
    if rgb is None:
        return None
    h, w = rgb.shape[:2]
    out = {"time_s": round(t, 3), "width": w, "height": h}
    if crop is not None:
        x0 = max(0, min(w - 1, round(crop[0] * w)))
        x1 = max(x0 + 1, min(w, round((crop[0] + crop[1]) * w)))
        rgb = rgb[:, x0:x1]
        out.update(width=x1 - x0, crop_px=[x0, x1], full_width=w)
    return {**out, **luma_stats(rgb)}


def black_band(bgr: Any, level: float = 2.0) -> dict:
    """Rows/columns of pure black at each edge of a still (Resolve fills uncovered canvas with 0)."""
    import numpy as np  # noqa: PLC0415

    a = np.asarray(bgr)
    g = a.max(axis=2) if a.ndim == 3 else a
    rows = g.max(axis=1) <= level
    cols = g.max(axis=0) <= level

    def run(mask: Any) -> int:
        n = 0
        for v in mask:
            if not v:
                break
            n += 1
        return n

    return {"top": run(rows), "bottom": run(rows[::-1]), "left": run(cols), "right": run(cols[::-1])}


def find_window(still_bgr: Any, proxy_rgb: Any, plan: rf.ReframePlan, src_w: int, src_h: int) -> dict:
    """Where a reframed still sits in the source: template match of the still on the proxy frame.

    The still is scaled to the proxy grid and its middle 60 % of rows (clear of any Smart
    Reframe black band) is matched (normalized cross-correlation, so gain and offset do not
    matter). Returns the window's left and top edges in source px, the position as ``x``
    (-1..1, the Script's scale), the vertical offset from centre and the match score.
    """
    import cv2  # noqa: PLC0415

    ph, pw = proxy_rgb.shape[:2]
    k = (pw / src_w) * (1.0 / plan.scale)  # proxy px per canvas px
    cw, ch = still_bgr.shape[1], still_bgr.shape[0]
    tw, th = max(8, round(cw * k)), max(8, round(ch * k))
    small = cv2.cvtColor(cv2.resize(still_bgr, (tw, th), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    r0, r1 = round(th * 0.2), round(th * 0.8)
    tpl = small[r0:r1]
    ref = cv2.cvtColor(proxy_rgb, cv2.COLOR_RGB2GRAY)
    if tpl.shape[0] > ref.shape[0] or tpl.shape[1] > ref.shape[1]:
        return {"error": f"template {tpl.shape} larger than proxy {ref.shape}"}
    res = cv2.matchTemplate(ref, tpl, cv2.TM_CCOEFF_NORMED)
    _, score, _, (mx, my) = cv2.minMaxLoc(res)
    sx, sy = src_w / pw, src_h / ph
    x0, y0 = mx * sx, (my - r0) * sy
    c = (src_w - plan.window_w) / 2
    return {"x0_src": round(x0, 1), "y0_src": round(y0, 1), "score": round(float(score), 3),
            "x": round((x0 - c) / c, 3) if c > 0 else 0.0,
            "tilt_src": round(y0 - (src_h - plan.window_h) / 2, 1),
            # 3 % of the width: overlays and the Look on the still disturb the match by ~1 %; a wrong Pan
            # sign or unit is off by hundreds of px. The exact Pan is checked by read-back.
            "tolerance_src": round(max(4 * sx, 0.03 * src_w), 1)}


# -- report ----------------------------------------------------------------------
@dataclass
class Report:
    reel: str
    footage: str
    project: str
    started: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    notes: list[str] = field(default_factory=list)
    settings: list[dict] = field(default_factory=list)
    media: list[dict] = field(default_factory=list)
    timeline: dict = field(default_factory=dict)
    shots: list[dict] = field(default_factory=list)
    audio: list[dict] = field(default_factory=list)
    writes: list[dict] = field(default_factory=list)
    canvas: dict = field(default_factory=dict)
    upscale: list[dict] = field(default_factory=list)
    reframe: list[dict] = field(default_factory=list)
    overlays: dict = field(default_factory=dict)
    assets: dict = field(default_factory=dict)
    look: dict = field(default_factory=dict)
    stills: list[dict] = field(default_factory=list)
    sources: dict = field(default_factory=dict)
    mismatches: list[str] = field(default_factory=list)
    error: str | None = None

    def check(self, what: str, expected: Any, actual: Any, ok: bool | None = None) -> bool:
        ok = (expected == actual) if ok is None else ok
        self.writes.append({"what": what, "expected": expected, "actual": actual, "ok": ok})
        if not ok:
            self.mismatches.append(f"{what}: expected {expected!r}, got {actual!r}")
        return ok


def grade_drx_files(drx_dir: Path, shot_ids: list[str]) -> dict[str, Path]:
    """Per-shot DRX files in ``drx_dir``: ``<id>.drx`` or ``<id>_*.drx`` (the ExportStills
    name). Raises BuildError when a shot has none or more than one."""
    found: dict[str, Path] = {}
    bad = []
    for sid in shot_ids:
        hits = sorted({*drx_dir.glob(f"{sid}.drx"), *drx_dir.glob(f"{sid}_*.drx")})
        if len(hits) == 1:
            found[sid] = hits[0]
        else:
            bad.append(f"{sid}: {len(hits)} DRX files" + (f" ({', '.join(h.name for h in hits)})" if hits else ""))
    if bad:
        raise BuildError(f"--grade-drx {drx_dir}: " + "; ".join(bad))
    return found


def grade_build_differences(meta: dict, current: dict) -> list[str]:
    """Build options in ``grade.json`` ``build`` that differ from this build's (pure)."""
    want = meta.get("build") or {}
    return [f"{k}: grade made on {v!r}, this build uses {current.get(k)!r}"
            for k, v in want.items() if k in current and str(current.get(k)) != str(v)]


def _jsonable(x: Any) -> Any:
    if isinstance(x, dict):
        return {str(k): _jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_jsonable(v) for v in x]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


# -- Resolve steps ---------------------------------------------------------------
class Builder:
    def __init__(self, reel_dir: Path, footage_dir: Path, project_name: str | None, stills: bool,
                 look: str | None = None, stills_only: bool = False, stills_dir: Path | None = None,
                 script_path: Path | None = None, use_track: bool = True,
                 ambience_db: float | None = None, canvas: str | None = None, superscale: bool = True,
                 deliver: str = "sdr", hlg_normalize: str = "cdl",
                 overlay_nits: float = hdr_mod.GRAPHICS_WHITE_NITS, grade_drx: Path | None = None,
                 hdr_source: str | None = None, shared_root: Path | None = None,
                 db_path: Path | None = None, use_assets: bool = True):
        self.reel_dir = reel_dir
        self.use_assets = use_assets
        self.grade_drx_dir = grade_drx
        self.deliver = deliver
        self.overlay_nits = overlay_nits
        self.hlg_normalize = hlg_normalize
        self.color = color_settings(deliver)
        self.cdl = hlg_cdl(deliver, hlg_normalize)
        self.superscale = superscale
        self.use_track = use_track
        self.ambience_db_override = ambience_db
        self.reel = reel_dir.name
        self.footage_dir = footage_dir
        self.want_stills = stills
        self.look_override = look
        self.stills_only = stills_only
        self.stills_dir = stills_dir or reel_dir / "stills"
        self.report_path = (self.stills_dir / "stills-report.json") if stills_only else reel_dir / "build-report.json"
        self.style = load_json(STYLE_PATH)
        self.manifest = load_json(footage_dir / "clip_manifest.json")
        self.footage_id = self.manifest.get("footage") or self.manifest.get("walk") or footage_dir.name
        self.hdr_source_requested = hdr_source or mezz_mod.hdr_source_default(self.style)
        self.hdr_source = mezz_mod.effective_hdr_source(self.hdr_source_requested, deliver)
        self.sources: dict[str, dict] = {}
        self.script = load(script_path or reel_dir / "script.json")
        cuts_path = reel_dir / "cuts.json"
        self.cuts = load_json(cuts_path) if cuts_path.exists() else None
        self.track_on = bool(self.script.track) and use_track
        self.beats: dict | None = None
        self.beats_path: Path | None = None
        if self.script.track:
            track = Path(self.script.track).expanduser()
            track = track if track.is_absolute() else reel_dir / track
            self.beats_path = next((bp for bp in (track.with_name("beats.json"), reel_dir / "beats.json")
                                    if bp.exists()), None)
            self.beats = load_json(self.beats_path) if self.beats_path else None
        # --canvas > the Script's canvas > style.json canvas.
        self.canvas: Canvas = for_reel(self.style, self.script.canvas, canvas)
        self.width, self.height, self.fps = self.canvas.width, self.canvas.height, self.canvas.fps
        self.project_name = project_name or f"cf-{self.footage_id}-{self.reel}"
        self.r = Report(reel=self.reel, footage=self.footage_id, project=self.project_name)
        self.r.canvas = {"width": self.width, "height": self.height, "fps": self.fps,
                         "reference_width": self.canvas.reference_width, "scale": self.canvas.scale,
                         "preset": self.canvas.preset, "override": canvas, "script_canvas": self.script.canvas,
                         "spec": spec_of(canvas, self.script.canvas),
                         "safe_zone_px": scaled_safe_zone(self.style, self.canvas)}
        self.d: Any = None
        self.cue_plan: list[PlannedCue] = []
        self.assets_ctx = None
        if has_cues(self.script):
            self.r.assets = {"enabled": use_assets, "library_problem": None, "warnings": [], "cues": [],
                             "tracks": {}, "stills": []}
        if has_cues(self.script) and use_assets:
            from cf.assets import context  # noqa: PLC0415

            self.assets_ctx = context(script_path or reel_dir / "script.json", root=shared_root, db_path=db_path)
            self.r.assets["library_problem"] = self.assets_ctx.library_problem

    # ---- steps
    def validate(self) -> None:
        f = check(self.script, self.manifest, self.style, self.assets_ctx, cues=self.use_assets)
        if f.problems:
            raise BuildError("script.json does not validate:\n- " + "\n- ".join(f.problems))
        for w in f.warnings:
            self.r.notes.append(f"asset warning: {w}")
        if self.r.assets:
            self.r.assets["warnings"] = list(f.warnings)
            if not self.use_assets:
                self.r.notes.append("--no-assets: the Script's Asset cues are left out of this build")

    def cues_on(self) -> bool:
        return self.assets_ctx is not None and self.use_assets

    def cue_reference(self) -> None:
        """The level the sound cues are set against, measured before Resolve is touched."""
        from cf import assets as ca  # noqa: PLC0415

        if not self.cues_on():
            return
        lib = self.assets_ctx.library
        sound = any(ca.has_sound(a) for a in (ca.lookup(lib, c.ref) for s in self.script.shots for c in s.assets)
                    if a is not None)
        track_lufs = None
        if sound and self.track_on:
            shots, _ = plan_shots(self.script, self.manifest, 0, self.fps, self.cuts)
            duration = shots[-1].record_end
            plan, _ = plan_track(self.script, self.reel_dir, 0, duration, self.fps, self.beats,
                                 DEFAULT_TRACK_FADE_OUT_S)
            track_lufs = measure_track_lufs(plan.path, plan.src_start / self.fps, duration / self.fps)
        ref, source = reference_level(self.style, track_lufs)
        self.r.assets["reference"] = {"lufs": ref, "source": source, "measured_track_lufs": track_lufs}

    def connect(self) -> None:
        from cf.resolve_driver import ResolveDriver  # noqa: PLC0415 - keeps planning importable without Resolve

        self.d = ResolveDriver(timeout=60)
        self.d.connect()
        self.d.get_or_create_project(self.project_name)

    def project_settings(self) -> None:
        d, p = self.d, self.d.project
        wanted = {"timelineResolutionWidth": str(self.width), "timelineResolutionHeight": str(self.height),
                  "timelineFrameRate": str(self.fps), **self.color}
        from cf.resolve_driver import same_value  # noqa: PLC0415

        order = list(PROJECT_SETTINGS_ORDER) + [k for k in wanted if k not in PROJECT_SETTINGS_ORDER]
        for key in order:
            value = wanted[key]
            before = (d.call(p.GetSettings) or {}).get(key)
            if same_value(value, before):
                row = {"key": key, "wanted": value, "before": before, "after": before, "action": "kept", "ok": True}
            else:
                try:
                    after = d.set_setting_verified(key, value)
                    row = {"key": key, "wanted": value, "before": before, "after": after, "action": "written",
                           "ok": True}
                except Exception as exc:  # noqa: BLE001 - recorded as a mismatch
                    after = (d.call(p.GetSettings) or {}).get(key)
                    row = {"key": key, "wanted": value, "before": before, "after": after, "action": "FAILED",
                           "ok": False, "error": str(exc)}
                    self.r.mismatches.append(f"project setting {key}: wanted {value!r}, read {after!r}")
            self.r.settings.append(row)

    def prepare_sources(self) -> None:
        """The file Resolve imports per clip (``cf.mezz.plan_sources``); with ``apple-sdr`` the
        HDR clips' mezzanines are made (or reused from the cache) here, before Resolve is touched."""
        order = list(dict.fromkeys(s.clip for s in self.script.shots))
        clips = manifest_clips(self.manifest)
        raw = {c: str(self.footage_dir / "raw" / c) for c in order}
        for c, pth in raw.items():
            if not Path(pth).exists():
                alt = clips[c].get("path")
                if alt and Path(alt).exists():
                    raw[c] = alt
                else:
                    raise BuildError(f"clip file not found: {pth}")
        self.sources = mezz_mod.plan_sources(clips, self.footage_dir, raw, self.hdr_source)
        rows = {}
        for c, src in self.sources.items():
            row = {"file": src["path"], "input_color_space": src["input_color_space"], "mezz": src["mezz"]}
            if src["mezz"]:
                try:
                    meta = mezz_mod.make_mezz(Path(src["raw"]), Path(src["path"]))
                except mezz_mod.MezzError as exc:
                    raise BuildError(str(exc)) from exc
                row.update(raw=src["raw"], action=meta["action"], seconds=meta.get("seconds"),
                           method=meta.get("method"), frames=meta.get("frames"), audio=meta.get("audio"))
            rows[c] = row
        self.r.sources = {"hdr_source": self.hdr_source, "requested": self.hdr_source_requested, "clips": rows}
        if self.hdr_source != self.hdr_source_requested:
            self.r.notes.append(f"--deliver {self.deliver} reads HDR clips through Resolve "
                                f"(hdr_source {self.hdr_source_requested!r} ignored)")

    def import_clips(self) -> dict[str, Any]:
        d = self.d
        order = list(dict.fromkeys(s.clip for s in self.script.shots))
        clips = manifest_clips(self.manifest)
        paths = {c: self.sources[c]["path"] for c in order}
        before = d.clip_index()
        items_list = d.import_media([paths[c] for c in order], bin_name=self.footage_id)
        after = d.clip_index()
        items = dict(zip(order, items_list))
        for c in order:
            mpi = items[c]
            props = d.call(mpi.GetClipProperty) or {}
            want_cs = self.sources[c]["input_color_space"]
            got_cs = props.get("Input Color Space")
            if not want_cs:
                raise BuildError(f"{c}: the manifest has no resolve_input_color_space")
            # Forced: Resolve auto-detects iPhone HLG as 'Rec.2100 HLG', which is not the
            # transform the experiment chose; a mezzanine is forced to 'Rec.709 Gamma 2.4'.
            action = "kept" if got_cs == want_cs else None
            if action is None:
                try:
                    got_cs = d.set_clip_property_verified(mpi, "Input Color Space", want_cs)
                    action = "written"
                except Exception as exc:  # noqa: BLE001
                    action = f"FAILED: {exc}"
                    self.r.mismatches.append(f"{c} Input Color Space: wanted {want_cs!r}, read {got_cs!r}")
            dup = len(after.get(paths[c], []))
            row = {"clip": c, "path": paths[c], "pool": "reused" if paths[c] in before else "imported",
                   "copies_in_pool": dup, "resolve_fps": float(props.get("FPS") or 0),
                   "manifest_fps": clips[c]["fps"], "resolve_frames": props.get("Frames"),
                   "manifest_color_space": clips[c].get("resolve_input_color_space"),
                   "apple_sdr_mezz": self.sources[c]["mezz"], "resolution": props.get("Resolution"),
                   "input_color_space": got_cs, "color_action": action}
            self.r.media.append(row)
            self.r.check(f"{c} single copy in media pool", 1, dup)
            if abs(row["resolve_fps"] - float(row["manifest_fps"])) > 1e-3:
                self.r.notes.append(f"{c}: Resolve reads {row['resolve_fps']:g} fps, the manifest says "
                                    f"{row['manifest_fps']:g}; source frames use Resolve's value")
        self.super_scale(items, {c: clips[c] for c in order})
        return items

    def super_scale(self, items: dict[str, Any], clips: dict[str, dict]) -> None:
        """Super Scale on each media pool clip per ``upscale_plan``, read back.

        The read-back cannot tell 2x from 2x Enhanced (both read ``Super Scale`` = 2); for
        Enhanced the sharpness and noise-reduction values it wrote are read back instead.
        The stills are the pixel-level check (Enhanced, plain 2x and off differ).
        """
        d, r = self.d, self.r
        for u in upscale_plan(clips, self.canvas, self.style, enabled=self.superscale):
            mpi = items[u.clip]
            before = d.call(mpi.GetClipProperty) or {}
            if u.super_scale != 1:
                # Writing 2 over 2x Enhanced keeps Enhanced (same read-back, same pixels;
                # 2026-10-11), so go through off first and the target mode always applies.
                d.call(mpi.SetClipProperty, "Super Scale", 1)
            ok = d.call(mpi.SetClipProperty, "Super Scale", *u.set_args())
            got = d.call(mpi.GetClipProperty) or {}
            row = {"clip": u.clip, "display_height": u.display_height, "reason": u.reason,
                   "wanted": "2x Enhanced" if u.enhanced else ("2x" if u.super_scale == 2 else "off"),
                   "set_args": list(u.set_args()), "returned": ok,
                   "before": before.get("Super Scale"), "super_scale": got.get("Super Scale"),
                   "sharpness": got.get("SuperScale Sharpness"),
                   "noise_reduction": got.get("SuperScale Noise Reduction"),
                   "resolution": got.get("Resolution")}
            r.upscale.append(row)
            r.check(f"{u.clip} Super Scale ({row['wanted']}, returned {ok})", u.super_scale,
                    int(got.get("Super Scale") or 0))
            if u.enhanced:
                got_sn = [float(got.get("SuperScale Sharpness") or -1),
                          float(got.get("SuperScale Noise Reduction") or -1)]
                r.check(f"{u.clip} SuperScale Sharpness / Noise Reduction", [u.sharpness, u.noise_reduction],
                        got_sn, ok=abs(got_sn[0] - u.sharpness) < 1e-3 and abs(got_sn[1] - u.noise_reduction) < 1e-3)

    def build_timeline(self, items: dict[str, Any]) -> None:
        d, r, fps = self.d, self.r, self.fps
        proj = d.call(d.project.GetSettings) or {}
        from cf.resolve_driver import same_value  # noqa: PLC0415

        project_ok = all(same_value(v, proj.get(k)) for k, v in (
            ("timelineResolutionWidth", self.width), ("timelineResolutionHeight", self.height),
            ("timelineFrameRate", self.fps)))
        existed = d.find_timeline(self.reel) is not None
        tl = d.create_timeline(self.reel, self.width, self.height, fps, custom=not project_ok)
        self.tl = tl
        start = int(d.call(tl.GetStartFrame))
        tls = d.call(tl.GetSettings) or {}
        r.timeline = {"name": self.reel, "replaced_existing": existed, "custom_settings": not project_ok,
                      "start_frame": start, "start_tc": d.call(tl.GetStartTimecode),
                      "settings": {k: tls.get(k) for k in ("useCustomSettings", "timelineResolutionWidth",
                                                           "timelineResolutionHeight", "timelineFrameRate")}}
        clip_fps = {m["clip"]: m["resolve_fps"] for m in r.media if m["resolve_fps"]}
        shots, notes = plan_shots(self.script, self.manifest, start, fps, self.cuts, clip_fps,
                                  raw_dir=self.footage_dir / "raw")
        r.notes.extend(notes)
        self.plan = shots

        d.ensure_tracks(tl, "video", 3, VIDEO_TRACK_NAMES)
        d.ensure_tracks(tl, "audio", 1, {1: AUDIO_TRACK_NAMES[1]})

        vids = d.append(append_infos(shots, items, media_type=1, track_index=1))
        r.check("V1 items returned by AppendToTimeline", len(shots), len(vids))
        auds = d.append(append_infos(shots, items, media_type=2, track_index=1))
        r.check("A1 items returned by AppendToTimeline", len(shots), len(auds))
        self._remove_audio_spill(tl)
        self.vids, self.auds = vids, auds

        # Speed (RippleTimeline false: keeps the timeline duration, rescales the source span).
        for s, v, a in zip(shots, vids, auds):
            if abs(s.speed - 1.0) < 1e-9:
                continue
            for kind, it in (("video", v), ("audio", a)):
                ok = d.call(it.SetSpeed, {"Percentage": s.speed * 100.0, "RippleTimeline": False})
                got = (d.call(it.GetSpeed) or {}).get("Percentage")
                r.check(f"{s.id} {kind} speed % (SetSpeed returned {ok})", round(s.speed * 100.0, 3),
                        round(float(got or 0), 3))

        # Volume: ambience under a Track (also with --no-track, where the Track is added in
        # Instagram), natural sound at 0 dB for a Reel without a Track; --ambience-db wins.
        if self.ambience_db_override is not None:
            vol = float(self.ambience_db_override)
        else:
            vol = float(self.style["audio"]["ambience_db"]) if self.script.track else 0.0
        r.timeline["ambience_db"] = vol
        if self.script.track and not self.track_on:
            r.notes.append(f"--no-track: Track {self.script.track!r} left out; ambience stays at {vol:g} dB "
                           "as the bed under the sound added in Instagram")
        for s, a in zip(shots, auds):
            try:
                got = d.set_item_property_verified(a, "AudioVolume", vol)
                r.check(f"{s.id} A1 AudioVolume", vol, float(got))
            except Exception as exc:  # noqa: BLE001
                r.check(f"{s.id} A1 AudioVolume", vol, str(exc), ok=False)

        # Fades on picture and sound.
        for s, v, a in zip(shots, vids, auds):
            if not (s.fade_in or s.fade_out):
                continue
            want = {"FadeIn": s.fade_in, "FadeOut": s.fade_out}
            for kind, it in (("video", v), ("audio", a)):
                d.call(it.SetFades, want)
                got = d.call(it.GetFades) or {}
                r.check(f"{s.id} {kind} fades", want, {k: got.get(k) for k in want})

        self.reframe(tl, shots, vids)

        # Transitions: a shot's transition is the one INTO it (the first shot: from black).
        dur = int(self.style.get("transitions", {}).get("dissolve_frames", 8))
        for i, s in enumerate(shots):
            if s.transition == "cut":
                continue
            opts = {"type": TRANSITION_TYPES[s.transition], "category": "simple", "duration": dur}
            where = start + s.record_offset
            if i == 0:
                target = vids[0]
                opts.update(position="start", alignment="right")
            else:
                target = vids[i - 1]
                opts.update(position="end", alignment="center")
            tr = d.call(target.AddTransition, opts)
            if tr is None:
                r.check(f"{s.id} transition {opts}", "transition item", None, ok=False)
                continue
            got = (int(d.call(tr.GetStart)), int(d.call(tr.GetEnd)))
            want = (where, where + dur) if i == 0 else (where - dur // 2, where + dur - dur // 2)
            r.check(f"{s.id} {opts['type']} span", list(want), list(got))

        if self.track_on:
            self.place_track(tl, start, shots[-1].record_end - start)
        self.place_cues(tl, shots)

        # Markers: timeline markers take offsets from the timeline start (S10). One marker
        # per frame, so a beat marker on a shot's first frame is left out.
        shot_frames = set()
        for s in shots:
            payload = json.dumps({"shot_id": s.id, "clip": s.clip, "role": s.role}, ensure_ascii=False)
            shot_frames.add(s.record_offset)
            try:
                got = d.add_marker(tl, s.record_offset, ROLE_MARKER_COLOR.get(s.role, "Green"), s.id,
                                   s.overlay_text or "", 1, payload)
                r.check(f"{s.id} marker at +{s.record_offset}", payload, got.get("customData"))
            except Exception as exc:  # noqa: BLE001
                r.check(f"{s.id} marker at +{s.record_offset}", payload, str(exc), ok=False)
        self.beat_markers = []
        skipped = []
        for m in beat_marker_plan(self.cuts, shots[-1].record_end - start):
            if m["frame"] in shot_frames:
                skipped.append(m["frame"])
                continue
            color = DOWNBEAT_MARKER_COLOR if m["downbeat"] else BEAT_MARKER_COLOR
            name = ("downbeat" if m["downbeat"] else "beat") + f" {m['beat_index']}"
            payload = json.dumps({"beat_index": m["beat_index"], "downbeat": m["downbeat"], "t": m["t"]})
            try:
                got = d.add_marker(tl, m["frame"], color, name, "", 1, payload)
                ok = r.check(f"{name} marker at +{m['frame']}", [color, payload], [got.get("color"),
                                                                                    got.get("customData")])
                if ok:
                    self.beat_markers.append(m)
            except Exception as exc:  # noqa: BLE001
                r.check(f"{name} marker at +{m['frame']}", payload, str(exc), ok=False)
        r.timeline["beat_markers"] = {"placed": len(self.beat_markers),
                                      "downbeats": sum(1 for m in self.beat_markers if m["downbeat"]),
                                      "skipped_on_shot_frames": skipped}

    def follow_analysis(self) -> None:
        """Person boxes on the proxies for every reframed landscape shot; the follow windows.

        Runs before Resolve is touched (the detector and Resolve together were heavy on the earlier 8 GB M2).
        ``follow`` shots get the window from ``cf.follow.choose_window`` (the loop-seam pair
        shares one window over both ranges); ``center``/``pan`` shots get the coverage of their
        fixed window, for the report. Raw detections are cached in ``<reel>/follow-boxes.json``.
        """
        r = self.r
        self.default_mode = rf.default_mode(self.style)
        eff = effective_reframes(self.script, self.manifest, self.width, self.height, self.default_mode)
        clips = manifest_clips(self.manifest)
        wanted = [s for s in self.script.shots if eff[s.id][0] is not None and eff[s.id][0].mode != "smart"]
        self.follow_x: dict[str, float] = {}
        self.follow_rows: dict[str, dict] = {}
        if not wanted:
            return
        cache_path = self.reel_dir / "follow-boxes.json"
        try:
            cache = json.loads(cache_path.read_text()) if cache_path.exists() else {}
        except json.JSONDecodeError:
            cache = {}
        det = None
        boxes: dict[str, list[fw.Box | None]] = {}
        try:
            for s in wanted:
                proxy = self.footage_dir / "proxy" / (Path(s.clip).stem + ".mp4")
                key = f"{s.clip}|{s.in_s:.4f}|{s.out_s:.4f}|{fw.SAMPLE_FPS:g}|{fw.CONF:g}"
                if key not in cache:
                    if not proxy.exists():
                        raise BuildError(f"shot {s.id}: reframe {eff[s.id][0].mode} needs the proxy {proxy}")
                    if det is None:
                        det = fw.Detector()
                    cache[key] = {"model": det.model_name, "samples": det.samples(proxy, s.in_s, s.out_s)}
                boxes[s.id] = fw.subject_boxes([(t, [tuple(d) for d in ds]) for t, ds in cache[key]["samples"]])
        finally:
            if det is not None:
                det.close()
        cache_path.write_text(json.dumps(cache))
        by_id = {s.id: s for s in self.script.shots}
        for group in follow_groups(self.script, eff):
            s0 = by_id[group[0]]
            w_px, h_px = rf.display_size(clips.get(s0.clip))
            w = fw.window_fraction(w_px, h_px, self.width, self.height, eff[s0.id][0].zoom)
            # In source-time order: the seam pair is [last, first], and the last shot runs up to the first.
            union = [b for g in group for b in boxes[g]]
            hold = tuple(h for g in group for h in (eff[g][0].hold_s or ()))
            res = fw.choose_window(union, w, hold)
            if hold:
                r.notes.append(f"{'+'.join(group)}: follow window must hold the person at {list(hold)} s: "
                               + (f"held {res.held}" if res.fallback != "hold" else
                                  "impossible (no window holds all of them, or no frame sampled there); hold dropped"))
            for g in group:
                self.follow_x[g] = res.x
                cov, n = fw.coverage(boxes[g], res.left, w)
                self.follow_rows[g] = {**res.to_dict(), "group": group,
                                       "shot_covered": cov, "shot_detected": n,
                                       "shot_coverage_pct": round(100.0 * cov / n, 1) if n else 0.0}
            if res.fallback:
                r.notes.append(f"{'+'.join(group)}: follow: {res.fallback} fallback (no window holds the whole "
                               f"person in any frame; best overlap window at x {res.x:g})")
            elif res.coverage_pct < 100:
                r.notes.append(f"{'+'.join(group)}: follow window x {res.x:g} holds the whole person in "
                               f"{res.covered}/{res.detected} frames ({res.coverage_pct:g} %); missed at source "
                               f"{res.missed_times} s")
        for s in wanted:
            want = eff[s.id][0]
            if want.mode in ("center", "pan"):
                w_px, h_px = rf.display_size(clips.get(s.clip))
                w = fw.window_fraction(w_px, h_px, self.width, self.height, want.zoom)
                x = want.x if want.mode == "pan" else 0.0
                left = fw.left_for_x(x, w)
                cov, n = fw.coverage(boxes[s.id], left, w)
                alt = fw.choose_window(boxes[s.id], w)
                self.follow_rows[s.id] = {"x": x, "left": round(left, 5), "width": round(w, 5),
                                          "frames": len(boxes[s.id]), "detected": n, "covered": cov,
                                          "coverage_pct": round(100.0 * cov / n, 1) if n else 0.0,
                                          "follow_would_choose": {"x": alt.x, "coverage_pct": alt.coverage_pct,
                                                                  "fallback": alt.fallback}}
                if alt.coverage_pct > (100.0 * cov / n if n else 0.0):
                    r.notes.append(f"{s.id}: {want.mode} x {x:g} holds the person in {cov}/{n} frames; follow "
                                   f"would hold {alt.covered}/{alt.detected} at x {alt.x:g}")

    def reframe(self, tl: Any, shots: list[PlannedShot], vids: list[Any]) -> None:
        """Fit-height zoom and Pan on V1 items with a source wider than the canvas; Smart Reframe.

        Order (probe 2026-10-11): the zoom first. ``SmartReframe()`` on a fit-width
        (letterboxed) item completes and changes nothing; after the zoom it keyframes Pan to
        follow the subject. The keyframes do not show in ``GetProperties()`` (Pan still reads
        the written value), so the per-shot still is the read-back for ``smart``.
        """
        d, r = self.d, self.r
        mismatch = (d.call(tl.GetSettings) or {}).get("timelineInputResMismatchBehavior") or \
            (d.call(d.project.GetSettings) or {}).get("timelineInputResMismatchBehavior") or "scaleToFit"
        plans = plan_reframes(self.script, self.manifest, self.width, self.height, mismatch,
                              getattr(self, "default_mode", rf.DEFAULT_MODE), getattr(self, "follow_x", {}))
        self.reframe_plans = plans
        for s, v in zip(shots, vids):
            p = plans.get(s.id)
            if p is None:
                continue
            row: dict[str, Any] = {"shot": s.id, "clip": s.clip, **p.to_dict()}
            if s.id in getattr(self, "follow_rows", {}):
                row["person"] = self.follow_rows[s.id]
            before = d.call(v.GetProperties) or {}
            row["before"] = {k: before.get(k) for k in ("ZoomX", "ZoomY", "ZoomGang", "Pan", "Tilt", "Scaling")}
            try:
                if not before.get("ZoomGang"):
                    d.set_item_property_verified(v, "ZoomGang", True)
                d.set_item_property_verified(v, "ZoomX", p.zoom_x)
                d.set_item_property_verified(v, "Pan", p.pan)
            except Exception as exc:  # noqa: BLE001 - recorded as a mismatch
                row["error"] = str(exc)
            got = d.call(v.GetProperties) or {}
            row["after"] = {k: got.get(k) for k in ("ZoomX", "ZoomY", "ZoomGang", "Pan", "Tilt")}
            r.check(f"{s.id} reframe {p.mode} ZoomX/ZoomY/Pan", [round(p.zoom_x, 4), round(p.zoom_x, 4), p.pan],
                    [round(float(got.get("ZoomX") or 0), 4), round(float(got.get("ZoomY") or 0), 4),
                     round(float(got.get("Pan") or 0), 4)])
            if p.mode == "smart" and "error" not in row:
                row["smart_reframe"] = self._smart_reframe(v)
                got = d.call(v.GetProperties) or {}
                row["after_smart"] = {k: got.get(k) for k in ("ZoomX", "ZoomY", "Pan", "Tilt")}
                status = row["smart_reframe"].get("status") or {}
                r.check(f"{s.id} Smart Reframe job (returned {row['smart_reframe'].get('returned')})", "Complete",
                        status.get("JobStatus"))
                r.check(f"{s.id} ZoomX after Smart Reframe", round(p.zoom_x, 4),
                        round(float(got.get("ZoomX") or 0), 4))
            for n in p.notes:
                r.notes.append(f"{s.id}: reframe {p.mode}: {n}")
            r.reframe.append(row)

    def _smart_reframe(self, item: Any) -> dict:
        """``TimelineItem.SmartReframe()`` and poll ``Project.GetSmartReframeStatus()`` to the end.

        The status is project-wide and keeps the last job's 'Complete', so a terminal status
        counts only on two reads a second apart.
        """
        d = self.d
        if d.call(d.resolve.GetCurrentPage) not in ("edit", "color"):
            d.call(d.resolve.OpenPage, "edit")
        t0 = time.monotonic()
        ok = d.call(item.SmartReframe, timeout=SMART_REFRAME_TIMEOUT_S)
        status: dict = {}
        seen: list[str] = []
        terminal_reads = 0
        while time.monotonic() - t0 < SMART_REFRAME_TIMEOUT_S:
            status = d.call(d.project.GetSmartReframeStatus) or {}
            js = status.get("JobStatus")
            if not seen or seen[-1] != js:
                seen.append(js)
            # 'Inactive' ends the wait only when the call failed or no job showed up in 15 s.
            idle = js == "Inactive" and (not ok or (seen == ["Inactive"] and time.monotonic() - t0 > 15))
            terminal_reads = terminal_reads + 1 if js in SMART_REFRAME_DONE or idle else 0
            if terminal_reads >= 2:
                break
            time.sleep(1.0)
        return {"returned": ok, "status": status, "statuses_seen": seen,
                "seconds": round(time.monotonic() - t0, 1)}

    def place_track(self, tl: Any, start: int, duration: int) -> None:
        """The Track on A2 "music": from the timeline start, for the picture's length, 0 dB,
        fade-out at the end; everything read back."""
        d, r = self.d, self.r
        plan, notes = plan_track(self.script, self.reel_dir, start, duration, self.fps, self.beats,
                                 DEFAULT_TRACK_FADE_OUT_S)
        r.notes.extend(notes)
        self.track_plan = plan
        if not Path(plan.path).exists():
            raise BuildError(f"Track file not found: {plan.path}")
        d.ensure_tracks(tl, "audio", 2, AUDIO_TRACK_NAMES, sub_type="stereo")
        r.check("A2 track name", "music", d.call(tl.GetTrackName, "audio", 2))
        (mpi,) = d.import_media([plan.path], bin_name=f"{self.footage_id} music")
        props = d.call(mpi.GetClipProperty) or {}
        r.check("Track clip FPS = timeline fps (WAV frames are timeline frames)", float(self.fps),
                float(props.get("FPS") or 0))
        items = d.append([{"mediaPoolItem": mpi, "startFrame": plan.src_start, "endFrame": plan.src_end,
                           "mediaType": 2, "trackIndex": 2, "recordFrame": plan.record_frame}])
        r.check("A2 items returned by AppendToTimeline", 1, len(items))
        it = items[0]
        self.music_item = it
        got = d.set_item_property_verified(it, "AudioVolume", 0.0)
        r.check("music AudioVolume", 0.0, float(got))
        want = {"FadeIn": 0, "FadeOut": plan.fade_out}
        d.call(it.SetFades, want)
        fades = d.call(it.GetFades) or {}
        r.check("music fades", want, {k: int(float(fades.get(k) or 0)) for k in want})
        r.timeline["track"] = {**asdict(plan), "beats_json": str(self.beats_path) if self.beats_path else None,
                               "src_start_s": round(plan.src_start / self.fps, 4),
                               "audio_sub_type": d.call(tl.GetTrackSubType, "audio", 2),
                               "file_duration": props.get("Duration")}

    def _plan_cues(self, shots: list[PlannedShot], mismatch: str,
                   file_fps: dict[str, float] | None = None) -> tuple[list[PlannedCue], list[str]]:
        ref = self.r.assets.get("reference") or {}
        lufs, source = (ref["lufs"], ref["source"]) if ref else reference_level(self.style, None)
        return plan_cues(self.script, shots, self.assets_ctx.library, fps=self.fps, canvas=self.canvas,
                         style=self.style, reference_lufs=lufs, reference_source=source, mismatch=mismatch,
                         file_fps=file_fps)

    def place_cues(self, tl: Any, shots: list[PlannedShot]) -> None:
        """Asset cues: sounds on A3/A4 at their level, pictures on V4/V5 with the pos transform; read back."""
        from cf import assets as ca  # noqa: PLC0415

        if not self.cues_on():
            return
        d, r = self.d, self.r
        mismatch = (d.call(tl.GetSettings) or {}).get("timelineInputResMismatchBehavior") or \
            (d.call(d.project.GetSettings) or {}).get("timelineInputResMismatchBehavior") or "scaleToFit"
        cues, _ = self._plan_cues(shots, mismatch)
        if not cues:
            return
        paths = list(dict.fromkeys(c.path for c in cues))
        for p in paths:
            if not Path(p).exists():
                raise BuildError(f"Asset file not found: {p}")
        pool = d.import_media(paths, bin_name=f"{self.footage_id} assets")
        items = dict(zip(paths, pool))
        file_fps = {p: float((d.call(items[p].GetClipProperty) or {}).get("FPS") or 0) for p in paths}
        cues, notes = self._plan_cues(shots, mismatch, {p: f for p, f in file_fps.items() if f})
        r.notes.extend(notes)
        self.cue_plan = cues
        base_audio = 2 if self.track_on else 1
        want = cue_tracks(cues, base_audio)
        has_audio = any(c.track_type == "audio" for c in cues)
        v_names = {i: n for i, n in zip(ca.CUE_TRACKS["video"], ("assets", "assets 2")) if i <= want["video"]}
        a_names = {i: n for i, n in {2: AUDIO_TRACK_NAMES[2], **dict(zip(ca.CUE_TRACKS["audio"], ("sfx", "sfx 2")))}
                   .items() if i <= want["audio"]}
        got_v = d.ensure_tracks(tl, "video", want["video"], v_names)
        got_a = d.ensure_tracks(tl, "audio", want["audio"], a_names, sub_type="stereo") if has_audio else \
            int(d.call(tl.GetTrackCount, "audio"))
        r.assets["tracks"] = {"wanted": want, "video": got_v, "audio": got_a}
        r.check("tracks for the Asset cues (video, audio)", [want["video"], want["audio"] if has_audio else got_a],
                [got_v, got_a])
        placed: dict[int, Any] = {}
        for kind in ("video", "audio"):
            group = [c for c in cues if c.track_type == kind]
            if not group:
                continue
            got = d.append(cue_append_infos(group, items))
            r.check(f"Asset cue {kind} items returned by AppendToTimeline", len(group), len(got))
            for c, it in zip(group, got):
                placed[id(c)] = it
        if has_audio:
            self._remove_cue_audio_spill(tl, want["audio"])
        rows = []
        for c in cues:
            it = placed.get(id(c))
            row = {**asdict(c), "start": None, "end": None}
            if it is not None:
                row.update(start=int(d.call(it.GetStart)), end=int(d.call(it.GetEnd)))
                try:
                    if c.track_type == "audio":
                        row["AudioVolume"] = float(d.set_item_property_verified(it, "AudioVolume", c.volume_db))
                    else:
                        before = d.call(it.GetProperties) or {}
                        if not before.get("ZoomGang"):
                            d.set_item_property_verified(it, "ZoomGang", True)
                        for key in ("ZoomX", "ZoomY", "Pan", "Tilt"):
                            d.set_item_property_verified(it, key, c.transform[key])
                        got = d.call(it.GetProperties) or {}
                        row["after"] = {k: got.get(k) for k in ("ZoomX", "ZoomY", "ZoomGang", "Pan", "Tilt")}
                except Exception as exc:  # noqa: BLE001 - recorded as a mismatch
                    row["error"] = str(exc)
                    r.mismatches.append(f"cue {c.cue} {c.lane}: {exc}")
            r.check(f"cue {c.cue} {c.ref} on {c.lane} start/end", [c.record_frame, c.record_end],
                    [row["start"], row["end"]])
            rows.append(row)
        r.assets["cues"] = rows

    def _remove_cue_audio_spill(self, tl: Any, keep: int) -> None:
        """A multi-channel file can spill onto tracks past the last cue lane; delete those items and tracks."""
        d, r = self.d, self.r
        n = int(d.call(tl.GetTrackCount, "audio"))
        removed = 0
        for idx in range(n, keep, -1):
            extra = d.call(tl.GetItemListInTrack, "audio", idx) or []
            if extra and not d.call(tl.DeleteClips, list(extra), False):
                raise BuildError(f"DeleteClips on A{idx} returned False")
            removed += len(extra)
            if not d.call(tl.DeleteTrack, "audio", idx):
                raise BuildError(f"DeleteTrack('audio', {idx}) returned False")
        if n > keep:
            r.notes.append(f"Asset cue audio spilled onto A{keep + 1}..A{n}: {removed} item(s) and the tracks removed")
        r.assets["audio_spill"] = {"tracks_after_append": n, "items_removed": removed}
        r.check("audio tracks after the Asset cue append", keep, int(d.call(tl.GetTrackCount, "audio")))

    def _remove_audio_spill(self, tl: Any) -> None:
        """iPhone clips carry extra (spatial) audio streams that land on A2..A5 even with
        ``mediaType: 2, trackIndex: 1``. Delete those items and the extra tracks."""
        d, r = self.d, self.r
        n = int(d.call(tl.GetTrackCount, "audio"))
        spilled = 0
        for idx in range(n, 1, -1):
            extra = d.call(tl.GetItemListInTrack, "audio", idx) or []
            if extra and not d.call(tl.DeleteClips, list(extra), False):
                raise BuildError(f"DeleteClips on A{idx} returned False")
            spilled += len(extra)
            if not d.call(tl.DeleteTrack, "audio", idx):
                raise BuildError(f"DeleteTrack('audio', {idx}) returned False")
        r.timeline["audio_spill"] = {"tracks_created_by_append": n, "items_removed": spilled}
        r.check("audio tracks after spill cleanup", 1, int(d.call(tl.GetTrackCount, "audio")))

    def overlays(self) -> None:
        d, r = self.d, self.r
        placed, missing, converted = [], [], []
        hdr = self.deliver == "hdr-hlg"
        for s in self.plan:
            if not s.overlay_text:
                continue
            f = self.reel_dir / "overlays" / f"{s.id}.mov"
            if not f.exists():
                missing.append({"shot": s.id, "text": s.overlay_text, "expected_file": str(f)})
                continue
            if hdr:
                # SDR overlay -> HLG at graphics white (203 nits), cf.hdr; the inverse DRT
                # would put SDR white at the 1000-nit peak.
                f, info = hdr_mod.hlg_overlay(f, self.overlay_nits)
                if info:
                    converted.append(info)
            (mpi,) = d.import_media([f], bin_name=f"{self.footage_id} overlays" + (" hlg" if hdr else ""))
            frames = int(float((d.call(mpi.GetClipProperty) or {}).get("Frames") or 0))
            on_disk = file_frames(f)
            # A re-rendered overlay keeps its path, and Resolve keeps the old pixels (and,
            # when the length changed, the old length) behind the pool item. Always swap
            # the asset under the item so the timeline uses the file as it is on disk.
            ok = d.call(mpi.ReplaceClip, str(f))
            old = frames
            frames = int(float((d.call(mpi.GetClipProperty) or {}).get("Frames") or 0))
            if on_disk and old != on_disk:
                r.notes.append(f"{s.id}: overlay pool item had {old} frames, file has {on_disk}; "
                               f"ReplaceClip returned {ok}, now {frames}")
            elif not ok:
                r.notes.append(f"{s.id}: ReplaceClip returned {ok}")
            r.check(f"{s.id} overlay pool frames = file frames", on_disk or frames, frames)
            if hdr:
                props = d.call(mpi.GetClipProperty) or {}
                if props.get("Input Color Space") != hdr_mod.HLG_INPUT_COLOR_SPACE:
                    d.set_clip_property_verified(mpi, "Input Color Space", hdr_mod.HLG_INPUT_COLOR_SPACE)
                got_cs = (d.call(mpi.GetClipProperty) or {}).get("Input Color Space")
                r.check(f"{s.id} HLG overlay Input Color Space", hdr_mod.HLG_INPUT_COLOR_SPACE, got_cs)
            res = (d.call(mpi.GetClipProperty) or {}).get("Resolution")
            if res and res != f"{self.width}x{self.height}":
                r.notes.append(f"{s.id}: overlay is {res}, the canvas {self.width}x{self.height}; Resolve scales "
                               "it to fit (soft text when upscaled): re-render the overlay at the canvas size")
            want = s.overlay_frames or s.duration
            if frames != want:
                span = f" ({s.overlay_span} shots)" if s.overlay_span > 1 else ""
                r.notes.append(f"{s.id}: overlay is {frames} frames, the shot{span} {want}; "
                               "re-render the overlay with that duration")
            r.check(f"{s.id} overlay frames = spanned duration", want, frames)
            (it,) = d.append([{"mediaPoolItem": mpi, "startFrame": 0, "endFrame": frames, "mediaType": 1,
                               "trackIndex": 2, "recordFrame": s.record_frame}])
            got = [int(d.call(it.GetStart)), int(d.call(it.GetEnd))]
            r.check(f"{s.id} overlay on V2", [s.record_frame, s.record_frame + frames], got)
            placed.append({"shot": s.id, "file": str(f), "frames": frames, "start": got[0], "end": got[1]})
        r.overlays = {"placed": placed, "missing": missing}
        if hdr:
            r.overlays["hlg"] = {"white_nits": self.overlay_nits, "converted": converted,
                                 "input_color_space": hdr_mod.HLG_INPUT_COLOR_SPACE}
        if missing:
            r.notes.append(f"{len(missing)} overlay file(s) missing, skipped: "
                           + ", ".join(m["shot"] for m in missing))

    def look(self) -> None:
        d, r = self.d, self.r
        rel = (self.style.get("look") or {}).get("drx")
        drx = (REPO_ROOT / rel) if rel else None
        if not drx or not drx.exists():
            r.look = {"drx": str(drx) if drx else None, "applied": False, "reason": "file does not exist yet"}
            r.notes.append(f"Look skipped: {drx} does not exist yet")
            return
        res = []
        for s, v in zip(self.plan, self.vids):
            ok = d.call(d.call(v.GetNodeGraph).ApplyGradeFromDRX, str(drx), 0)
            res.append({"shot": s.id, "returned": ok})
            r.check(f"{s.id} ApplyGradeFromDRX (returned value only; a grade cannot be read back)", True, bool(ok))
        r.look = {"drx": str(drx), "applied": True, "items": res}

    def look_lut_path(self) -> Path | None:
        """The Look LUT to apply: ``--look`` wins over ``style.look.lut``; ``none`` means no LUT."""
        if self.look_override is not None:
            rel = self.look_override
        elif self.deliver == "hdr-hlg":
            rel = None  # an HDR delivery keeps the source picture; --look still applies one
        else:
            rel = (self.style.get("look") or {}).get("lut")
        if not rel or str(rel).lower() == "none":
            return None
        path = Path(rel).expanduser()
        return path if path.is_absolute() else (REPO_ROOT / path)

    def look_lut(self) -> None:
        """Look LUT on the ``cf-look`` color group's post-clip node 1; every V1 item in the group.

        Runs after ``normalize_hlg`` (post-clip grades come after the clip's node 1). The
        .cube is copied into Resolve's LUT folder, the LUT list refreshed, and ``GetLUT(1)``
        and each item's ``GetColorGroup()`` read back. A Look of ``none`` clears the LUT.
        """
        import filecmp  # noqa: PLC0415
        import shutil  # noqa: PLC0415

        d, r, p = self.d, self.r, self.d.project
        src = self.look_lut_path()
        if src is not None and not src.exists():
            r.look["lut"] = {"path": str(src), "applied": False, "reason": "file does not exist"}
            r.notes.append(f"Look LUT skipped: {src} does not exist")
            return
        groups = d.call(p.GetColorGroupsList) or []
        grp = next((g for g in groups if d.call(g.GetName) == LOOK_GROUP), None)
        if grp is None:
            if src is None:
                r.look["lut"] = {"path": None, "applied": False, "reason": "no Look LUT set"}
                return
            grp = d.call(p.AddColorGroup, LOOK_GROUP)
            if grp is None:
                raise BuildError(f"AddColorGroup({LOOK_GROUP!r}) returned None")
        post = d.call(grp.GetPostClipNodeGraph)
        if src is None:
            ok = d.call(post.SetLUT, 1, "")
            r.check("Look LUT cleared (group post-clip node 1)", "", d.call(post.GetLUT, 1) or "")
            r.look["lut"] = {"path": None, "applied": False, "cleared": bool(ok)}
            return
        dst = RESOLVE_LUT_DIR / LUT_SUBDIR / src.name
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not (dst.exists() and filecmp.cmp(src, dst, shallow=False)):
            shutil.copyfile(src, dst)
        d.call(p.RefreshLUTList)
        rel = f"{LUT_SUBDIR}/{src.name}"
        ok = d.call(post.SetLUT, 1, str(dst))
        r.check(f"Look LUT on {LOOK_GROUP} post-clip node 1 (SetLUT returned {ok})", rel, d.call(post.GetLUT, 1))
        for s, v in zip(self.plan, self.vids):
            assigned = d.call(v.AssignToColorGroup, grp)
            got = d.call(v.GetColorGroup)
            r.check(f"{s.id} in color group {LOOK_GROUP} (returned {assigned})", LOOK_GROUP,
                    d.call(got.GetName) if got else None)
        r.look["lut"] = {"path": str(src), "resolve_lut": rel, "group": LOOK_GROUP, "node": "post-clip 1",
                         "items": len(self.vids), "applied": True}

    def apply_grade_drx(self) -> None:
        """``--grade-drx``: ApplyGradeFromDRX(<shot>.drx, 0) on every V1 item, last of the color
        steps. The API cannot read a grade back; check the stills against the saved ones."""
        if self.grade_drx_dir is None:
            return
        d, r = self.d, self.r
        files = grade_drx_files(self.grade_drx_dir, [s.id for s in self.plan])
        meta_path = self.grade_drx_dir / "grade.json"
        if meta_path.exists():
            current = {"deliver": self.deliver, "hlg_normalize": self.hlg_normalize, "hdr_source": self.hdr_source,
                       "look": "none" if self.look_lut_path() is None else str(self.look_lut_path())}
            for diff in grade_build_differences(load_json(meta_path), current):
                r.notes.append(f"--grade-drx: {diff}")
        rows = []
        for s, v in zip(self.plan, self.vids):
            ok = d.call(d.call(v.GetNodeGraph).ApplyGradeFromDRX, str(files[s.id]), 0)
            rows.append({"shot": s.id, "drx": str(files[s.id]), "returned": ok})
            r.check(f"{s.id} grade DRX applied (returned value only; a grade cannot be read back)", True, bool(ok))
        r.look["grade_drx"] = {"dir": str(self.grade_drx_dir), "items": rows}

    def normalize_hlg(self) -> None:
        """Node-1 CDL (``hlg_cdl``) on every V1 item whose clip is tagged HLG.

        Runs after the Look so ApplyGradeFromDRX cannot wipe it. The API has no GetCDL,
        so the stills' luma (``stills``) is the read-back. With ``--hlg-normalize none`` or
        ``--deliver hdr-hlg`` there is no CDL: the timeline is rebuilt, so node 1 starts empty.
        """
        d, r = self.d, self.r
        r.timeline["deliver"] = self.deliver
        if self.cdl is None:
            r.timeline["hlg_normalize"] = {"cdl": None, "mode": self.hlg_normalize, "deliver": self.deliver,
                                           "items": []}
            return
        clips = manifest_clips(self.manifest)
        rows, mezz = [], []
        for s, v in zip(self.plan, self.vids):
            if "HLG" not in (clips[s.clip].get("resolve_input_color_space") or ""):
                continue
            if self.sources.get(s.clip, {}).get("mezz"):
                mezz.append(s.id)  # an Apple SDR mezzanine is already SDR: no CDL
                continue
            ok = d.call(v.SetCDL, self.cdl)
            rows.append({"shot": s.id, "clip": s.clip, "returned": ok})
            r.check(f"{s.id} HLG normalize SetCDL (returned value only; no GetCDL)", True, bool(ok))
        r.timeline["hlg_normalize"] = {"cdl": self.cdl if rows else None, "mode": self.hlg_normalize, "items": rows,
                                       "skipped_apple_sdr": mezz}

    def read_back(self) -> None:
        d, r, tl = self.d, self.r, self.tl
        # GetItemListInTrack also returns transitions as items (no MediaPoolItem, no source frames).
        v1_all = d.call(tl.GetItemListInTrack, "video", 1) or []
        v1 = [it for it in v1_all if d.call(it.GetMediaPoolItem) is not None]
        trans = [it for it in v1_all if d.call(it.GetMediaPoolItem) is None]
        a1 = [it for it in (d.call(tl.GetItemListInTrack, "audio", 1) or [])
              if d.call(it.GetMediaPoolItem) is not None]
        r.timeline["transitions_on_v1"] = [{"name": d.call(t.GetName), "start": int(d.call(t.GetStart)),
                                            "end": int(d.call(t.GetEnd))} for t in trans]
        r.check("V1 transition count", sum(1 for s in self.plan if s.transition != "cut"), len(trans))
        r.check("V1 item count", len(self.plan), len(v1))
        r.check("A1 item count", len(self.plan), len(a1))
        start = r.timeline["start_frame"]
        for kind, track, rows in (("V1", v1, r.shots), ("A1", a1, r.audio)):
            for i, s in enumerate(self.plan):
                it = track[i] if i < len(track) else None
                row = {"shot": s.id, "clip": s.clip, "role": s.role, "speed": s.speed,
                       "expected_start": s.record_frame, "expected_end": s.record_end,
                       "expected_duration": s.duration, "expected_src_start": s.src_start,
                       "expected_src_end": s.src_end_after_speed}
                if it is None:
                    row.update(ok=False, problem="missing")
                else:
                    row.update(name=d.call(it.GetName), start=int(d.call(it.GetStart)),
                               end=int(d.call(it.GetEnd)), duration=int(d.call(it.GetDuration)),
                               src_start=d.call(it.GetSourceStartFrame), src_end=d.call(it.GetSourceEndFrame),
                               left_offset=d.call(it.GetLeftOffset, True))
                    # GetSourceStartFrame floors a float (3572 reads 3571 at 29.97 on 30); the left
                    # offset gives the true in-point (cf.frames).
                    row["src_start_exact"] = frames.start_from_left_offset(float(row["left_offset"]), s.clip_fps,
                                                                           self.fps)
                    # The item is named after the imported file (the mezzanine, IMG_0477.mov, for an
                    # Apple SDR source).
                    row["ok"] = (row["name"] == Path(self.sources[s.clip]["path"]).name
                                 and row["start"] == s.record_frame
                                 and row["end"] == s.record_end and row["duration"] == s.duration
                                 and row["src_start_exact"] == s.src_start
                                 and abs(float(row["src_end"]) - s.src_end_after_speed) <= 1.5)
                row["offset"] = s.record_offset
                rows.append(row)
                if not row["ok"]:
                    r.mismatches.append(f"{kind} {s.id}: {row}")
        if self.script.ending == "loop_seamless" and len(self.plan) > 1:
            seam = loop_seam(self.plan, self.fps)
            first, last = r.shots[0], r.shots[-1]
            p_last = self.plan[-1]
            if first.get("src_start_exact") is not None and last.get("src_start_exact") is not None:
                nxt = frames.next_frame(last["src_start_exact"], last["duration"], p_last.clip_fps, self.fps)
                seam["read_back"] = {"last_src_start": last["src_start_exact"], "last_frames": last["duration"],
                                     "next_frame": nxt, "first_src_start": first["src_start_exact"]}
                seam["read_back_gap_frames"] = first["src_start_exact"] - nxt
            r.timeline["loop_seam"] = seam
            r.check("loop seam: the last shot's next source frame = the first shot's first (plan, read-back)",
                    [0, 0], [seam["gap_frames"], seam.get("read_back_gap_frames")])
        r.timeline["end_frame"] = int(d.call(tl.GetEndFrame))
        r.timeline["duration_frames"] = r.timeline["end_frame"] - start
        r.timeline["expected_duration_frames"] = self.plan[-1].record_end - start
        r.timeline["track_counts"] = {t: int(d.call(tl.GetTrackCount, t)) for t in ("video", "audio")}
        r.timeline["markers"] = len(d.call(tl.GetMarkers) or {})
        r.check("timeline marker count", len(self.plan) + len(getattr(self, "beat_markers", [])),
                r.timeline["markers"])
        r.check("timeline length = planned picture length", r.timeline["expected_duration_frames"],
                r.timeline["duration_frames"])
        n_audio = 2 if self.track_on else 1
        if any(c.track_type == "audio" for c in self.cue_plan):
            n_audio = cue_tracks(self.cue_plan, n_audio)["audio"]
        r.check("audio track count", n_audio, r.timeline["track_counts"]["audio"])
        self.read_back_cues()
        if self.track_on:
            tp = self.track_plan
            a2 = [it for it in (d.call(tl.GetItemListInTrack, "audio", 2) or [])
                  if d.call(it.GetMediaPoolItem) is not None]
            r.check("A2 item count", 1, len(a2))
            if a2:
                it = a2[0]
                row = {"name": d.call(it.GetName), "start": int(d.call(it.GetStart)), "end": int(d.call(it.GetEnd)),
                       "src_start": d.call(it.GetSourceStartFrame), "src_end": d.call(it.GetSourceEndFrame),
                       "src_start_time": d.call(it.GetSourceStartTime),
                       "volume": (d.call(it.GetProperties) or {}).get("AudioVolume"),
                       "fades": d.call(it.GetFades)}
                r.timeline["track_read_back"] = row
                r.check("A2 music start/end", [tp.record_frame, tp.record_frame + tp.duration],
                        [row["start"], row["end"]])
                # GetSourceStartFrame() floors a float (988 reads 987 for 32.9333 s; cf.frames), so the
                # in-point is read from GetSourceStartTime() when Resolve returns it.
                t = row.get("src_start_time")
                got_in = round(float(t) * self.fps) if t is not None else int(row["src_start"] or -1)
                r.check("A2 music source in-point (frames, from GetSourceStartTime)", tp.src_start, got_in)
                r.check("A2 music AudioVolume", 0.0, float(row["volume"] or 0))
        vols = [(d.call(it.GetProperties) or {}).get("AudioVolume") for it in a1]
        r.check("A1 ambience AudioVolume (all items)", [r.timeline.get("ambience_db")] * len(a1),
                [float(v) if v is not None else None for v in vols])

    def read_back_cues(self) -> None:
        """Each cue lane against the plan: items, name, start, end, duration, level or transform."""
        d, r, tl = self.d, self.r, self.tl
        if not self.cue_plan:
            return
        rows = []
        for (kind, idx) in sorted({(c.track_type, c.track_index) for c in self.cue_plan}):
            want = sorted((c for c in self.cue_plan if (c.track_type, c.track_index) == (kind, idx)),
                          key=lambda c: c.record_frame)
            got = sorted((it for it in (d.call(tl.GetItemListInTrack, kind, idx) or [])
                          if d.call(it.GetMediaPoolItem) is not None), key=lambda it: int(d.call(it.GetStart)))
            lane = want[0].lane
            r.check(f"{lane} cue item count", len(want), len(got))
            for c, it in zip(want, got):
                props = d.call(it.GetProperties) or {}
                row = {"cue": c.cue, "ref": c.ref, "lane": lane, "name": d.call(it.GetName),
                       "start": int(d.call(it.GetStart)), "end": int(d.call(it.GetEnd)),
                       "duration": int(d.call(it.GetDuration))}
                ok = (row["name"] == Path(c.path).name and row["start"] == c.record_frame
                      and row["end"] == c.record_end and row["duration"] == c.duration)
                if kind == "audio":
                    row["AudioVolume"] = props.get("AudioVolume")
                    ok = ok and row["AudioVolume"] is not None and \
                        abs(float(row["AudioVolume"]) - float(c.volume_db)) <= 0.05
                else:
                    row.update({k: props.get(k) for k in ("ZoomX", "ZoomY", "Pan", "Tilt")})
                    ok = ok and all(row[k] is not None and abs(float(row[k]) - float(c.transform[k])) <= 1e-3
                                    for k in ("ZoomX", "ZoomY", "Pan", "Tilt"))
                row["ok"] = ok
                rows.append(row)
                if not ok:
                    r.mismatches.append(f"cue {c.cue} {lane}: planned {asdict(c)}, read {row}")
        r.assets["read_back"] = rows

    def _export_still(self, frame: int, f: Path) -> dict:
        d, tl = self.d, self.tl
        tc = timecode(frame, self.fps)
        f.unlink(missing_ok=True)
        set_ok = d.call(tl.SetCurrentTimecode, tc)
        got_tc = d.call(tl.GetCurrentTimecode)
        ok, tries = False, 0
        for tries in range(1, 4):
            ok = d.call(d.project.ExportCurrentFrameAsStill, str(f), timeout=60)
            if ok and f.exists():
                break
            time.sleep(1.0)
        return {"frame": frame, "timecode": tc, "playhead": got_tc, "set_returned": set_ok, "export_returned": ok,
                "export_tries": tries, "file": str(f), "bytes": f.stat().st_size if f.exists() else 0}

    def cue_stills(self) -> None:
        """One still per picture cue at its middle frame (no pixel check: the agent looks at them)."""
        r = self.r
        for c in self.cue_plan:
            if c.track_type != "video":
                continue
            row = {"cue": c.cue, "ref": c.ref, **self._export_still(c.record_frame + c.duration // 2,
                                                                     self.stills_dir / f"cue-{c.cue}.png")}
            r.assets["stills"].append(row)
            r.check(f"cue {c.cue} still at {row['timecode']}", True,
                    bool(row["export_returned"]) and row["bytes"] > 0 and row["playhead"] == row["timecode"])

    def stills(self) -> None:
        d, r, tl = self.d, self.r, self.tl
        out_dir = self.stills_dir
        out_dir.mkdir(parents=True, exist_ok=True)
        page = d.call(d.resolve.GetCurrentPage)
        if page not in ("edit", "color"):
            d.call(d.resolve.OpenPage, "edit")
        for s in self.plan:
            frame = s.record_frame + s.duration // 2
            tc = timecode(frame, self.fps)
            f = out_dir / f"{s.id}.png"
            f.unlink(missing_ok=True)
            set_ok = d.call(tl.SetCurrentTimecode, tc)
            got_tc = d.call(tl.GetCurrentTimecode)
            # The first export after Smart Reframe (and sometimes after a timeline switch) can
            # return False with no file (probe, 2026-10-11); a second try a second later works.
            tries = 0
            for tries in range(1, 4):
                ok = d.call(d.project.ExportCurrentFrameAsStill, str(f), timeout=60)
                if ok and f.exists():
                    break
                time.sleep(1.0)
            size = f.stat().st_size if f.exists() else 0
            row = {"shot": s.id, "frame": frame, "timecode": tc, "playhead": got_tc, "set_returned": set_ok,
                   "export_returned": ok, "export_tries": tries, "file": str(f), "bytes": size}
            if size:
                src_t = (s.src_start + (s.duration // 2) * s.speed * s.clip_fps / self.fps) / s.clip_fps
                proxy = self.footage_dir / "proxy" / (Path(s.clip).stem + ".mp4")
                rp = (getattr(self, "reframe_plans", None) or {}).get(s.id)
                # An Apple SDR mezzanine is what the still must show, so it is the luma reference
                # (on the proxy grid); otherwise the proxy (its own tone map) is.
                luma_frame = self._mezz_frame(s.clip, src_t, proxy)
                if rp is not None:
                    ref = self._reframe_still_checks(s, rp, f, proxy, src_t, row, luma_frame)
                elif luma_frame is not None:
                    ref = proxy_frame_stats(proxy, src_t, luma_frame)
                else:
                    ref = proxy_frame_stats(proxy, src_t) if proxy.exists() else None
                row.update(still_stats(f, (ref["width"], ref["height"]) if ref else None))
                if ref and luma_frame is not None:
                    ref["reference"] = "apple-sdr mezzanine"
                    row["proxy"] = ref
                    mine = row.get("at_proxy_size") or row
                    r.check(f"{s.id} still mean luma = Apple SDR mezzanine frame (within {MEZZ_STILL_TOLERANCE:g}, "
                            f"at {ref['width']}x{ref['height']})", ref["mean_luma"], mine["mean_luma"],
                            ok=abs(mine["mean_luma"] - ref["mean_luma"]) <= MEZZ_STILL_TOLERANCE)
                elif ref:
                    row["proxy"] = ref
                    # Compared on the proxy's grid: the still downscaled to the proxy size.
                    mine = row.get("at_proxy_size") or row
                    if abs(mine["mean_luma"] - ref["mean_luma"]) > 20:
                        r.notes.append(f"{s.id}: still mean luma {mine['mean_luma']} (at "
                                       f"{ref['width']}x{ref['height']}) vs proxy {ref['mean_luma']} "
                                       "(check the color settings)")
                r.check(f"{s.id} still size = canvas", [self.width, self.height],
                        [row.get("width"), row.get("height")])
                import cv2  # noqa: PLC0415

                img = cv2.imread(str(f), cv2.IMREAD_COLOR)
                band = black_band(img) if img is not None else None
                row["black_band"] = band
                worst = max(band.values()) if band else None
                r.check(f"{s.id} no black band > {BLACK_BAND_TOLERANCE_PX} px at any edge of the still "
                        "(top, bottom, left, right)", "<= " + str(BLACK_BAND_TOLERANCE_PX),
                        band, ok=worst is not None and worst <= BLACK_BAND_TOLERANCE_PX)
            r.stills.append(row)
            r.check(f"{s.id} still at {tc}", True, bool(ok) and size > 0 and got_tc == tc)
        self.cue_stills()

    def _mezz_frame(self, clip: str, src_t: float, proxy: Path) -> Any:
        """The clip's Apple SDR mezzanine frame at ``src_t`` on the proxy grid, or None (no mezzanine)."""
        src = self.sources.get(clip) or {}
        if not src.get("mezz") or not Path(src["path"]).exists():
            return None
        size = (540, 960)
        if proxy.exists():
            frame = proxy_frame(proxy, src_t)
            if frame is not None:
                size = (frame.shape[1], frame.shape[0])
        return scaled_frame(Path(src["path"]), src_t, size)

    def _reframe_still_checks(self, s: PlannedShot, rp: rf.ReframePlan, f: Path, proxy: Path, src_t: float,
                              row: dict, luma_frame: Any = None) -> dict | None:
        """Read-back of a reframed shot from its stills.

        Window position: the mid still is template-matched on the proxy frame; for ``center``
        and ``pan`` the window's left edge must be where the plan puts it. For ``smart`` the
        found position is recorded, and 5 frames (first, quarters, last) are checked for a
        black band: Smart Reframe keeps the subject centred and can move past the source edge.
        Returns the luma stats of the window (the band the still shows) in ``luma_frame`` (the
        mezzanine frame on the proxy grid) or else the proxy frame, or None.
        """
        import cv2  # noqa: PLC0415

        d, r, tl = self.d, self.r, self.tl
        src_w, src_h = (int(float(v)) for v in rp.source.split("x"))
        ref = None
        frame = proxy_frame(proxy, src_t) if proxy.exists() else None
        bgr = cv2.imread(str(f), cv2.IMREAD_COLOR)
        x0 = rp.window_x0
        if frame is not None and bgr is not None:
            win = find_window(bgr, frame, rp, src_w, src_h)
            row["reframe_window"] = win
            if "x0_src" in win:
                if rp.mode == "smart":
                    x0 = win["x0_src"]
                else:
                    r.check(f"{s.id} reframe {rp.mode} window left edge in source px (still matched on the proxy, "
                            f"score {win['score']})", rp.window_x0, win["x0_src"],
                            ok=abs(win["x0_src"] - rp.window_x0) <= win["tolerance_src"] and win["score"] >= 0.5)
            ref = proxy_frame_stats(proxy, src_t, luma_frame if luma_frame is not None else frame,
                                    (x0 / src_w, rp.window_w / src_w))
        if rp.mode != "smart":
            return ref
        bands = []
        probe = f.with_name(f".{s.id}-smart-check.png")
        for off in sorted({0, s.duration // 4, s.duration // 2, 3 * s.duration // 4, s.duration - 1}):
            if off == s.duration // 2 and bgr is not None:
                img = bgr
            else:
                probe.unlink(missing_ok=True)
                d.call(tl.SetCurrentTimecode, timecode(s.record_frame + off, self.fps))
                for _ in range(3):
                    if d.call(d.project.ExportCurrentFrameAsStill, str(probe), timeout=60) and probe.exists():
                        break
                    time.sleep(1.0)
                img = cv2.imread(str(probe), cv2.IMREAD_COLOR)
                probe.unlink(missing_ok=True)
            if img is not None:
                bands.append({"offset": off, **black_band(img)})
        worst_v = max((max(b["top"], b["bottom"]) for b in bands), default=0)
        worst_h = max((max(b["left"], b["right"]) for b in bands), default=0)
        suggest = rf.zoom_to_hide_band(worst_v, self.height, rp.zoom) if worst_v > BLACK_BAND_TOLERANCE_PX else None
        row["smart_black_band"] = {"frames": bands, "worst_vertical_px": worst_v, "worst_horizontal_px": worst_h,
                                   "suggested_zoom": suggest}
        ok = r.check(f"{s.id} Smart Reframe leaves no black band (5 frames; px at top/bottom, left/right)",
                     [0, 0], [worst_v, worst_h],
                     ok=worst_v <= BLACK_BAND_TOLERANCE_PX and worst_h <= BLACK_BAND_TOLERANCE_PX)
        if not ok:
            r.notes.append(
                f"{s.id}: Smart Reframe moved the window past the source edge ({worst_v} px black at top/bottom, "
                f"{worst_h} px at the sides): it centres the subject and does not stop at the frame edge. Fix in "
                f"the Script with reframe {{mode: 'smart', zoom: {suggest}}}" if suggest else
                f"{s.id}: Smart Reframe moved the window past the source edge ({worst_v} px black at top/bottom, "
                f"{worst_h} px at the sides); no zoom hides it")
            if suggest:
                r.notes[-1] += (" (or mode 'pan'/'center'; or delete the Tilt keyframes in the Inspector by hand)")
        return ref

    # ---- run
    def attach_timeline(self) -> None:
        """--stills-only: use the built timeline as is; plan from the script for the stills."""
        d, r = self.d, self.r
        tl = d.find_timeline(self.reel)
        if tl is None:
            raise BuildError(f"timeline {self.reel!r} not found in {self.project_name!r}: build it first")
        if not d.call(d.project.SetCurrentTimeline, tl):
            raise BuildError(f"SetCurrentTimeline({self.reel!r}) failed")
        self.tl = tl
        start = int(d.call(tl.GetStartFrame))
        r.timeline = {"name": self.reel, "start_frame": start, "stills_only": True}
        clip_fps: dict[str, float] = {}
        index = d.clip_index()
        for c, info in manifest_clips(self.manifest).items():
            path = (self.sources.get(c) or {}).get("path") or str(self.footage_dir / "raw" / c)
            items = index.get(path) or index.get(str(info.get("path"))) or []
            if items:
                clip_fps[c] = float((d.call(items[0].GetClipProperty) or {}).get("FPS") or 0) or info["fps"]
        self.plan, notes = plan_shots(self.script, self.manifest, start, self.fps, self.cuts, clip_fps,
                                      raw_dir=self.footage_dir / "raw")
        r.notes.extend(notes)
        mismatch = (d.call(tl.GetSettings) or {}).get("timelineInputResMismatchBehavior") or "scaleToFit"
        self.reframe_plans = plan_reframes(self.script, self.manifest, self.width, self.height, mismatch,
                                           getattr(self, "default_mode", rf.DEFAULT_MODE),
                                           getattr(self, "follow_x", {}))
        self.vids = [it for it in (d.call(tl.GetItemListInTrack, "video", 1) or [])
                     if d.call(it.GetMediaPoolItem) is not None]
        r.check("V1 items on the existing timeline", len(self.plan), len(self.vids))
        built = self.reel_dir / "build-report.json"
        if self.cues_on() and built.exists():
            self.cue_plan = cue_plan_from_report(load_json(built) or {})
            r.assets.setdefault("stills", [])
            if not self.cue_plan:
                r.notes.append(f"no cue plan in {built}: no cue stills (rebuild to get them)")
        for s, v in zip(self.plan, self.vids):
            name = Path((self.sources.get(s.clip) or {}).get("path") or s.clip).name
            r.check(f"{s.id} V1 item start", [name, s.record_frame], [d.call(v.GetName), int(d.call(v.GetStart))])

    def run(self) -> int:
        if self.stills_only:
            try:
                self.validate()
                self.follow_analysis()
                self.prepare_sources()
                self.connect()
                self.attach_timeline()
                self.look_lut()
                self.stills()
                self.d.save()
            except Exception as exc:  # noqa: BLE001
                self.r.error = f"{type(exc).__name__}: {exc}"
                self.r.notes.append(traceback.format_exc())
            self.write_report()
            self.print_table()
            return 1 if (self.r.error or self.r.mismatches) else 0
        try:
            self.validate()
            self.cue_reference()
            self.follow_analysis()
            self.prepare_sources()
            self.connect()
            self.project_settings()
            items = self.import_clips()
            self.build_timeline(items)
            self.overlays()
            self.look()
            self.normalize_hlg()
            self.look_lut()
            self.apply_grade_drx()
            self.read_back()
            if self.want_stills:
                self.stills()
            self.d.save()
        except Exception as exc:  # noqa: BLE001 - the report records it, exit code says it
            self.r.error = f"{type(exc).__name__}: {exc}"
            self.r.notes.append(traceback.format_exc())
        self.write_report()
        self.print_table()
        return 1 if (self.r.error or self.r.mismatches) else 0

    def write_report(self) -> None:
        data = _jsonable(asdict(self.r))
        data["plan"] = [asdict(s) for s in getattr(self, "plan", [])]
        data["cue_plan"] = [asdict(c) for c in self.cue_plan]
        data["ok"] = not (self.r.error or self.r.mismatches)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def print_table(self) -> None:
        r = self.r
        print(f"project {r.project}  timeline {r.reel}  start {r.timeline.get('start_frame')} "
              f"({r.timeline.get('start_tc')})  replaced existing: {r.timeline.get('replaced_existing')}")
        print("\nsettings:")
        for s in r.settings:
            print(f"  {'ok ' if s['ok'] else 'BAD'} {s['key']:<30} {s['action']:<8} {s['after']!r}")
        c = r.canvas
        override = f"  (--canvas {c['override']})" if c.get("override") else \
            (f"  (script canvas {c['script_canvas']})" if c.get("script_canvas") else "")
        print(f"canvas {c.get('width')}x{c.get('height')} @{c.get('fps')}  scale x{c.get('scale'):g} from the "
              f"{c.get('reference_width')}-wide reference{override}  safe zone px {c.get('safe_zone_px')}")
        print("\nmedia:")
        for m in r.media:
            print(f"  {m['clip']:<14} {m['pool']:<8} copies={m['copies_in_pool']} fps={m['resolve_fps']:g} "
                  f"(manifest {m['manifest_fps']:g})  {m['input_color_space']!r} [{m['color_action']}]"
                  + ("  Apple SDR mezzanine" if m.get("apple_sdr_mezz") else ""))
        if r.upscale:
            print("\nSuper Scale (read back; 2x and 2x Enhanced both read 2):")
            for u in r.upscale:
                print(f"  {u['clip']:<14} h={u['display_height']!s:<5} {u['wanted']:<12} -> {u['super_scale']}"
                      + (f"  sharp {u['sharpness']} nr {u['noise_reduction']}" if u["wanted"] == "2x Enhanced" else "")
                      + f"  ({u['reason']})")
        if r.reframe:
            bands = {st["shot"]: st.get("black_band") for st in r.stills}
            print("\nreframe coverage (person = whole box inside the window, sampled at "
                  f"{fw.SAMPLE_FPS:g} fps on the proxy; black band = max px at any edge of the mid still):")
            print(f"  {'shot':<5}{'clip':<14}{'mode':<8}{'x':>8}{'coverage':>10}{'frames':>9}{'band px':>9}  note")
            for f in r.reframe:
                pr = f.get("person") or {}
                band = bands.get(f["shot"])
                cov = f"{pr['coverage_pct']:g} %" if pr else "-"
                frames = f"{pr.get('covered', '-')}/{pr.get('detected', '-')}" if pr else "-"
                note = []
                if pr.get("group") and len(pr["group"]) > 1:
                    note.append("seam window " + "+".join(pr["group"]))
                if pr.get("fallback"):
                    note.append(pr["fallback"] + " fallback")
                if pr.get("follow_would_choose"):
                    fc = pr["follow_would_choose"]
                    note.append(f"follow: x {fc['x']:g}, {fc['coverage_pct']:g} %")
                x = f["x"] if f["x"] is not None else 0.0
                print(f"  {f['shot']:<5}{f['clip'][:12]:<14}{f['mode']:<8}{x:>8.3f}{cov:>10}{frames:>9}"
                      f"{(max(band.values()) if band else '-')!s:>9}  {'; '.join(note)}")
            print("\nreframe (ZoomX ganged, Pan in canvas px; read back):")
            for f in r.reframe:
                sr = f.get("smart_reframe") or {}
                smart = (f"  Smart Reframe {sr.get('status', {}).get('JobStatus')} in {sr.get('seconds')} s"
                         if sr else "")
                print(f"  {f['shot']:<5}{f['mode']:<7}{'(default) ' if f['default'] else ''}src {f['source']} "
                      f"window {f['window_w']:g}x{f['window_h']:g} at x0 {f['window_x0']:g}  ZoomX {f['zoom_x']:.4f} "
                      f"-> {(f.get('after') or {}).get('ZoomX')}  Pan {f['pan']:g} -> {(f.get('after') or {}).get('Pan')}"
                      + smart + (f"  ERROR {f['error']}" if f.get("error") else ""))
        print("\nV1 read-back (frames; offsets from timeline start):")
        hdr = f"  {'shot':<5}{'clip':<14}{'role':<8}{'spd':>5}{'exp start':>10}{'got':>7}{'exp end':>9}{'got':>7}" \
              f"{'dur':>5}{'got':>5}{'src in':>8}{'src out':>9}  ok"
        print(hdr)
        for row in r.shots:
            st = r.timeline["start_frame"]
            print(f"  {row['shot']:<5}{row['clip']:<14}{row['role']:<8}{row['speed']:>5g}"
                  f"{row['expected_start'] - st:>10}{row.get('start', -1) - st:>7}"
                  f"{row['expected_end'] - st:>9}{row.get('end', -1) - st:>7}"
                  f"{row['expected_duration']:>5}{row.get('duration', -1):>5}"
                  f"{row.get('src_start', '-')!s:>8}{row.get('src_end', '-')!s:>9}  {'ok' if row['ok'] else 'MISMATCH'}")
        a_ok = sum(1 for row in r.audio if row["ok"])
        print(f"\nA1 read-back: {a_ok}/{len(r.audio)} items at the expected frames")
        if r.timeline.get("audio_spill"):
            print(f"audio spill: {r.timeline['audio_spill']}")
        print(f"A1 ambience: {r.timeline.get('ambience_db')} dB")
        tb = r.timeline.get("track_read_back")
        if tb:
            st = r.timeline["start_frame"]
            print(f"A2 music: {tb['name']} +{tb['start'] - st}..+{tb['end'] - st}, source in {tb['src_start']} "
                  f"({tb['src_start_time']} s), {tb['volume']} dB, fades {tb['fades']}")
        elif self.script.track:
            print("A2 music: none (--no-track)")
        if r.timeline.get("beat_markers"):
            print(f"beat markers: {r.timeline['beat_markers']}")
        if r.stills:
            print(f"stills: {sum(1 for s in r.stills if s['bytes'])}/{len(r.stills)} written to "
                  f"{self.stills_dir}")
            print(f"  {'shot':<5}{'clip':<14}{'size':>10}{'mean luma':>10}{'>=235 %':>9}{'@proxy':>8}"
                  f"{'proxy luma':>12}{'proxy %':>9}")
            for st in r.stills:
                px = st.get("proxy") or {}
                small = st.get("at_proxy_size") or {}
                clip = next((p.clip for p in self.plan if p.id == st["shot"]), "")
                size = f"{st.get('width', '-')}x{st.get('height', '-')}"
                print(f"  {st['shot']:<5}{clip:<14}{size:>10}{st.get('mean_luma', '-')!s:>10}"
                      f"{st.get('pct_ge_235', '-')!s:>9}{small.get('mean_luma', '-')!s:>8}"
                      f"{px.get('mean_luma', '-')!s:>12}{px.get('pct_ge_235', '-')!s:>9}")
        if r.assets.get("cues"):
            st = r.timeline["start_frame"]
            ref = r.assets.get("reference") or {}
            print(f"\nAsset cues (levels against {ref.get('lufs')} LUFS, {ref.get('source')}; "
                  f"tracks {r.assets.get('tracks')}):")
            print(f"  {'cue':<8}{'ref':<28}{'lane':<5}{'start':>7}{'end':>7}  {'variant':<10}"
                  f"{'dB / Zoom Pan Tilt':<30}ok")
            back = {(b["cue"], b["lane"]): b for b in r.assets.get("read_back", [])}
            for c in r.assets["cues"]:
                if c["track_type"] == "audio":
                    what = f"{c['volume_db']:+.1f} dB" + (f" ({c['level']['capped']})" if c["level"]["capped"] else "")
                else:
                    t = c["transform"]
                    what = f"{t['pos']} {t['ZoomX']:g} {t['Pan']:g} {t['Tilt']:g}"
                ok = (back.get((c["cue"], c["lane"])) or {}).get("ok")
                print(f"  {c['cue']:<8}{c['ref'][:27]:<28}{c['lane']:<5}{c['record_frame'] - st:>7}"
                      f"{c['record_frame'] + c['duration'] - st:>7}  {c['variant']:<10}{what:<29} "
                      f"{'ok' if ok else 'MISMATCH'}")
            if r.assets.get("stills"):
                print(f"  cue stills: {sum(1 for s in r.assets['stills'] if s['bytes'])}/{len(r.assets['stills'])}")
        elif r.assets:
            print("\nAsset cues: none placed" + (" (--no-assets)" if not r.assets.get("enabled") else ""))
        print("\nnotes:")
        for n in r.notes:
            print("  - " + n.strip().replace("\n", "\n    "))
        if r.error:
            print(f"\nERROR: {r.error}")
        print(f"\n{len(r.mismatches)} mismatch(es)" + (":" if r.mismatches else ""))
        for m in r.mismatches:
            print(f"  - {m}")
        if r.look.get("lut"):
            print(f"look LUT: {r.look['lut']}")
        print(f"report: {self.report_path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.build", description=__doc__.splitlines()[0])
    ap.add_argument("reel_dir", help="reels/<reel>/ inside the Footage folder (holds script.json)")
    ap.add_argument("--footage", dest="footage",
                    help="Footage folder with clip_manifest.json and raw/ "
                         "(default: the Script's Footage for a Video folder, else two levels up)")
    ap.add_argument("--walk", dest="footage", help=argparse.SUPPRESS)
    ap.add_argument("--project-name", help="Resolve project (default: cf-<footage>-<reel>)")
    ap.add_argument("--no-stills", action="store_true", help="skip the per-shot stills")
    ap.add_argument("--look", help="Look LUT (.cube) overriding style.json look.lut; 'none' clears it")
    ap.add_argument("--stills-only", action="store_true",
                    help="no rebuild: apply the Look to the existing timeline and export the stills")
    ap.add_argument("--stills-dir", help="where the stills go (default <reel_dir>/stills)")
    ap.add_argument("--script", help="script file to use instead of <reel_dir>/script.json")
    ap.add_argument("--no-track", action="store_true",
                    help="leave the Track out (ambience-only build for a sound added in Instagram)")
    ap.add_argument("--ambience-db", type=float,
                    help="A1 ambience volume in dB (default: style.audio.ambience_db with a Track, else 0)")
    ap.add_argument("--canvas", help="canvas preset name (portrait, landscape) or WxH, overriding the Script's "
                                     "canvas and style.json canvas; e.g. 1080x1920 for a comparison build")
    ap.add_argument("--no-superscale", action="store_true",
                    help="Super Scale off (1) on every clip instead of style.json upscale on the low-res ones")
    ap.add_argument("--deliver", choices=DELIVERIES, default="sdr",
                    help="sdr (default): Rec.709 output; hdr-hlg: Rec.2100 HLG output for cf.render --hdr "
                         "(no HLG CDL, no Look unless --look)")
    ap.add_argument("--hlg-normalize", choices=HLG_NORMALIZE_MODES, default="cdl",
                    help="SDR only: cdl (default) puts the -1.02 stop CDL on HLG items; none uses Resolve's own "
                         "HLG -> 709 conversion (one stop brighter)")
    ap.add_argument("--overlay-nits", type=float, default=hdr_mod.GRAPHICS_WHITE_NITS,
                    help="hdr-hlg only: overlay white in nits (default 203 = BT.2408 graphics white, HLG 75 %%)")
    ap.add_argument("--overlay-specs", action="store_true",
                    help="no Resolve: write overlays/specs/<shot>.json for overlays/render.mjs and print the commands")
    ap.add_argument("--hdr-source", choices=mezz_mod.HDR_SOURCES,
                    help="HDR (HLG / Dolby Vision) clips: apple-sdr imports the Apple SDR mezzanine (QuickTime's "
                         "tone mapping, cf.mezz), resolve imports the HLG file (default: style.json "
                         "color.hdr_source, apple-sdr); --deliver hdr-hlg always uses resolve")
    ap.add_argument("--grade-drx", metavar="DIR",
                    help="after the build, ApplyGradeFromDRX each shot's <shot>.drx / <shot>_*.drx from DIR "
                         "(a hand grade saved with ExportStills, e.g. reels/<reel>/author-grade)")
    ap.add_argument("--shared-root", dest="shared_root",
                    help="shared root holding the Library (default: CF_SHARED_ROOT)")
    ap.add_argument("--footage-root", dest="shared_root", help=argparse.SUPPRESS)
    ap.add_argument("--db", help="factory.db for the Library (default: CF_FACTORY_DB, else <shared root>/factory.db)")
    ap.add_argument("--no-assets", action="store_true",
                    help="build without the Script's Asset cues (their rules are skipped; no Library is needed)")
    args = ap.parse_args(argv)
    if args.canvas:
        from cf.canvas import resolve  # noqa: PLC0415

        try:
            resolve(load_json(STYLE_PATH), args.canvas)
        except ValueError as exc:
            print(exc, file=sys.stderr)
            return 2
    reel_dir = Path(args.reel_dir).expanduser().resolve()
    script_path = Path(args.script).expanduser().resolve() if args.script else reel_dir / "script.json"
    if not script_path.exists():
        print(f"no {script_path}", file=sys.stderr)
        return 2
    if args.footage:
        footage_dir = Path(args.footage).expanduser().resolve()
    else:
        try:
            footage_dir = default_footage_dir(reel_dir, load(script_path))
        except Exception:  # noqa: BLE001 - the Builder reports an unreadable Script
            footage_dir = reel_dir.parent.parent
    if not (footage_dir / "clip_manifest.json").exists():
        print(f"no clip_manifest.json in {footage_dir}", file=sys.stderr)
        return 2
    if args.stills_only and args.no_stills:
        print("--stills-only and --no-stills contradict each other", file=sys.stderr)
        return 2
    if args.overlay_specs:
        return write_overlay_specs(reel_dir, footage_dir, script_path, args.canvas)
    stills_dir = Path(args.stills_dir).expanduser().resolve() if args.stills_dir else None
    grade_drx = Path(args.grade_drx).expanduser().resolve() if args.grade_drx else None
    if grade_drx is not None and not grade_drx.is_dir():
        print(f"--grade-drx: no directory {grade_drx}", file=sys.stderr)
        return 2
    if grade_drx is not None and args.stills_only:
        print("--grade-drx needs a full build (it is not applied with --stills-only)", file=sys.stderr)
        return 2
    return Builder(reel_dir, footage_dir, args.project_name, stills=not args.no_stills, look=args.look,
                   stills_only=args.stills_only, stills_dir=stills_dir, script_path=script_path,
                   use_track=not args.no_track, ambience_db=args.ambience_db, canvas=args.canvas,
                   superscale=not args.no_superscale, deliver=args.deliver,
                   hlg_normalize=args.hlg_normalize, overlay_nits=args.overlay_nits, grade_drx=grade_drx,
                   hdr_source=args.hdr_source,
                   shared_root=Path(args.shared_root).expanduser() if args.shared_root else None,
                   db_path=Path(args.db).expanduser() if args.db else None, use_assets=not args.no_assets).run()


if __name__ == "__main__":
    sys.exit(main())
