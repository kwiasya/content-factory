"""Build a Shot log (`reel-shotlog/1.2`) for one proxy, or for every proxy of a Walk.

Usage:
  python -m cf.shotlog <proxy.mp4> [--manifest clip_manifest.json] [-o shotlog/<clip>.json]
  python -m cf.shotlog --all <walk_dir> [--force | --speech-only]
  python -m cf.shotlog <proxy.mp4> --source <media_file> -o <out.json>

The third form is for one file outside a Walk (e.g. a downloaded Reference): no
clip_manifest.json; the clip header (fps, duration, rotation, color tags) comes from
cf.probe.probe_file on the source, the clip id is the source's stem, and speech is read
from the source's audio. A proxy counts as inside a Walk only when it sits in a
directory named proxy/; outside a Walk there are no Walk speech levels and no
overrides.json, and -o is required. From Python:
analyze_proxy(proxy, source=media) -> dict, then write_json(data, out).

Chain per clip (one clip at a time, models released between clips):
  cf.metrics.ffstats  exposure, blur, hard cuts       (one ffmpeg pass)
  cf.metrics.people   YOLO nano person tracks, 3 fps
  cf.metrics.motion   OpenCV global motion, 10 fps    (person boxes masked out)
  cf.metrics.vision   Apple Vision aesthetics, faces  (tools/vision-score, optional)
  cf.metrics.speech   Whisper words in the RAW clip's audio (model loaded once per --all run),
                      segment levels; face landmarks on the proxy at 5 fps for clips with speech
  cf.metrics.speech_side  near (behind the camera) / far (on camera) per segment,
                      normalised per Walk (the operator's voice is the loudest)
then cf.scoring: usable / quality per 1 s bin, 2-5 s candidate segments, rejects,
and last the author's <walk>/shotlog/overrides.json.
Speech is a soft flag (the author talking behind the camera; music covers it); only a
second of on-camera speech is unusable (`speech_on_camera`, until a voiceover phase).
Schema: docs/research/04-video-understanding-shot-quality/result-a.md section C,
plus 1.1: per_second.speech, top-level speech_segments and speech_text;
plus 1.2: per_second.speech_on_camera, per segment side / side_confidence / rms_dbfs /
mouth_open_var, summary.speech_on_camera_s, top-level overrides.
1.0 and 1.1 logs stay readable (no speech_on_camera means nothing is rejected for
speech); `--all` adds only the speech part to them.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import platform
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from cf import scoring
from cf.probe import probe_file
from cf.metrics import ffstats, motion, people, speech, speech_side, vision
from cf.metrics.common import ProxyInfo, ffmpeg_bin, n_bins, probe_proxy, tool_version

SCHEMA = "reel-shotlog/1.2"
GENERATOR = "cf.shotlog 0.3"
OVERRIDES = "overrides.json"
APPROX_SUFFIX = "_approx"

log = logging.getLogger("cf.shotlog")


# ----------------------------------------------------------------------------
# Clip header


def clip_id(proxy: Path) -> str:
    stem = proxy.stem
    return stem[: -len(APPROX_SUFFIX)] if stem.endswith(APPROX_SUFFIX) else stem


def find_manifest_entry(manifest: dict | None, cid: str) -> dict | None:
    if not manifest:
        return None
    for c in manifest.get("clips", []):
        if Path(c.get("file", "")).stem == cid:
            return c
    return None


def bit_depth(pix_fmt: str | None) -> int | None:
    if not pix_fmt:
        return None
    for depth in (16, 12, 10):
        if f"p{depth}" in pix_fmt:
            return depth
    return 8


def clip_header(proxy: Path, info: ProxyInfo, entry: dict | None, source: str = "manifest") -> dict:
    """Clip header from a manifest-style entry (`source` names where it came from), else from the proxy."""
    cid = Path(entry["file"]).stem if entry and source != "manifest" else clip_id(proxy)
    if entry:
        fps = entry.get("fps")
        dw, dh = entry.get("display_width"), entry.get("display_height")
        profile = entry.get("color_profile")
        return {
            "id": cid,
            "path": entry.get("path"),
            "proxy": str(proxy),
            "device": {"make": (entry.get("device") or {}).get("make"), "model": (entry.get("device") or {}).get("model")},
            "created": entry.get("creation_time"),
            "duration_s": round(info.duration_s, 3),
            "source_duration_s": entry.get("duration_s"),
            "fps": fps,
            "vfr": entry.get("vfr"),
            "slowmo": bool(fps and fps >= 100),
            "color": {
                "transfer": entry.get("color_transfer"),
                "primaries": entry.get("color_primaries"),
                "dolby_vision": entry.get("dovi") is not None,
                "bit_depth": bit_depth(entry.get("pix_fmt")),
                "log": profile if profile in ("apple_log", "dji_dlog", "dji_dlog2") else None,
                "profile": profile,
            },
            "orientation": "portrait" if (dw and dh and dh > dw) else "landscape" if (dw and dh) else None,
            "gps": entry.get("gps"),
            "header_source": source,
        }
    return {
        "id": cid,
        "path": None,
        "proxy": str(proxy),
        "device": {"make": None, "model": None},
        "created": info.creation_time,
        "duration_s": round(info.duration_s, 3),
        "fps": round(info.fps, 3) if info.fps else None,
        "vfr": None,
        "slowmo": bool(info.fps and info.fps >= 100),
        "color": None,
        "orientation": "portrait" if info.height > info.width else "landscape",
        "gps": None,
        "header_source": "ffprobe(proxy)",
    }


# ----------------------------------------------------------------------------
# Segments


def _mean(vals, default=0.0) -> float:
    v = [x for x in vals if x is not None]
    return float(np.mean(v)) if v else default


def _reason(comp_mean: dict, mtag: str, pace: str, ps: dict, s: int, e: int, light: dict, subject: bool) -> str:
    parts = []
    stab = comp_mean["stability"]
    parts.append(("steady " if stab is not None and stab > 0.8 else "") + mtag.replace("_", " ") + f", {pace} pace")
    sharp = comp_mean["sharp"]
    if sharp is not None:
        parts.append("sharp" if sharp > 0.7 else "soft" if sharp < 0.4 else "ok sharpness")
    expo = comp_mean["exposure"]
    parts.append("well exposed" if expo > 0.8 else "exposure ok" if expo > 0.5 else "exposure weak")
    if comp_mean["aes"] is not None:
        parts.append(f"aes {comp_mean['aes'] * 2 - 1:+.2f}")
    if light.get("tag"):
        parts.append(light["tag"].replace("_", " "))
    persons = max(ps["persons"][s:e] or [0])
    if persons == 0:
        parts.append("no people")
    elif subject:
        parts.append("author on camera")
    else:
        parts.append(f"{persons} people")
    hi = max(ps["clip_hi_pct"][s:e] or [0])
    if hi > 1.0:
        parts.append(f"highlights {hi:.1f}% clipped")
    return ", ".join(parts)


def build_segments(ps: dict, comps: list[dict], q: list[float], usable: list[bool], events: list[dict],
                   header: dict, subject: dict, aes_available: bool, p: scoring.Params) -> list[dict]:
    types = [m["type"] if m else None for m in ps["motion"]]
    windows = scoring.select_windows(q, usable, types, p, duration_s=header["duration_s"])
    segs = []
    for k, w in enumerate(windows, 1):
        s, e = w["bins"]
        cm = {key: (None if all(c[key] is None for c in comps[s:e]) else round(_mean([c[key] for c in comps[s:e]]), 3))
              for key in scoring.WEIGHTS}
        mot = ps["motion"][s:e]
        mtag = scoring.motion_tag(mot, ps["shake_px"][s:e], p)
        speed = _mean([m["speed"] for m in mot if m and m.get("speed") is not None], None)
        pace = scoring.pace_label(speed)
        light = scoring.light_tag(
            _mean(ps["luma_mean"][s:e]), _mean(ps["sat"][s:e]), _mean(ps["warmth"][s:e]),
            _mean(ps["contrast"][s:e]), header.get("created"), header.get("gps"),
        )
        persons = max(ps["persons"][s:e] or [0])
        is_subject = subject.get("dominated", False) and persons > 0
        tags = [mtag]
        if light["tag"]:
            tags.append(light["tag"])
        tags.append("no_people" if persons == 0 else "author_on_camera" if is_subject else "crowd" if persons >= 4 else "people")
        in_ev = [ev for ev in events if w["in_s"] <= ev["t"] < w["out_s"]]
        flags = []
        if any(ev["type"] == "stranger_closeup" for ev in in_ev):
            flags.append("stranger_closeup")
        if any(ev["type"] == "person_enter" for ev in in_ev):
            flags.append("person_enter")
        if not aes_available:
            flags.append("aes_missing")
        if light["confidence"] < 0.4:
            flags.append("light_low_confidence")
        if max(ps["clip_hi_pct"][s:e] or [0]) > 1.0:
            flags.append("highlights_near_clip")
        if any(ps.get("is_utility", [None] * len(q))[s:e]):
            flags.append("utility_frame")
        if any((ps.get("speech") or [False] * len(q))[s:e]):
            flags.append("speech")  # off-camera talk: allowed, music covers it
        segs.append(
            {
                "id": f"s{k}",
                "in_s": w["in_s"],
                "out_s": w["out_s"],
                "source": ["local"],
                "scores": {"quality": round(w["mean_q"], 3), "window_score": w["score"], **cm},
                "tags": tags,
                "motion": {
                    "type": mtag,
                    "pace": pace,
                    "speed": None if speed is None else round(speed, 4),
                    "dx": round(_mean([m["dx"] for m in mot if m]), 1),
                    "div": round(_mean([m["div"] for m in mot if m]), 4),
                    "dir_in": scoring.direction_word(mot[0] if mot else None),
                    "dir_out": scoring.direction_word(mot[-1] if mot else None),
                },
                "light": light,
                "light_confidence": light["confidence"],
                "flags": flags,
                "reason": _reason(cm, mtag, pace, ps, s, e, light, is_subject),
            }
        )
    return segs


# ----------------------------------------------------------------------------
# One clip


def _versions(vision_available: bool, yolo_model: str) -> dict:
    import cv2
    import torch
    import ultralytics

    vbin = vision.binary()
    return {
        "ffmpeg": tool_version(ffmpeg_bin()),
        "opencv": cv2.__version__,
        "numpy": np.__version__,
        "ultralytics": ultralytics.__version__,
        "torch": torch.__version__,
        "yolo_model": yolo_model,
        "vision-score": (
            f"built {datetime.fromtimestamp(vbin.stat().st_mtime).isoformat(timespec='seconds')}" if vbin.exists() else None
        ),
        "python": platform.python_version(),
        "generator": GENERATOR,
    }


def speech_part(data: dict, proxy: Path, transcriber: speech.Transcriber) -> tuple[dict, float]:
    """Run cf.metrics.speech for a clip whose header is already in `data`, then face stats
    per speech segment from the proxy's landmarks; returns (result, seconds)."""
    raw = speech.find_raw(proxy.resolve().parent.parent, data["clip"]["id"], data["clip"].get("path"))
    t0 = time.perf_counter()
    sp = speech.analyze(raw, data["clip"]["duration_s"], transcriber)
    sp["_face_error"] = None
    if sp["speech_segments"]:
        frames, err = vision.landmark_frames(proxy, speech_side.FACE_FPS)
        sp["_face_error"] = err
        for seg in sp["speech_segments"]:
            stats = speech_side.face_stats(frames, seg["start"], seg["end"]) if frames is not None else {
                "face_frames": None, "max_face_h": None, "median_face_h": None, "mouth_open_var": None, "mouth_open_std": None}
            seg.update(stats)
    return sp, time.perf_counter() - t0


