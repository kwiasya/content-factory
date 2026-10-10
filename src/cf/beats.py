"""Beat grid of a Track: beats, downbeats, energy, sections, drop and the end of the quiet intro.

    python -m cf.beats <track.wav> -o beats.json [--window 0:60] [--device auto|mps|cpu]
                       [--sections auto|allin1|energy] [--click beats_check.wav [--click-s 30]]

Tools (docs/research/05-music-and-sound/result-a.md, Table B): Beat This! (CPJKU,
``beat-this``) for beats and downbeats; librosa-free numpy RMS for the energy curve;
``all-in-one-infer`` for labelled sections when it is installed and runs, otherwise
sections derived from the energy curve on the downbeat grid (``sections_source`` says
which). Output keys:

- ``bpm``: 60 / median beat interval (inside the window).
- ``beats``, ``downbeats``: seconds from the start of the file (not of the window).
- ``energy``: ``{"hop_s": 0.5, "values": [...]}``, RMS of non-overlapping 0.5 s windows of
  the whole file, normalized to the file's maximum (1.0).
- ``sections``: ``[{"label", "start", "end", "energy"}]`` inside the window.
- ``drop``: the largest positive energy jump (mean of the bar after minus the bar before)
  at a section start or downbeat.
- ``intro_end``: the first downbeat at or after the first 0.5 s window whose energy is
  above ``INTRO_LEVEL`` (35 %) of the file maximum: the quiet start to skip.
- ``sanity``: beat-interval median / std / coefficient of variation and the BPM check,
  for the whole window and for its first 30 s.

``--click`` writes a check file: the first ``--click-s`` seconds of the Track with short
sine blips on the beats (1 kHz) and downbeats (1.6 kHz), mixed by ffmpeg.

The pure parts (``rms_curve``, ``intro_end``, ``energy_sections``, ``find_drop``,
``grid_sanity``, ``parse_window``) are unit-tested in ``tests/test_beats.py``.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

import numpy as np

HOP_S = 0.5
INTRO_LEVEL = 0.35
LOW_LEVEL = 0.45   # bar energy below this (x file max) is a "low" section
HIGH_LEVEL = 0.75  # at or above this it is "high"
BPM_RANGE = (60.0, 180.0)
CV_MAX = 0.03
FFMPEG = shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


# -- pure helpers ------------------------------------------------------------------
def parse_window(spec: str | None, duration: float) -> tuple[float, float]:
    """``"a:b"`` (seconds; either side may be empty) -> (start, end) clipped to the file."""
    if not spec:
        return 0.0, duration
    a, _, b = spec.partition(":")
    start = float(a) if a.strip() else 0.0
    end = float(b) if b.strip() else duration
    start, end = max(0.0, start), min(duration, end)
    if end <= start:
        raise ValueError(f"empty window {spec!r} for a {duration:.1f} s file")
    return start, end


def to_mono(signal: np.ndarray) -> np.ndarray:
    return signal.mean(axis=1) if signal.ndim == 2 else signal


def rms_curve(mono: np.ndarray, sr: int, hop_s: float = HOP_S) -> np.ndarray:
    """RMS of non-overlapping ``hop_s`` windows, normalized to the maximum (0..1)."""
    n = int(round(hop_s * sr))
    count = int(np.ceil(len(mono) / n))
    padded = np.zeros(count * n, dtype=np.float64)
    padded[: len(mono)] = mono
    rms = np.sqrt((padded.reshape(count, n) ** 2).mean(axis=1))
    peak = rms.max()
    return rms / peak if peak > 0 else rms


def mean_energy(energy: np.ndarray, a: float, b: float, hop_s: float = HOP_S) -> float:
    """Mean of the energy windows that start in [a, b)."""
    i, j = int(np.floor(a / hop_s)), int(np.ceil(b / hop_s))
    seg = energy[max(0, i): max(i + 1, j)]
    return float(seg.mean()) if len(seg) else 0.0


def intro_end(energy: np.ndarray, downbeats: list[float], level: float = INTRO_LEVEL,
              hop_s: float = HOP_S, start: float = 0.0) -> float | None:
    """First downbeat at or after the first window (from ``start``) whose energy exceeds ``level``."""
    first = next((i * hop_s for i, e in enumerate(energy) if e > level and i * hop_s >= start - 1e-9), None)
    if first is None:
        return None
    return next((float(d) for d in downbeats if d >= first - 1e-6), None)


def grid_sanity(beats: list[float], upto: float | None = None, after: float = 0.0) -> dict:
    """Beat-interval statistics (optionally only for beats in [after, upto])."""
    b = np.asarray([x for x in beats if x >= after - 1e-9 and (upto is None or x <= upto + 1e-9)], dtype=float)
    if len(b) < 3:
        return {"beats": int(len(b)), "ok": False, "why": "fewer than 3 beats"}
    ibi = np.diff(b)
    med, std = float(np.median(ibi)), float(np.std(ibi))
    bpm = 60.0 / med
    cv = std / med
    return {"beats": int(len(b)), "from_s": round(float(b[0]), 3), "to_s": round(float(b[-1]), 3),
            "ibi_median_s": round(med, 4), "ibi_std_s": round(std, 4), "ibi_cv": round(cv, 4),
            "bpm": round(bpm, 2), "cv_ok": cv < CV_MAX, "bpm_ok": BPM_RANGE[0] <= bpm <= BPM_RANGE[1],
            "ok": cv < CV_MAX and BPM_RANGE[0] <= bpm <= BPM_RANGE[1]}


def bar_level(e: float) -> str:
    return "low" if e < LOW_LEVEL else ("high" if e >= HIGH_LEVEL else "mid")


def energy_sections(energy: np.ndarray, downbeats: list[float], start: float, end: float,
                    hop_s: float = HOP_S, min_bars: int = 2) -> list[dict]:
    """Sections from the energy curve on the downbeat grid.

    Each bar (downbeat to downbeat) gets a level (low / mid / high) from its mean energy;
    runs of bars with the same level merge into a section, and a run shorter than
    ``min_bars`` joins the previous section. The first section is labelled ``intro``
    when it is low. Without downbeats the whole window is one section.
    """
    edges = [start] + [d for d in downbeats if start + 1e-6 < d < end - 1e-6] + [end]
    bars = [(a, b, mean_energy(energy, a, b, hop_s)) for a, b in zip(edges, edges[1:]) if b - a > 1e-6]
    runs: list[list[Any]] = []
    for a, b, e in bars:
        lvl = bar_level(e)
        if runs and runs[-1][0] == lvl:
            runs[-1][2] = b
            runs[-1][3] += 1
        else:
            runs.append([lvl, a, b, 1])
    merged: list[list[Any]] = []
    for r in runs:
        if merged and r[3] < min_bars:
            merged[-1][2] = r[2]
            merged[-1][3] += r[3]
        elif merged and merged[-1][0] == r[0]:
            merged[-1][2] = r[2]
            merged[-1][3] += r[3]
        else:
            merged.append(list(r))
    out = []
    for i, (lvl, a, b, nbars) in enumerate(merged):
        label = "intro" if i == 0 and lvl == "low" else lvl
        out.append({"label": label, "start": round(a, 3), "end": round(b, 3), "bars": nbars,
                    "energy": round(mean_energy(energy, a, b, hop_s), 3)})
    return out


def find_drop(energy: np.ndarray, downbeats: list[float], sections: list[dict], start: float, end: float,
              hop_s: float = HOP_S) -> dict | None:
    """Largest positive jump (bar after minus bar before) at a section start or downbeat."""
    db = [d for d in downbeats if start - 1e-6 <= d <= end + 1e-6]
    bar = float(np.median(np.diff(db))) if len(db) > 1 else 2.0
    cands = sorted({round(float(d), 3) for d in db} | {s["start"] for s in sections})
    best = None
    for t in cands:
        if t - bar < start - 1e-6 or t + bar > end + 1e-6:
            continue
        before, after = mean_energy(energy, t - bar, t, hop_s), mean_energy(energy, t, t + bar, hop_s)
        jump = after - before
        if jump > 0 and (best is None or jump > best["jump"]):
            best = {"t": t, "jump": round(jump, 3), "energy_before": round(before, 3),
                    "energy_after": round(after, 3),
                    "on": "section" if any(abs(s["start"] - t) < 1e-3 for s in sections) else "downbeat"}
    return best


def click_track(beats: list[float], downbeats: list[float], sr: int, duration: float,
                blip_s: float = 0.04) -> np.ndarray:
    """Mono click signal: 1 kHz blips on beats, 1.6 kHz on downbeats, 40 ms with a decay."""
    out = np.zeros(int(duration * sr) + 1, dtype=np.float32)
    n = int(blip_s * sr)
    t = np.arange(n) / sr
    env = np.exp(-t / (blip_s / 4))
    down = {round(d, 3) for d in downbeats}
    for b in beats:
        if b >= duration:
            break
        f = 1600.0 if round(b, 3) in down else 1000.0
        i = int(b * sr)
        seg = (0.6 * np.sin(2 * np.pi * f * t) * env).astype(np.float32)
        out[i: i + n] += seg[: len(out) - i]
    return out


# -- runners -----------------------------------------------------------------------
def run_beat_this(signal: np.ndarray, sr: int, device: str) -> tuple[list[float], list[float], str]:
    import torch  # noqa: PLC0415
    from beat_this.inference import Audio2Beats  # noqa: PLC0415

    devices = [device] if device != "auto" else (["mps", "cpu"] if torch.backends.mps.is_available() else ["cpu"])
    last: Exception | None = None
    for dev in devices:
        try:
            beats, downbeats = Audio2Beats(checkpoint_path="final0", device=dev, dbn=False)(signal, sr)
            return [float(x) for x in beats], [float(x) for x in downbeats], dev
        except Exception as exc:  # noqa: BLE001 - fall back to the next device
            last = exc
    raise RuntimeError(f"Beat This! failed on {devices}: {last}")


def run_allin1(window_wav: Path, offset: float, work: Path) -> list[dict]:
    """Labelled sections from all-in-one-infer (CPU; Demucs inside, so one window at a time)."""
    import allin1_infer  # noqa: PLC0415

    res = allin1_infer.analyze(str(window_wav), device="cpu", demix_dir=str(work / "demix"),
                               spec_dir=str(work / "spec"), multiprocess=False)
    return [{"label": s.label, "start": round(s.start + offset, 3), "end": round(s.end + offset, 3)}
            for s in res.segments]


def write_click(track: Path, out: Path, beats: list[float], downbeats: list[float], seconds: float) -> None:
    import soundfile as sf  # noqa: PLC0415

    info = sf.info(str(track))
    sr = info.samplerate
    clicks = click_track(beats, downbeats, sr, seconds)
    with tempfile.TemporaryDirectory() as tmp:
        cw = Path(tmp) / "clicks.wav"
        sf.write(str(cw), clicks, sr)
        out.parent.mkdir(parents=True, exist_ok=True)
        cmd = [FFMPEG, "-v", "error", "-y", "-t", f"{seconds}", "-i", str(track), "-i", str(cw),
               "-filter_complex", "[1:a]aformat=channel_layouts=stereo[c];[0:a][c]amix=inputs=2:normalize=0[m]",
               "-map", "[m]", "-t", f"{seconds}", "-c:a", "pcm_s16le", str(out)]
        subprocess.run(cmd, check=True)


def analyze(track: Path, window: str | None = None, device: str = "auto", sections_mode: str = "auto",
            log: Any = print) -> dict:
    import soundfile as sf  # noqa: PLC0415

    signal, sr = sf.read(str(track), dtype="float32", always_2d=False)
    duration = len(signal) / sr
    start, end = parse_window(window, duration)
    mono = to_mono(signal)
    energy = rms_curve(mono, sr)
    seg = signal[int(start * sr): int(end * sr)]

    t0 = time.monotonic()
    beats, downbeats, dev = run_beat_this(seg, sr, device)
    beats = [round(b + start, 3) for b in beats]
    downbeats = [round(d + start, 3) for d in downbeats]
    log(f"Beat This! on {dev}: {len(beats)} beats, {len(downbeats)} downbeats in "
        f"{start:g}-{end:g} s ({time.monotonic() - t0:.1f} s)")

    notes: list[str] = []
    sections: list[dict] | None = None
    source = "energy"
    if sections_mode in ("auto", "allin1"):
        t0 = time.monotonic()
        try:
            with tempfile.TemporaryDirectory() as tmp:
                wav = Path(tmp) / "window.wav"
                sf.write(str(wav), seg, sr)
                sections = run_allin1(wav, start, Path(tmp))
            source = "all-in-one-infer"
            log(f"all-in-one-infer: {len(sections)} sections ({time.monotonic() - t0:.1f} s)")
        except Exception as exc:  # noqa: BLE001 - fall back to the energy curve
            notes.append(f"all-in-one-infer unavailable ({type(exc).__name__}: {str(exc)[:200]}); "
                         "sections derived from the RMS energy curve on the downbeat grid")
            if sections_mode == "allin1":
                raise
    energy_secs = energy_sections(energy, downbeats, start, end)
    if sections is None:
        sections = energy_secs
    else:
        for s in sections:
            s["energy"] = round(mean_energy(energy, s["start"], s["end"]), 3)

    drop = find_drop(energy, downbeats, sections, start, end)
    ie = intro_end(energy, downbeats, start=start)
    window_sanity = grid_sanity(beats)
    first30 = grid_sanity(beats, upto=start + 30.0)
    after_intro = grid_sanity(beats, after=ie, upto=(ie + 30.0)) if ie is not None else None
    bpm = window_sanity.get("bpm")
    return {
        "schema": "cf-beats/1",
        "track": str(track),
        "duration_s": round(duration, 3),
        "sample_rate": sr,
        "window": [round(start, 3), round(end, 3)],
        "device": dev,
        "bpm": bpm,
        "beats": beats,
        "downbeats": downbeats,
        "energy": {"hop_s": HOP_S, "values": [round(float(x), 4) for x in energy]},
        "sections_source": source,
        "sections": sections,
        "energy_sections": energy_secs,
        "drop": drop,
        "intro_level": INTRO_LEVEL,
        "intro_end": ie,
        "sanity": {"window": window_sanity, "first_30s": first30, "30s_after_intro": after_intro},
        "notes": notes,
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.beats", description=__doc__.splitlines()[0])
    ap.add_argument("track", help="the Track (WAV)")
    ap.add_argument("-o", "--out", help="beats.json (default: next to the Track)")
    ap.add_argument("--window", help="analyse only start:end seconds, e.g. 0:60")
    ap.add_argument("--device", default="auto", help="auto (mps, then cpu) | mps | cpu")
    ap.add_argument("--sections", default="auto", choices=("auto", "allin1", "energy"),
                    help="auto: all-in-one-infer, falling back to the energy curve")
    ap.add_argument("--click", help="also write a click-track check WAV here")
    ap.add_argument("--click-s", type=float, default=30.0, help="length of the click check (s)")
    args = ap.parse_args(argv)
    track = Path(args.track).expanduser().resolve()
    out = Path(args.out).expanduser().resolve() if args.out else track.with_name("beats.json")
    res = analyze(track, args.window, args.device, args.sections)
    out.write_text(json.dumps(res, indent=1))
    if args.click:
        write_click(track, Path(args.click).expanduser(), res["beats"], res["downbeats"], args.click_s)
        print(f"click check: {args.click}")
    s = res["sanity"]
    print(f"bpm {res['bpm']}  beats {len(res['beats'])}  downbeats {len(res['downbeats'])}  "
          f"intro_end {res['intro_end']}  drop {res['drop']}")
    for k, v in s.items():
        if v:
            print(f"sanity {k:<16} median {v.get('ibi_median_s')} s  std {v.get('ibi_std_s')} s  "
                  f"cv {v.get('ibi_cv')}  bpm {v.get('bpm')}  {'OK' if v.get('ok') else 'CHECK'}")
    print(f"sections ({res['sections_source']}):")
    for sec in res["sections"]:
        print(f"  {sec['label']:<8} {sec['start']:>7.2f}-{sec['end']:<7.2f} energy {sec.get('energy')}")
    for n in res["notes"]:
        print(f"note: {n}")
    print(f"wrote {out}")
    return 0 if s["window"].get("ok") else 1


if __name__ == "__main__":
    sys.exit(main())
