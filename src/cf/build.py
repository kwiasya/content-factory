"""Build a Reel's timeline in DaVinci Resolve Studio from its script.json.

    python -m cf.build <reel_dir> [--walk <walk_dir>] [--project-name NAME] [--no-stills]

Rules: ``docs/resolve-rules.md``; contract: ``.claude/skills/build-reel/SKILL.md``;
decision to rebuild rather than patch: ``docs/adr/0001-timeline-rebuilt-from-plan.md``.
Every write is read back; the read-back report goes to ``<reel_dir>/build-report.json``
and the exit code is non-zero on any mismatch.

The planning part (``plan_shots``, ``append_infos``, ``source_end``) is pure and has no
Resolve dependency, so it is unit-tested in ``tests/test_build_plan.py``.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
import traceback
from dataclasses import asdict, dataclass, field
from fractions import Fraction
from pathlib import Path
from typing import Any

from cf.script_schema import Script, load, load_json, manifest_clips, validate

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = REPO_ROOT / "style.json"

# docs/resolve-rules.md "Exact strings". Resolution and fps first: they can only be
# written at project level while the project has no timelines.
PROJECT_SETTINGS_ORDER = (
    "timelineResolutionWidth", "timelineResolutionHeight", "timelineFrameRate",
    "colorScienceMode", "separateColorSpaceAndGamma", "isAutoColorManage",
    "colorSpaceTimeline", "colorSpaceOutput", "inputDRT", "outputDRT",
    "timelineWorkingLuminanceMode",
)
COLOR_SETTINGS = {
    "colorScienceMode": "davinciYRGBColorManagedv2",
    "separateColorSpaceAndGamma": "0",
    "isAutoColorManage": "0",
    "colorSpaceTimeline": "DaVinci WG/Intermediate",
    "colorSpaceOutput": "Rec.709 Gamma 2.4",
    "inputDRT": "DaVinci",
    "outputDRT": "DaVinci",
    "timelineWorkingLuminanceMode": "SDR 100",
}
# Resolve auto-detects these strings on import; each is accepted for the manifest value.
INPUT_COLOR_EQUIVALENT = {
    "Rec.2100 HLG (Scene)": {"Rec.2100 HLG (Scene)", "Rec.2100 HLG"},
    "Rec.709 Gamma 2.4": {"Rec.709 Gamma 2.4", "Rec.709 (Scene)"},
}
TRANSITION_TYPES = {"dissolve": "Cross Dissolve", "dip": "Dip To Color Dissolve"}
ROLE_MARKER_COLOR = {"hook": "Red", "build": "Blue", "payoff": "Yellow", "loop": "Purple"}
VIDEO_TRACK_NAMES = {1: "shots", 2: "overlays", 3: "overlays 2"}
AUDIO_TRACK_NAMES = {1: "ambience"}


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
    span = Fraction(duration) * _frac(speed) * _frac(clip_fps) / _frac(timeline_fps)
    if span.denominator == 1:
        return src_start + int(span)
    return round(src_start + float(span) + 0.001, 4)


def plan_shots(script: Script, manifest: dict, start_frame: int, fps: float = 30,
               cuts: dict | None = None, clip_fps: dict[str, float] | None = None,
               raw_dir: str | Path | None = None) -> tuple[list[PlannedShot], list[str]]:
    """Turn a Script (+ optional cuts.json) into timeline positions and source ranges.

    Record positions come from ``cuts.json`` when given, otherwise the shots are laid
    back to back from ``in_s``/``out_s`` (divided by speed) at ``fps``, rounding the
    cumulative time so durations do not drift. Source frames are at each clip's own
    fps: ``clip_fps`` (Resolve's ``FPS`` clip property) wins over the manifest, because
    Resolve reads 59.94 fps iPhone clips as 60.
    """
    clips = manifest_clips(manifest)
    notes: list[str] = []
    cut_by_id: dict[str, dict] = {}
    if cuts is not None:
        cut_by_id = {c["id"]: c for c in cuts.get("shots", [])}
        missing = [s.id for s in script.shots if s.id not in cut_by_id]
        if missing:
            raise BuildError(f"cuts.json has no entry for shots {missing}")
        notes.append("record offsets and durations from cuts.json")
    else:
        notes.append("no cuts.json: shots laid back to back from in_s/out_s at "
                     f"{fps:g} fps (cumulative rounding)")
    out: list[PlannedShot] = []
    t = 0.0
    for s in script.shots:
        c = clips.get(s.clip)
        if c is None:
            raise BuildError(f"shot {s.id}: clip {s.clip!r} not in the manifest")
        cfps = float((clip_fps or {}).get(s.clip) or c["fps"])
        if cuts is not None:
            off = int(cut_by_id[s.id]["record_frame_offset"])
            dur = int(cut_by_id[s.id]["duration_frames"])
        else:
            off = round(t * fps)
            t += (s.out_s - s.in_s) / s.speed
            dur = round(t * fps) - off
        src_start = round(s.in_s * cfps)
        path = str(Path(raw_dir) / s.clip) if raw_dir else c.get("path") or s.clip
        out.append(PlannedShot(
            id=s.id, clip=s.clip, path=path, role=s.role, speed=s.speed, transition=s.transition,
            overlay_text=s.overlay.text if s.overlay else None, clip_fps=cfps,
            record_offset=off, record_frame=start_frame + off, duration=dur, src_start=src_start,
            src_end=source_end(src_start, dur, cfps, fps),
            src_end_after_speed=source_end(src_start, dur, cfps, fps, s.speed),
            fade_in=round(s.fade_in_s * fps), fade_out=round(s.fade_out_s * fps),
        ))
        frames = c.get("nb_frames")
        if frames and out[-1].src_end_after_speed > int(frames) + 1:
            notes.append(f"{s.id}: source range ends at {out[-1].src_end_after_speed:g}, "
                         f"past the clip's {frames} frames")
    for a, b in zip(out, out[1:]):
        if b.record_offset < a.record_offset + a.duration:
            raise BuildError(f"shots {a.id} and {b.id} overlap on V1")
    return out, notes


def append_infos(shots: list[PlannedShot], items: dict[str, Any], media_type: int,
                 track_index: int = 1) -> list[dict]:
    """``AppendToTimeline`` clip infos: source frames at clip fps, exclusive end, absolute record."""
    return [{"mediaPoolItem": items.get(s.clip, s.clip), "startFrame": s.src_start, "endFrame": s.src_end,
             "mediaType": media_type, "trackIndex": track_index, "recordFrame": s.record_frame}
            for s in shots]


def timecode(frame: int, fps: int) -> str:
    """Absolute frame -> non-drop timecode HH:MM:SS:FF."""
    ff = frame % fps
    s = frame // fps
    return f"{s // 3600:02d}:{s // 60 % 60:02d}:{s % 60:02d}:{ff:02d}"


# -- report ----------------------------------------------------------------------
@dataclass
class Report:
    reel: str
    walk: str
    project: str
    started: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%S%z"))
    notes: list[str] = field(default_factory=list)
    settings: list[dict] = field(default_factory=list)
    media: list[dict] = field(default_factory=list)
    timeline: dict = field(default_factory=dict)
    shots: list[dict] = field(default_factory=list)
    audio: list[dict] = field(default_factory=list)
    writes: list[dict] = field(default_factory=list)
    overlays: dict = field(default_factory=dict)
    look: dict = field(default_factory=dict)
    stills: list[dict] = field(default_factory=list)
    mismatches: list[str] = field(default_factory=list)
    error: str | None = None

    def check(self, what: str, expected: Any, actual: Any, ok: bool | None = None) -> bool:
        ok = (expected == actual) if ok is None else ok
        self.writes.append({"what": what, "expected": expected, "actual": actual, "ok": ok})
        if not ok:
            self.mismatches.append(f"{what}: expected {expected!r}, got {actual!r}")
        return ok


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
    def __init__(self, reel_dir: Path, walk_dir: Path, project_name: str | None, stills: bool):
        self.reel_dir = reel_dir
        self.reel = reel_dir.name
        self.walk_dir = walk_dir
        self.want_stills = stills
        self.style = load_json(STYLE_PATH)
        self.manifest = load_json(walk_dir / "clip_manifest.json")
        self.walk = self.manifest.get("walk") or walk_dir.name
        self.script = load(reel_dir / "script.json")
        cuts_path = reel_dir / "cuts.json"
        self.cuts = load_json(cuts_path) if cuts_path.exists() else None
        canvas = self.style.get("canvas", {})
        self.width, self.height = int(canvas.get("width", 1080)), int(canvas.get("height", 1920))
        self.fps = int(canvas.get("fps", 30))
        self.project_name = project_name or f"cf-{self.walk}-{self.reel}"
        self.r = Report(reel=self.reel, walk=self.walk, project=self.project_name)
        self.d: Any = None

    # ---- steps
    def validate(self) -> None:
        problems = validate(self.script, self.manifest, self.style)
        if problems:
            raise BuildError("script.json does not validate:\n- " + "\n- ".join(problems))

    def connect(self) -> None:
        from cf.resolve_driver import ResolveDriver  # noqa: PLC0415 - keeps planning importable without Resolve

        self.d = ResolveDriver(timeout=60)
        self.d.connect()
        self.d.get_or_create_project(self.project_name)

    def project_settings(self) -> None:
        d, p = self.d, self.d.project
        wanted = {"timelineResolutionWidth": str(self.width), "timelineResolutionHeight": str(self.height),
                  "timelineFrameRate": str(self.fps), **COLOR_SETTINGS}
        from cf.resolve_driver import same_value  # noqa: PLC0415

        for key in PROJECT_SETTINGS_ORDER:
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

    def import_clips(self) -> dict[str, Any]:
        d = self.d
        order = list(dict.fromkeys(s.clip for s in self.script.shots))
        clips = manifest_clips(self.manifest)
        paths = {c: str(self.walk_dir / "raw" / c) for c in order}
        for c, pth in paths.items():
            if not Path(pth).exists():
                alt = clips[c].get("path")
                if alt and Path(alt).exists():
                    paths[c] = alt
                else:
                    raise BuildError(f"clip file not found: {pth}")
        before = d.clip_index()
        items_list = d.import_media([paths[c] for c in order], bin_name=self.walk)
        after = d.clip_index()
        items = dict(zip(order, items_list))
        for c in order:
            mpi = items[c]
            props = d.call(mpi.GetClipProperty) or {}
            want_cs = clips[c].get("resolve_input_color_space")
            got_cs = props.get("Input Color Space")
            ok_set = INPUT_COLOR_EQUIVALENT.get(want_cs, {want_cs})
            action = "kept (equivalent)" if got_cs in ok_set else None
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
                   "manifest_color_space": want_cs, "input_color_space": got_cs, "color_action": action}
            self.r.media.append(row)
            self.r.check(f"{c} single copy in media pool", 1, dup)
            if abs(row["resolve_fps"] - float(row["manifest_fps"])) > 1e-3:
                self.r.notes.append(f"{c}: Resolve reads {row['resolve_fps']:g} fps, the manifest says "
                                    f"{row['manifest_fps']:g}; source frames use Resolve's value")
        return items

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
                                  raw_dir=self.walk_dir / "raw")
        r.notes.extend(notes)
        self.plan = shots

        d.ensure_tracks(tl, "video", 3, VIDEO_TRACK_NAMES)
        d.ensure_tracks(tl, "audio", 1, AUDIO_TRACK_NAMES)

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

        # Volume: ambience under a Track, natural sound at 0 dB without one.
        vol = float(self.style["audio"]["ambience_db"]) if self.script.track else 0.0
        if self.script.track:
            r.notes.append(f"Track {self.script.track!r} given: ambience at {vol:g} dB; placing the Track "
                           "on its own audio track is not implemented yet")
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

        # Markers: timeline markers take offsets from the timeline start (S10).
        for s in shots:
            payload = json.dumps({"shot_id": s.id, "clip": s.clip, "role": s.role}, ensure_ascii=False)
            try:
                got = d.add_marker(tl, s.record_offset, ROLE_MARKER_COLOR.get(s.role, "Blue"), s.id,
                                   s.overlay_text or "", s.duration, payload)
                r.check(f"{s.id} marker at +{s.record_offset}", payload, got.get("customData"))
            except Exception as exc:  # noqa: BLE001
                r.check(f"{s.id} marker at +{s.record_offset}", payload, str(exc), ok=False)

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
        placed, missing = [], []
        for s in self.plan:
            if not s.overlay_text:
                continue
            f = self.reel_dir / "overlays" / f"{s.id}.mov"
            if not f.exists():
                missing.append({"shot": s.id, "text": s.overlay_text, "expected_file": str(f)})
                continue
            (mpi,) = d.import_media([f], bin_name=f"{self.walk} overlays")
            frames = int(float((d.call(mpi.GetClipProperty) or {}).get("Frames") or 0))
            (it,) = d.append([{"mediaPoolItem": mpi, "startFrame": 0, "endFrame": frames, "mediaType": 1,
                               "trackIndex": 2, "recordFrame": s.record_frame}])
            got = [int(d.call(it.GetStart)), int(d.call(it.GetEnd))]
            r.check(f"{s.id} overlay on V2", [s.record_frame, s.record_frame + frames], got)
            placed.append({"shot": s.id, "file": str(f), "start": got[0], "end": got[1]})
        r.overlays = {"placed": placed, "missing": missing}
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
                               src_start=d.call(it.GetSourceStartFrame), src_end=d.call(it.GetSourceEndFrame))
                    row["ok"] = (row["name"] == s.clip and row["start"] == s.record_frame
                                 and row["end"] == s.record_end and row["duration"] == s.duration
                                 and abs(float(row["src_start"]) - s.src_start) <= 1
                                 and abs(float(row["src_end"]) - s.src_end_after_speed) <= 1.5)
                row["offset"] = s.record_offset
                rows.append(row)
                if not row["ok"]:
                    r.mismatches.append(f"{kind} {s.id}: {row}")
        r.timeline["end_frame"] = int(d.call(tl.GetEndFrame))
        r.timeline["duration_frames"] = r.timeline["end_frame"] - start
        r.timeline["expected_duration_frames"] = self.plan[-1].record_end - start
        r.timeline["track_counts"] = {t: int(d.call(tl.GetTrackCount, t)) for t in ("video", "audio")}
        r.timeline["markers"] = len(d.call(tl.GetMarkers) or {})
        r.check("timeline marker count", len(self.plan), r.timeline["markers"])

    def stills(self) -> None:
        d, r, tl = self.d, self.r, self.tl
        out_dir = self.reel_dir / "stills"
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
            ok = d.call(d.project.ExportCurrentFrameAsStill, str(f), timeout=60)
            size = f.stat().st_size if f.exists() else 0
            row = {"shot": s.id, "frame": frame, "timecode": tc, "playhead": got_tc, "set_returned": set_ok,
                   "export_returned": ok, "file": str(f), "bytes": size}
            r.stills.append(row)
            r.check(f"{s.id} still at {tc}", True, bool(ok) and size > 0 and got_tc == tc)

    # ---- run
    def run(self) -> int:
        try:
            self.validate()
            self.connect()
            self.project_settings()
            items = self.import_clips()
            self.build_timeline(items)
            self.overlays()
            self.look()
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
        data["ok"] = not (self.r.error or self.r.mismatches)
        (self.reel_dir / "build-report.json").write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def print_table(self) -> None:
        r = self.r
        print(f"project {r.project}  timeline {r.reel}  start {r.timeline.get('start_frame')} "
              f"({r.timeline.get('start_tc')})  replaced existing: {r.timeline.get('replaced_existing')}")
        print("\nsettings:")
        for s in r.settings:
            print(f"  {'ok ' if s['ok'] else 'BAD'} {s['key']:<30} {s['action']:<8} {s['after']!r}")
        print("\nmedia:")
        for m in r.media:
            print(f"  {m['clip']:<14} {m['pool']:<8} copies={m['copies_in_pool']} fps={m['resolve_fps']:g} "
                  f"(manifest {m['manifest_fps']:g})  {m['input_color_space']!r} [{m['color_action']}]")
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
        if r.stills:
            print(f"stills: {sum(1 for s in r.stills if s['bytes'])}/{len(r.stills)} written to "
                  f"{self.reel_dir / 'stills'}")
        print("\nnotes:")
        for n in r.notes:
            print("  - " + n.strip().replace("\n", "\n    "))
        if r.error:
            print(f"\nERROR: {r.error}")
        print(f"\n{len(r.mismatches)} mismatch(es)" + (":" if r.mismatches else ""))
        for m in r.mismatches:
            print(f"  - {m}")
        print(f"report: {self.reel_dir / 'build-report.json'}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.build", description=__doc__.splitlines()[0])
    ap.add_argument("reel_dir", help="reels/<reel>/ inside the Walk folder (holds script.json)")
    ap.add_argument("--walk", help="Walk folder with clip_manifest.json and raw/ (default: two levels up)")
    ap.add_argument("--project-name", help="Resolve project (default: cf-<walk>-<reel>)")
    ap.add_argument("--no-stills", action="store_true", help="skip the per-shot stills")
    args = ap.parse_args(argv)
    reel_dir = Path(args.reel_dir).expanduser().resolve()
    walk_dir = Path(args.walk).expanduser().resolve() if args.walk else reel_dir.parent.parent
    if not (reel_dir / "script.json").exists():
        print(f"no script.json in {reel_dir}", file=sys.stderr)
        return 2
    if not (walk_dir / "clip_manifest.json").exists():
        print(f"no clip_manifest.json in {walk_dir}", file=sys.stderr)
        return 2
    return Builder(reel_dir, walk_dir, args.project_name, stills=not args.no_stills).run()


if __name__ == "__main__":
    sys.exit(main())