def apply_speech(data: dict, sp: dict, seconds: float, transcriber: speech.Transcriber) -> None:
    """Write a cf.metrics.speech result into a Shot log dict (in place) and bump the schema."""
    ps = data["per_second"]
    nb = len(ps["t"])
    ps["speech"] = (sp["speech"] + [False] * nb)[:nb]
    data["speech_segments"] = sp["speech_segments"]
    data["speech_text"] = sp["speech_text"]
    data["speech_noise_floor_dbfs"] = sp.get("_noise_floor_dbfs")
    data["schema"] = SCHEMA
    prov = data.setdefault("provenance", {})
    rt = prov.setdefault("runtime_s", {})
    rt["speech"] = round(seconds, 2)
    rt["total"] = round(sum(v for k, v in rt.items() if k != "total"), 2)
    prov.setdefault("tool_versions", {}).update(transcriber.versions())
    prov.setdefault("notes", {})["speech"] = {
        "rule": f"a second is speech if any Whisper word, padded {speech.PAD_S:g} s each side, overlaps it",
        "source": "first audio stream of the raw clip, 16 kHz mono",
        "model": sp.get("_model"),
        "device": sp.get("_device"),
        "language_hint": sp.get("_lang_hint"),
        "language": sp.get("_language"),
        "audio": sp.get("_audio"),
        "error": sp.get("_error"),
        "faces": f"tools/vision-score --landmarks --faces-only at {speech_side.FACE_FPS:g} fps on the proxy",
        "face_error": sp.get("_face_error"),
    }


