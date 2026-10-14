"""People in frame with an Ultralytics YOLO nano model + ByteTrack at ~3 fps.

Per 1 s bin: persons (max simultaneous person boxes), max_person_h (tallest box
as a fraction of frame height). Events: person_enter (a track first seen after
the first sample and seen at least twice), stranger_closeup (a track whose box
height exceeds CLOSEUP_H).

There is no identity recognition. Most Walk footage stars the author (selfies,
tripod shots), so a "subject" is guessed and excluded from stranger_closeup:
the track seen in >= SUBJECT_COVERAGE of samples, and, when the clip is
subject-dominated (a box taller than SUBJECT_H in >= SUBJECT_COVERAGE of
samples), the tallest box of every sample; and, when a subject track exists, a
lone person in a sample (tracker IDs switch after occlusion).

The model is loaded per call and released afterwards (a limit set on the earlier 8 GB M2). Weights
live outside the repo in $CF_MODELS_DIR (default ~/Movies/content-factory/_models)
and are downloaded there by Ultralytics on first use.
"""

from __future__ import annotations

import gc
import os
from pathlib import Path

import cv2
import numpy as np

from cf.metrics.common import ProxyInfo, bin_reduce, n_bins

SAMPLE_FPS = 3.0
CONF = 0.4
IMGSZ = 640
CLOSEUP_H = 0.45
MIN_SIGHTINGS = 2
SUBJECT_COVERAGE = 0.4
SUBJECT_H = 0.35
DEFAULT_MODEL = "yolo26n.pt"  # Ultralytics 8.4 default nano detector


def models_dir() -> Path:
    return Path(os.environ.get("CF_MODELS_DIR", Path.home() / "Movies" / "content-factory" / "_models"))


def model_name() -> str:
    return os.environ.get("CF_YOLO_MODEL", DEFAULT_MODEL)


def _load_model():
    # Keep Ultralytics' anonymous usage analytics off for this process (no settings file change).
    try:
        import ultralytics.utils.events as _events

        _events.events.enabled = False
    except Exception:  # pragma: no cover - analytics module layout differs between versions
        pass
    from ultralytics import YOLO

    d = models_dir()
    d.mkdir(parents=True, exist_ok=True)
    return YOLO(str(d / model_name()))


def side_of(cx: float) -> str:
    return "left" if cx < 1 / 3 else "right" if cx > 2 / 3 else "center"


Det = tuple  # (track_id | None, box_h_frac, cx_frac[, (x1, y1, x2, y2) fractions])


def summarize(samples: list[tuple[float, list[Det]]], nbins: int) -> dict:
    """Turn per-sample detections [(t, [(track_id, box_h_frac, cx_frac, ...), ...])] into bins + events.

    Pure function (tested without a model).
    """
    times = [t for t, _ in samples]
    counts = [len(d) for _, d in samples]
    heights = [max((d[1] for d in dets), default=0.0) for _, dets in samples]
    persons = bin_reduce(times, counts, nbins, np.max)
    max_h = bin_reduce(times, heights, nbins, np.max)
    n = len(samples)

    sightings: dict[int, int] = {}
    for _, dets in samples:
        for d in dets:
            if d[0] is not None:
                sightings[d[0]] = sightings.get(d[0], 0) + 1
    subject_tracks = {tid for tid, c in sightings.items() if n and c / n >= SUBJECT_COVERAGE}
    subject_dominated = bool(n) and sum(h > SUBJECT_H for h in heights) / n >= SUBJECT_COVERAGE

    first_seen: dict[int, tuple[float, float]] = {}
    closeup: dict[int, tuple[float, float]] = {}
    first_t = times[0] if times else 0.0
    for t, dets in samples:
        tallest = max(range(len(dets)), key=lambda k: dets[k][1]) if dets else None
        for k, d in enumerate(dets):
            tid, h, cx = d[0], d[1], d[2]
            if tid is None:
                continue
            first_seen.setdefault(tid, (t, cx))
            # Tracker IDs switch after occlusions; a lone person in a clip that has a
            # subject is taken to be that subject again.
            lone_subject = bool(subject_tracks) and len(dets) == 1
            is_subject = tid in subject_tracks or lone_subject or (subject_dominated and k == tallest)
            if h > CLOSEUP_H and not is_subject:
                prev = closeup.get(tid)
                if prev is None:
                    closeup[tid] = (t, h)
                elif h > prev[1]:
                    closeup[tid] = (prev[0], h)

    events = []
    for tid, (t, cx) in first_seen.items():
        if t > first_t and sightings[tid] >= MIN_SIGHTINGS:
            events.append({"t": round(t, 2), "type": "person_enter", "track": tid, "side": side_of(cx)})
    for tid, (t, h) in closeup.items():
        events.append({"t": round(t, 2), "type": "stranger_closeup", "track": tid, "box_h": round(h, 2)})
    events.sort(key=lambda e: (e["t"], e["type"]))
    return {
        "persons": [0 if v is None else int(v) for v in persons],
        "max_person_h": [0.0 if v is None else round(v, 3) for v in max_h],
        "events": events,
        "tracks": len(first_seen),
        "subject": {
            "dominated": subject_dominated,
            "tracks": sorted(subject_tracks),
            "coverage": round(sum(h > SUBJECT_H for h in heights) / n, 2) if n else 0.0,
        },
    }


def analyze(info: ProxyInfo, device: str | None = None) -> dict:
    nb = n_bins(info.duration_s)
    device = device or os.environ.get("CF_YOLO_DEVICE", "cpu")
    model = _load_model()
    samples: list[tuple[float, list[Det]]] = []
    cap = cv2.VideoCapture(str(info.path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open {info.path}")
    next_t = 0.0
    try:
        while cap.grab():
            t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if t + 1e-6 < next_t:
                continue
            ok, frame = cap.retrieve()
            if not ok:
                continue
            next_t = max(next_t + 1 / SAMPLE_FPS, t + 0.5 / SAMPLE_FPS)
            fh, fw = frame.shape[:2]
            res = model.track(
                frame, persist=True, classes=[0], conf=CONF, imgsz=IMGSZ, device=device,
                tracker="bytetrack.yaml", verbose=False,
            )[0]
            dets = []
            boxes = res.boxes
            if boxes is not None and len(boxes):
                xyxy = boxes.xyxy.cpu().numpy()
                ids = boxes.id.cpu().numpy().astype(int).tolist() if boxes.id is not None else [None] * len(xyxy)
                for (x1, y1, x2, y2), tid in zip(xyxy, ids):
                    box = (float(x1 / fw), float(y1 / fh), float(x2 / fw), float(y2 / fh))
                    dets.append((tid, float((y2 - y1) / fh), float((x1 + x2) / 2 / fw), box))
            samples.append((t, dets))
    finally:
        cap.release()
        del model
        gc.collect()
        try:
            import torch

            if device == "mps":
                torch.mps.empty_cache()
        except Exception:
            pass
    out = summarize(samples, nb)
    out["_samples"] = len(samples)
    out["_boxes"] = [(t, [d[3] for d in dets]) for t, dets in samples]  # for motion masking; not written
    out["_model"] = model_name()
    out["_device"] = device
    return out


if __name__ == "__main__":
    import json
    import sys

    from cf.metrics.common import probe_proxy

    res = analyze(probe_proxy(Path(sys.argv[1])))
    res.pop("_boxes")
    print(json.dumps(res))
