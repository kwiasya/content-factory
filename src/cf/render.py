"""Render a Reel's timeline from DaVinci Resolve Studio and verify the file.

    python -m cf.render <reel_dir> [--walk <walk_dir>] [--preset NAME] [--canvas WxH]
                        [--out <path.mp4>] [--no-check] [--fix-loudness]

Opens project ``cf-<walk>-<reel>`` (never creates one), selects timeline ``<reel>``,
creates or updates the render preset ``cf-instagram-<w>x<h>`` (``style.json``: ``render``
format/codec, ``canvas`` size and fps, ``render.bitrate_mbps`` for that size, i.e. mp4 /
H.264 High, 2160x3840, 30 fps, about 45 Mbit/s by default; AAC 48 kHz,
``ColorSpaceTag='Rec.709'``, ``GammaTag='Rec.709-A'``). ``--canvas 1080x1920`` renders a
comparison file at that size (22 Mbit/s); Resolve scales the timeline to it. It targets
``reels/<reel>/out/<reel>.mp4``, deletes this timeline's old render jobs, queues one job,
renders it with progress, restores the UI page, and runs ``cf.render_check`` on the file.
A JSON report goes to ``out/render-report.json``. Exit code: non-zero when the render
fails or the check fails.

Rules: ``docs/resolve-rules.md``; contract: ``.claude/skills/render-reel/SKILL.md``;
export settings: ``docs/research/03-color-iphone-osmo/result-a.md`` Section D.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from cf import render_check
from cf.canvas import Canvas, from_style, preset_name, render_bitrate_kbps, render_codec
from cf.script_schema import load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
STYLE_PATH = REPO_ROOT / "style.json"
OPTIONAL_KEYS = {"EncodingProfile", "NetworkOptimization"}  # nice to have; a False here is a note
DONE = ("Complete", "Failed", "Cancelled")


def preset_settings(canvas: Canvas, video_kbps: int) -> tuple[tuple[str, Any], ...]:
    """RenderSettings written one key per call, in this order, so a rejected key is named
    (a False return leaves the old value). ``VideoQuality``: an int > 0 is the bit rate cap
    in kbit/s (22000 gave 22.2 Mbit/s at 1080x1920). Data levels are not a RenderSettings
    key; the project's videoDataLevels='Video' gives limited range, and render_check
    verifies color_range=tv."""
    return (
        ("ExportVideo", True),
        ("ExportAudio", True),
        ("FormatWidth", canvas.width),
        ("FormatHeight", canvas.height),
        ("FrameRate", float(canvas.fps)),
        ("VideoQuality", int(video_kbps)),
        ("EncodingProfile", "High"),
        ("NetworkOptimization", True),
        ("AudioCodec", "aac"),
        ("AudioSampleRate", 48000),
        ("ColorSpaceTag", "Rec.709"),
        ("GammaTag", "Rec.709-A"),
    )


def job_expect(canvas: Canvas) -> dict:
    """What GetRenderJobList must report for the queued job."""
    return {"FormatWidth": canvas.width, "FormatHeight": canvas.height, "FrameRate": str(canvas.fps),
            "IsExportVideo": True, "IsExportAudio": True, "AudioSampleRate": 48000}


class RenderError(RuntimeError):
    pass


def job_mismatches(job: dict, expect: dict, out: Path) -> list[str]:
    """Differences between a GetRenderJobList entry and what was asked for (pure)."""
    bad = []
    for k, v in expect.items():
        got = job.get(k)
        if k == "FrameRate":
            try:
                same = abs(float(got) - float(v)) < 1e-3
            except (TypeError, ValueError):
                same = False
        else:
            same = got == v or str(got) == str(v)
        if not same:
            bad.append(f"{k}: wanted {v!r}, job has {got!r}")
    if job.get("TargetDir") and Path(job["TargetDir"]).resolve() != out.parent.resolve():
        bad.append(f"TargetDir: wanted {str(out.parent)!r}, job has {job.get('TargetDir')!r}")
    name = job.get("OutputFilename")
    if name and name != out.name:
        bad.append(f"OutputFilename: wanted {out.name!r}, job has {name!r}")
    return bad


class Renderer:
    def __init__(self, reel_dir: Path, walk_dir: Path, preset: str | None, out: Path | None, project: str | None,
                 canvas: str | None = None):
        self.reel_dir = reel_dir
        style = load_json(STYLE_PATH)
        self.canvas = from_style(style, canvas)
        self.fmt, self.codec = render_codec(style)
        try:
            self.video_kbps = render_bitrate_kbps(style, self.canvas)
        except ValueError as exc:
            raise RenderError(str(exc)) from exc
        preset = preset or preset_name(self.canvas)
        self.reel = reel_dir.name
        manifest = load_json(walk_dir / "clip_manifest.json")
        self.walk = manifest.get("walk") or walk_dir.name
        self.project_name = project or f"cf-{self.walk}-{self.reel}"
        self.preset = preset
        self.out = (out or reel_dir / "out" / f"{self.reel}.mp4").expanduser().resolve()
        if self.out.suffix.lower() != ".mp4":
            raise RenderError(f"--out must end in .mp4: {self.out}")
        self.fps = self.canvas.fps
        self.report: dict[str, Any] = {"reel": self.reel, "project": self.project_name, "preset": self.preset,
                                       "out": str(self.out), "notes": [],
                                       "canvas": {"width": self.canvas.width, "height": self.canvas.height,
                                                  "fps": self.canvas.fps, "override": canvas},
                                       "format": self.fmt, "codec": self.codec, "video_kbps": self.video_kbps}
        self.d: Any = None

    # ---- steps
    def connect(self) -> None:
        from cf.resolve_driver import ResolveDriver  # noqa: PLC0415

        d = self.d = ResolveDriver(timeout=60)
        d.connect()
        pm = d.call(d.resolve.GetProjectManager)
        cur = d.call(pm.GetCurrentProject)
        if not (cur and d.call(cur.GetName) == self.project_name) and \
                self.project_name not in (d.call(pm.GetProjectListInCurrentFolder) or []):
            raise RenderError(f"project {self.project_name!r} not found; build the Reel first (cf.build)")
        d.get_or_create_project(self.project_name)
        self.page = d.call(d.resolve.GetCurrentPage)
        tl = d.find_timeline(self.reel)
        if tl is None:
            raise RenderError(f"timeline {self.reel!r} not found in {self.project_name!r}")
        if not d.call(d.project.SetCurrentTimeline, tl):
            raise RenderError(f"SetCurrentTimeline({self.reel!r}) returned False")
        cur_tl = d.call(d.project.GetCurrentTimeline)
        if d.call(cur_tl.GetName) != self.reel:
            raise RenderError(f"current timeline is {d.call(cur_tl.GetName)!r}, wanted {self.reel!r}")
        self.tl = tl
        start, end = int(d.call(tl.GetStartFrame)), int(d.call(tl.GetEndFrame))
        self.frames = end - start
        self.report["timeline"] = {"name": self.reel, "start_frame": start, "end_frame": end,
                                   "frames": self.frames, "seconds": self.frames / self.fps}

    def ensure_preset(self) -> None:
        """Write the preset settings key by key, then save or update the named preset."""
        d, p = self.d, self.d.project
        d._require_safe_project()
        rows = []
        # Both calls switch the UI to the Deliver page (S8); the page is restored at the end.
        rows.append({"key": "RenderMode", "value": "Single clip", "returned": d.call(p.SetCurrentRenderMode, 1)})
        ok = d.call(p.SetCurrentRenderFormatAndCodec, self.fmt, self.codec)
        got = d.call(p.GetCurrentRenderFormatAndCodec) or {}
        rows.append({"key": "format/codec", "value": f"{self.fmt}/{self.codec}", "returned": ok, "read": got})
        if (got.get("format"), got.get("codec")) != (self.fmt, self.codec):
            raise RenderError(f"SetCurrentRenderFormatAndCodec({self.fmt!r}, {self.codec!r}) -> {ok}, reads {got}")
        for key, value in preset_settings(self.canvas, self.video_kbps):
            ok = bool(d.call(p.SetRenderSettings, {key: value}))
            rows.append({"key": key, "value": value, "returned": ok})
            if not ok:
                msg = f"SetRenderSettings({{{key!r}: {value!r}}}) returned False"
                if key in OPTIONAL_KEYS:
                    self.report["notes"].append(msg + " (optional, skipped)")
                else:
                    raise RenderError(msg)
        presets = d.call(p.GetRenderPresetList) or []
        if self.preset in presets:
            ok, action = d.call(p.UpdateRenderPreset, self.preset), "updated"
        else:
            ok, action = d.call(p.SaveAsNewRenderPreset, self.preset), "created"
        if not ok:
            raise RenderError(f"render preset {self.preset!r} could not be {action}")
        if self.preset not in (d.call(p.GetRenderPresetList) or []):
            raise RenderError(f"render preset {self.preset!r} missing after {action}")
        if not d.call(p.LoadRenderPreset, self.preset):
            raise RenderError(f"LoadRenderPreset({self.preset!r}) returned False")
        self.report["preset_settings"] = rows
        self.report["preset_action"] = action

    def queue(self) -> str:
        d, p = self.d, self.d.project
        removed = []
        for job in d.call(p.GetRenderJobList) or []:
            if job.get("TimelineName") == self.reel:
                if not d.call(p.DeleteRenderJob, job["JobId"]):
                    raise RenderError(f"DeleteRenderJob({job['JobId']}) returned False")
                removed.append(job["JobId"])
        self.report["old_jobs_removed"] = removed
        self.out.parent.mkdir(parents=True, exist_ok=True)
        if self.out.exists():
            self.out.unlink()
        for key, value in (("SelectAllFrames", True), ("TargetDir", str(self.out.parent)),
                           ("CustomName", self.out.stem), ("UseUniqueFilenames", False)):
            if not d.call(p.SetRenderSettings, {key: value}):
                raise RenderError(f"SetRenderSettings({{{key!r}: {value!r}}}) returned False")
        job_id = d.call(p.AddRenderJob)
        if not job_id:
            raise RenderError("AddRenderJob returned no job id")
        job = next((j for j in d.call(p.GetRenderJobList) or [] if j.get("JobId") == job_id), None)
        if job is None:
            raise RenderError(f"job {job_id} not in GetRenderJobList")
        self.report["job"] = job
        bad = job_mismatches(job, job_expect(self.canvas), self.out)
        if bad:
            raise RenderError(f"queued job {job_id} does not match: " + "; ".join(bad))
        return job_id

    def render(self, job_id: str, poll: float = 1.0, max_wait: float = 1800.0) -> dict:
        d, p = self.d, self.d.project
        t0 = time.monotonic()
        if not d.call(p.StartRendering, [job_id]):
            raise RenderError(f"StartRendering([{job_id}]) returned False")
        last = None
        status: dict = {}
        while time.monotonic() - t0 < max_wait:
            status = d.call(p.GetRenderJobStatus, job_id) or {}
            state, pct = status.get("JobStatus"), status.get("CompletionPercentage")
            if (state, pct) != last:
                eta = status.get("EstimatedTimeRemainingInMs")
                print(f"  {time.monotonic() - t0:6.1f}s  {state:<10} {pct if pct is not None else '-':>3}%"
                      + (f"  eta {eta / 1000:.0f}s" if eta else ""), flush=True)
                last = (state, pct)
            if state in DONE:
                break
            time.sleep(poll)
        else:
            d.call(p.StopRendering)
            raise RenderError(f"render did not finish in {max_wait:.0f}s: {status}")
        status = dict(status, wall_s=round(time.monotonic() - t0, 1))
        self.report["status"] = status
        if status.get("JobStatus") != "Complete":
            raise RenderError(f"render ended with {status}")
        if not self.out.exists():
            raise RenderError(f"render reported Complete but {self.out} does not exist")
        return status

    def restore_page(self) -> None:
        if self.d is None or not getattr(self, "page", None):
            return
        try:
            if self.d.call(self.d.resolve.GetCurrentPage) != self.page:
                self.d.call(self.d.resolve.OpenPage, self.page)
            self.report["page_restored"] = self.page
        except Exception as exc:  # noqa: BLE001 - cosmetic
            self.report["notes"].append(f"could not restore page {self.page!r}: {exc}")

    def run(self, check: bool, fix_loudness: bool) -> int:
        code = 0
        try:
            self.connect()
            print(f"project {self.project_name}  timeline {self.reel}  {self.frames} frames "
                  f"({self.frames / self.fps:.2f} s)  -> {self.out}")
            self.ensure_preset()
            job_id = self.queue()
            print(f"preset {self.preset} ({self.report['preset_action']}): {self.fmt}/{self.codec} "
                  f"{self.canvas.name} @{self.fps}, {self.video_kbps / 1000:g} Mbit/s cap, job {job_id}")
            status = self.render(job_id)
            print(f"rendered in {status.get('TimeTakenToRenderInMs', 0) / 1000:.1f} s "
                  f"(wall {status['wall_s']} s): {self.out}")
            self.d.save()
        except Exception as exc:  # noqa: BLE001 - reported, exit code says it
            self.report["error"] = f"{type(exc).__name__}: {exc}"
            print(f"ERROR: {self.report['error']}", file=sys.stderr)
            code = 1
        finally:
            self.restore_page()
        if code == 0 and check:
            print()
            code = render_check.run(self.out, expect_duration=self.frames / self.fps, fix=fix_loudness,
                                    report=self.out.parent / "render-check.json",
                                    expected=render_check.expected_for(self.canvas))
            self.report["check"] = "PASS" if code == 0 else "FAIL"
        for n in self.report["notes"]:
            print(f"note: {n}")
        self.out.parent.mkdir(parents=True, exist_ok=True)
        (self.out.parent / "render-report.json").write_text(json.dumps(self.report, indent=2, ensure_ascii=False,
                                                                       default=repr))
        return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.render", description=__doc__.splitlines()[0])
    ap.add_argument("reel_dir", help="reels/<reel>/ inside the Walk folder")
    ap.add_argument("--walk", help="Walk folder with clip_manifest.json (default: two levels up)")
    ap.add_argument("--preset", help="render preset to create/update (default cf-instagram-<w>x<h> of the canvas)")
    ap.add_argument("--canvas", help="output size WxH overriding style.json canvas, e.g. 1080x1920 for a "
                                     "comparison render (fps and bitrate table from style.json)")
    ap.add_argument("--out", help="output .mp4 (default: <reel_dir>/out/<reel>.mp4)")
    ap.add_argument("--project-name", help="Resolve project (default: cf-<walk>-<reel>)")
    ap.add_argument("--no-check", action="store_true", help="skip cf.render_check")
    ap.add_argument("--fix-loudness", action="store_true",
                    help="pass --fix-loudness to render_check (writes <reel>.normalized.mp4)")
    args = ap.parse_args(argv)
    reel_dir = Path(args.reel_dir).expanduser().resolve()
    walk_dir = Path(args.walk).expanduser().resolve() if args.walk else reel_dir.parent.parent
    if not (walk_dir / "clip_manifest.json").exists():
        print(f"no clip_manifest.json in {walk_dir}", file=sys.stderr)
        return 2
    try:
        r = Renderer(reel_dir, walk_dir, args.preset, Path(args.out) if args.out else None, args.project_name,
                     canvas=args.canvas)
    except (RenderError, ValueError) as exc:
        print(exc, file=sys.stderr)
        return 2
    return r.run(check=not args.no_check, fix_loudness=args.fix_loudness)


if __name__ == "__main__":
    sys.exit(main())