def segment_levels(data: dict) -> list[float]:
    return [s["level_dbfs"] for s in data.get("speech_segments") or [] if s.get("level_dbfs") is not None]


def classify_speech(data: dict, walk_ref: float | None, min_conf: float = speech_side.MIN_CONF) -> None:
    """Side per speech segment and per_second.speech_on_camera (in place).

    `walk_ref` is speech_side.walk_reference over every segment of the Walk.
    A second is on-camera speech if a far segment with side_confidence >= min_conf,
    padded speech.PAD_S each side, overlaps it.
    """
    ps = data["per_second"]
    nb = len(ps["t"])
    floor = data.get("speech_noise_floor_dbfs")
    spans = []
    for seg in data.get("speech_segments") or []:
        if "level_dbfs" not in seg:  # a 1.1 log: no levels yet
            continue
        seg.update(speech_side.classify(seg, floor, walk_ref))
        if speech_side.is_on_camera(seg, min_conf):
            spans.append((seg["start"], seg["end"]))
    ps["speech_on_camera"] = speech.speech_bins(spans, nb)
    data.setdefault("provenance", {}).setdefault("notes", {})["speech_side"] = {
        "rule": (f"a second is speech_on_camera if a far segment with side_confidence >= {min_conf:g}, "
                 f"padded {speech.PAD_S:g} s each side, overlaps it; other speech is a soft flag"),
        "walk_ref_dbfs": walk_ref,
        "noise_floor_dbfs": floor,
        "cues": "level vs Walk reference and clip noise floor (raw audio); face size and mouth_open spread (proxy)",
    }


def load_overrides(walk: Path | None) -> dict:
    """<walk>/shotlog/overrides.json: {"<clip>": {"reject": [[in, out, "reason"]], "allow": [[in, out]]}}."""
    if walk is None:
        return {}
    path = walk / "shotlog" / OVERRIDES
    if not path.exists():
        return {}
    data = json.loads(path.read_text())
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected an object keyed by clip id")
    for cid, ov in data.items():
        for key in ov:
            if key not in ("reject", "allow"):
                raise ValueError(f"{path}: {cid}: unknown key {key!r} (use reject / allow)")
        for rng in (ov.get("reject") or []) + (ov.get("allow") or []):
            if len(rng) < 2 or float(rng[1]) <= float(rng[0]):
                raise ValueError(f"{path}: {cid}: bad range {rng!r} (need [in_s, out_s] with out_s > in_s)")
    return data


def finalize(data: dict, params: scoring.Params = scoring.DEFAULT, override: dict | None = None) -> dict:
    """(Re)compute quality, usable, segments, rejects and summary from per_second (in place).

    Shared by a full analysis and by the speech-only pass over an existing log.
    `override` is this clip's entry from overrides.json, applied after every automatic rule.
    """
    ps = data["per_second"]
    header = data["clip"]
    notes = (data.get("provenance") or {}).get("notes") or {}
    subject = notes.get("subject") or {"dominated": False}
    base_flags = [f for f in (data.get("summary") or {}).get("flags", [])
                  if f not in ("speech", "speech_on_camera", "overrides")]
    aes_available = "aes_missing" not in base_flags
    nb = len(ps["t"])

    flags = scoring.apply_overrides(scoring.bin_flags(ps, params), override)
    if override:
        data["overrides"] = override
    else:
        data.pop("overrides", None)
    comps = scoring.components(ps, params)
    q = [round(scoring.quality(c), 3) for c in comps]
    usable = [not f for f in flags]
    ps["quality"] = q
    ps["usable"] = usable

    segments = build_segments(ps, comps, q, usable, data.get("events", []), header, subject, aes_available, params)
    rejects = scoring.reject_runs(flags, header["duration_s"])

    speech_s = speech.speech_seconds(ps.get("speech") or [])
    on_cam_s = sum(1 for f in flags if "speech_on_camera" in f)
    clip_flags = (base_flags + (["speech"] if speech_s else []) + (["speech_on_camera"] if on_cam_s else [])
                  + (["overrides"] if override else []))
    summary = {
        "usable_s": int(sum(usable)),
        "bins": nb,
        "speech_s": speech_s if "speech" in ps else None,
        "speech_on_camera_s": on_cam_s if "speech_on_camera" in ps or override else None,
        "best": segments[0]["id"] if segments else None,
        "reject_clip": not segments,
        "reject_why": None,
        "flags": clip_flags,
        "light": segments[0]["light"] if segments else scoring.light_tag(
            _mean(ps["luma_mean"]), _mean(ps["sat"]), _mean(ps["warmth"]), _mean(ps["contrast"]),
            header.get("created"), header.get("gps")),
    }
    if not segments:
        counts = Counter(w for f in flags for w in f)
        summary["reject_why"] = [w for w, _ in counts.most_common()] or ["shorter than a 2 s window"]
    data["segments"] = segments
    data["rejects"] = rejects
    data["summary"] = summary
    data.setdefault("provenance", {})["params"] = params.as_dict() | {"weights": scoring.WEIGHTS}
    return data


def analyze_proxy(proxy: Path, manifest: dict | None = None, params: scoring.Params = scoring.DEFAULT,
                  transcriber: speech.Transcriber | None = None, other_levels: list[float] | None = None,
                  override: dict | None = None, source: Path | None = None) -> dict:
    """Full analysis of one proxy. `other_levels`: speech levels of the Walk's other clips
    (for the Walk loudness reference); `override`: this clip's overrides.json entry;
    `source`: the media file the proxy was made from, probed for the header instead of a manifest."""
    proxy = proxy.resolve()
    info = probe_proxy(proxy)
    if source is not None:
        header = clip_header(proxy, info, probe_file(Path(source)), "probe(source)")
    else:
        header = clip_header(proxy, info, find_manifest_entry(manifest, clip_id(proxy)))
    nb = n_bins(info.duration_s)
    timings = {}

    t0 = time.perf_counter()
    ff = ffstats.analyze(info)
    timings["ffstats"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    pe = people.analyze(info)
    timings["people"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    mo = motion.analyze(info, person_boxes=pe.pop("_boxes", None))
    timings["motion"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    vi = vision.analyze(info)
    timings["vision"] = time.perf_counter() - t0

    ps = {
        "t": list(range(nb)),
        "luma_mean": ff["luma_mean"],
        "clip_hi_pct": ff["clip_hi_pct"],
        "clip_lo_pct": ff["clip_lo_pct"],
        "blur": ff["blur"],
        "shake_px": mo["shake_px"],
        "roll_deg": mo["roll_deg"],
        "motion": mo["motion"],
        "aes": vi["aes"],
        "persons": pe["persons"],
        "max_person_h": pe["max_person_h"],
        "scd_score": ff["scd_score"],
        "pace": mo["pace"],
        "sat": ff["sat"],
        "warmth": ff["warmth"],
        "contrast": ff["contrast"],
        "faces": vi["faces"],
        "max_face_h": vi["max_face_h"],
        "is_utility": vi["is_utility"],
    }
    clip_flags = []
    if pe["subject"]["dominated"]:
        clip_flags.append("author_on_camera")
    if not vi.get("_available"):
        clip_flags.append("aes_missing")
    if mo.get("_failed"):
        clip_flags.append(f"motion_tracking_failed_pairs={mo['_failed']}")
    data = {
        "schema": SCHEMA,
        "clip": header,
        "per_second": ps,
        "events": pe["events"],
        "speech_segments": [],
        "speech_text": "",
        "segments": [],
        "rejects": [],
        "summary": {"flags": clip_flags},
        "llm": None,
        "provenance": {
            "tool_versions": _versions(vi.get("_available", False), pe.get("_model", "")),
            "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "params": params.as_dict() | {"weights": scoring.WEIGHTS},
            "runtime_s": {k: round(v, 2) for k, v in timings.items()} | {"total": round(sum(timings.values()), 2)},
            "notes": {
                "shake_px": "px at 1080 short side, RMS of camera path minus 1 s local quadratic trend, person boxes masked",
                "blur": "blurdetect edge width at 10 fps, mean per second; higher = blurrier",
                "luma_mean": "0..1 of nominal range on the SDR proxy",
                "aes": "Apple Vision overallScore -1..1 (null if vision-score unavailable)",
                "people": f"{pe.get('_model')} on {pe.get('_device')}, ByteTrack, {people.SAMPLE_FPS:g} fps; no identity: author vs stranger is a heuristic",
                "vision": vi.get("_error"),
                "subject": pe["subject"],
                "motion_pairs": {"total": mo.get("_pairs"), "failed": mo.get("_failed"), "person_masked": mo.get("_masked")},
            },
        },
    }
    own = transcriber is None
    tr = transcriber or speech.Transcriber()
    try:
        sp, sp_s = speech_part(data, proxy, tr)
    finally:
        if own:
            tr.close()
    apply_speech(data, sp, sp_s, tr)
    classify_speech(data, speech_side.walk_reference((other_levels or []) + segment_levels(data)))
    return finalize(data, params, override)


def add_speech(data: dict, proxy: Path, transcriber: speech.Transcriber | None = None,
               params: scoring.Params = scoring.DEFAULT) -> dict:
    """Speech-only pass over an existing (e.g. 1.0) Shot log: other metrics are not recomputed.

    Sides are classified against this clip alone; `run_all` reclassifies against the Walk."""
    own = transcriber is None
    tr = transcriber or speech.Transcriber()
    try:
        sp, sp_s = speech_part(data, proxy, tr)
    finally:
        if own:
            tr.close()
    apply_speech(data, sp, sp_s, tr)
    classify_speech(data, speech_side.walk_reference(segment_levels(data)))
    return finalize(data, params)


def has_speech(data: dict) -> bool:
    return "speech" in (data.get("per_second") or {}) and "speech_segments" in data


def has_speech_side(data: dict) -> bool:
    """1.2 speech: levels per segment (sides can be reclassified without audio)."""
    return (has_speech(data) and "speech_noise_floor_dbfs" in data
            and all("level_dbfs" in s for s in data["speech_segments"]))


def write_json(data: dict, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(out.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    os.replace(tmp, out)


# ----------------------------------------------------------------------------
# Summary line


def summary_line(data: dict, runtime: float | None = None, skipped: bool = False) -> str:
    c = data["clip"]
    segs = data["segments"]
    summ = data.get("summary", {})
    if segs:
        b = segs[0]
        best = f"{b['in_s']:5.1f}-{b['out_s']:5.1f}  q={b['scores']['quality']:.2f}"
        tags = ",".join(b["tags"])
        flags = ",".join(b["flags"] + [f for f in summ.get("flags", []) if f not in b["flags"]])
        more = f"+{len(segs) - 1}" if len(segs) > 1 else ""
    else:
        best = "REJECT".ljust(20)
        tags = "-"
        flags = ",".join(summ.get("reject_why") or [])
        more = ""
    rt = "skipped (up to date)" if skipped else (f"{runtime:5.1f}s" if runtime is not None else "")
    sp, oc = summ.get("speech_s"), summ.get("speech_on_camera_s")
    sp_txt = f"  speech {'-' if sp is None else sp:>2}/{'-' if oc is None else oc:<2}"
    return (f"{c['id']:<12} {c['duration_s']:5.1f}s  usable {summ.get('usable_s', '?'):>2}/{summ.get('bins', '?'):<2}{sp_txt}  "
            f"{best} {more:<3} [{tags}]  {flags or '-'}  {rt}")


def speech_lines(data: dict) -> list[str]:
    """Indented lines with each speech segment and its side, for the --all table."""
    out = []
    for s in data.get("speech_segments", []):
        side = s.get("side")
        side_txt = "?" if side is None else f"{side:<4} {s.get('side_confidence', 0):.2f}"
        if speech_side.is_on_camera(s):
            side_txt += " REJECT"
        lv = s.get("level_dbfs")
        face = s.get("max_face_h")
        mv = s.get("mouth_open_std")
        cues = (f"lvl {'-' if lv is None else f'{lv:.0f}'} dB, face {'-' if face is None else f'{face:.2f}'}, "
                f"mouth sd {'-' if mv is None else f'{mv:.3f}'}")
        out.append(f"{'':<14}speech {s['start']:5.1f}-{s['end']:5.1f}  {side_txt:<16} {cues:<38} {s['text']}")
    return out


def load_manifest(path: Path | None) -> dict | None:
    if path and path.exists():
        return json.loads(path.read_text())
    return None


def walk_levels(walk: Path, exclude: str | None = None) -> list[float]:
    """Speech levels from the Walk's existing Shot logs (for a single-clip run)."""
    out = []
    for f in sorted((walk / "shotlog").glob("*.json")):
        if f.name == OVERRIDES or f.stem == exclude:
            continue
        try:
            out += segment_levels(json.loads(f.read_text()))
        except (json.JSONDecodeError, OSError):
            continue
    return out


def run_all(walk: Path, force: bool = False, params: scoring.Params = scoring.DEFAULT, speech_only: bool = False) -> int:
    """Analyse every proxy of a Walk; the Whisper model is loaded once for the whole run.

    Pass 1, per clip: an up-to-date log without 1.2 speech gets only the speech pass;
    `speech_only` redoes the speech pass on every existing log (others are analysed in full).
    Pass 2, the Walk: the loudness reference over every clip's speech, sides per segment,
    overrides.json, scoring, and every log is rewritten. A run where every log is up to
    date is therefore a cheap re-score after editing overrides.json.
    """
    proxy_dir, out_dir = walk / "proxy", walk / "shotlog"
    proxies = sorted(p for p in proxy_dir.glob("*.mp4") if not p.name.startswith("."))
    if not proxies:
        print(f"no proxies in {proxy_dir}", file=sys.stderr)
        return 1
    try:
        overrides = load_overrides(walk)
    except (ValueError, json.JSONDecodeError) as exc:
        print(f"bad {OVERRIDES}: {exc}", file=sys.stderr)
        return 1
    unknown = sorted(set(overrides) - {clip_id(p) for p in proxies})
    if unknown:
        log.warning("%s names clips with no proxy: %s", OVERRIDES, ", ".join(unknown))
    manifest = load_manifest(walk / "clip_manifest.json")
    if manifest is None:
        log.warning("no clip_manifest.json in %s; clip headers come from ffprobe", walk)
    t_all = time.perf_counter()
    done = speech_done = 0
    logs: list[tuple[dict, Path]] = []
    transcriber = speech.Transcriber()
    try:
        for proxy in proxies:
            cid = clip_id(proxy)
            out = out_dir / f"{cid}.json"
            existing = None
            if not force and out.exists():
                try:
                    existing = json.loads(out.read_text())
                except json.JSONDecodeError:
                    existing = None
            fresh = (existing is not None and out.stat().st_mtime >= proxy.stat().st_mtime
                     and all(k in existing for k in ("clip", "per_second", "segments", "summary")))
            t0 = time.perf_counter()
            try:
                if existing is not None and (speech_only or (fresh and not has_speech_side(existing))):
                    data = add_speech(existing, proxy, transcriber, params)
                    speech_done += 1
                    status = "speech only"
                elif fresh:
                    data = existing
                    status = "up to date"
                else:
                    data = analyze_proxy(proxy, manifest, params, transcriber)
                    done += 1
                    status = "analysed"
            except Exception as exc:  # keep going; one bad clip must not stop the Walk
                log.error("%s failed: %s", proxy.name, exc)
                print(f"{cid:<12} FAILED: {exc}", flush=True)
                continue
            if status != "up to date":
                write_json(data, out)  # provisional until the Walk pass below
            logs.append((data, out))
            print(f"{cid:<12} {status:<12} {time.perf_counter() - t0:5.1f}s", flush=True)
    finally:
        load_s = transcriber.load_s
        transcriber.close()

    ref = speech_side.walk_reference(lv for data, _ in logs for lv in segment_levels(data))
    print(f"\nWalk speech reference {ref} dBFS (median of the {speech_side.REF_TOP_N} loudest segments); "
          f"overrides: {', '.join(sorted(overrides)) or 'none'}\n")
    print(f"{'clip':<12} {'dur':>6}  usable  speech/oncam  best in-out   quality      [tags]  flags")
    for data, out in logs:
        cid = data["clip"]["id"]
        classify_speech(data, ref)
        finalize(data, params, overrides.get(cid))
        write_json(data, out)
        print(summary_line(data), flush=True)
        for line in speech_lines(data):
            print(line, flush=True)
    print(f"\n{len(proxies)} proxies, {done} analysed, {speech_done} speech-only, whisper load {load_s:.1f}s, "
          f"total {time.perf_counter() - t_all:.1f}s -> {out_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.shotlog", description=__doc__.splitlines()[0])
    ap.add_argument("proxy", type=Path, nargs="?", help="proxy .mp4")
    ap.add_argument("--all", type=Path, metavar="WALK_DIR", help="process every <walk>/proxy/*.mp4 into <walk>/shotlog/")
    ap.add_argument("--manifest", type=Path, help="clip_manifest.json (default: ../clip_manifest.json next to proxy/)")
    ap.add_argument("--source", type=Path, metavar="MEDIA",
                    help="the file the proxy was made from; its probe replaces the manifest (one file outside a Walk)")
    ap.add_argument("-o", "--output", type=Path, help="default: <walk>/shotlog/<clip>.json; required outside a Walk")
    ap.add_argument("--force", action="store_true", help="with --all: redo up-to-date logs")
    ap.add_argument("--speech-only", action="store_true",
                    help="with --all: redo only the speech part (Whisper, levels, faces, sides) of existing logs, "
                         "then re-apply shotlog/overrides.json")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO if args.verbose else logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    if args.all:
        if args.force and args.speech_only:
            ap.error("--force and --speech-only exclude each other")
        return run_all(args.all, args.force, speech_only=args.speech_only)
    if not args.proxy:
        ap.error("give a proxy or --all <walk_dir>")
    proxy = args.proxy
    if not proxy.exists():
        ap.error(f"no such file: {proxy}")
    if args.source and not args.source.is_file():
        ap.error(f"no such file: {args.source}")
    walk = proxy.resolve().parent.parent if proxy.resolve().parent.name == "proxy" else None
    if walk is None and not args.output:
        ap.error(f"{proxy} is not in a Walk's proxy/ directory; give -o")
    manifest = load_manifest(args.manifest or (walk / "clip_manifest.json" if walk else None))
    out = args.output or walk / "shotlog" / f"{clip_id(proxy)}.json"
    t0 = time.perf_counter()
    data = analyze_proxy(proxy, manifest, other_levels=walk_levels(walk, clip_id(proxy)) if walk else [],
                         override=load_overrides(walk).get(clip_id(proxy)), source=args.source)
    write_json(data, out)
    print(summary_line(data, time.perf_counter() - t0))
    for line in speech_lines(data):
        print(line)
    print(f"-> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
