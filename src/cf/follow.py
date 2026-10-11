"""``reframe.mode: follow``: one STATIC canvas-shaped window per shot, placed on the person.

Smart Reframe keyframes Tilt past the source edge and leaves black bands (Mallorca reel-01:
692 px and 644 px), so the default for a landscape clip is a static window chosen here:

1. ``detect``: the Ultralytics nano person detector (the shot-log model, ``cf.metrics.people``)
   with ByteTrack on the proxy frames of the shot's in–out range at ``SAMPLE_FPS``. The subject
   is the track with the largest summed box height (persistent and large); in a frame where that
   track is missing (ID switch after an occlusion) the box nearest its last centre stands in.
   Boxes are fractions of the source width (the proxy has the source's display aspect).
2. ``choose_window``: the window's left edge L in [0, 1 - w] that maximises the number of frames
   whose whole box lies inside [L, L + w]; ties go to the window that holds the LATEST frames
   (the end of a shot is where she looks into the lens); the window is centred in the range of L
   that holds exactly those frames. When no frame fits (a box wider than the window), the window
   with the largest summed box overlap wins, centred on the last frame's box among equals.
3. ``x_for_left``: L as the Script's pan ``x`` (-1 = left edge, 1 = right edge), so the existing
   reframe math gives Pan; L is clamped to [0, 1 - w], so the window never leaves the source.

Pure parts (``subject_boxes``, ``choose_window``, ``coverage``, ``x_for_left``) are unit-tested in
``tests/test_follow.py``; ``detect`` needs the model and the proxies.
"""

from __future__ import annotations

import gc
import math
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

SAMPLE_FPS = 5.0
CONF = 0.1  # low on purpose: ByteTrack associates low-confidence boxes; the subject rule drops strays
IMGSZ = 640
REJOIN_DIST = 0.15  # fraction of width: a box this close to the subject's last centre is the subject
GRID = 2000         # candidate left edges over [0, 1 - w]


@dataclass(frozen=True)
class Box:
    """The subject in one sampled frame: source time and horizontal extent (fractions of width)."""
    t: float
    x1: float
    x2: float

    @property
    def cx(self) -> float:
        return (self.x1 + self.x2) / 2


@dataclass
class FollowResult:
    x: float                    # the Script-scale pan x of the chosen window
    left: float                 # window left edge, fraction of source width
    width: float                # window width, fraction of source width
    frames: int                 # sampled frames
    detected: int               # frames with the subject
    covered: int                # frames whose whole box is inside the window
    coverage_pct: float         # covered / detected (0 when nothing detected)
    fallback: str | None = None  # 'overlap' (no box fits) or 'no_person' (centre)
    covered_times: list[float] = field(default_factory=list)
    missed_times: list[float] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def window_fraction(src_w: float, src_h: float, canvas_w: float, canvas_h: float, zoom: float = 1.0) -> float:
    """Window width as a fraction of the source width: canvas aspect x source height / source width / zoom."""
    return (canvas_w / canvas_h) * src_h / src_w / zoom


def x_for_left(left: float, w: float) -> float:
    """Window left edge (fraction) -> pan x (-1..1). The centre 0.5 + x (0.5 - w/2)."""
    half = 0.5 - w / 2
    if half <= 0:
        return 0.0
    return max(-1.0, min(1.0, (left + w / 2 - 0.5) / half))


def left_for_x(x: float, w: float) -> float:
    return 0.5 + x * (0.5 - w / 2) - w / 2


def _fits(b: Box, left: float, w: float, eps: float = 1e-9) -> bool:
    return b.x1 >= left - eps and b.x2 <= left + w + eps


def coverage(boxes: list[Box | None], left: float, w: float) -> tuple[int, int]:
    """(frames whose whole box lies inside [left, left + w], frames with a box)."""
    det = [b for b in boxes if b is not None]
    return sum(_fits(b, left, w) for b in det), len(det)


def choose_window(boxes: list[Box | None], w: float) -> FollowResult:
    """The static window (width ``w``, fraction of the source) that holds the subject longest.

    ``boxes`` is one entry per sampled frame in time order (None: no subject in that frame).
    """
    w = min(max(w, 1e-6), 1.0)
    hi = 1.0 - w
    frames = len(boxes)
    idx = [i for i, b in enumerate(boxes) if b is not None]
    det = [boxes[i] for i in idx]
    if not det:
        left = hi / 2
        return FollowResult(x=x_for_left(left, w), left=round(left, 5), width=round(w, 5), frames=frames,
                            detected=0, covered=0, coverage_pct=0.0, fallback="no_person")
    # Each frame fits for L in [x2 - w, x1] (when its box is not wider than the window).
    ivals = [(max(0.0, b.x2 - w), min(hi, b.x1)) for b in det]
    best_key: tuple | None = None
    best_set: tuple[int, ...] = ()
    for k in range(GRID + 1):
        left = hi * k / GRID
        s = tuple(j for j, (a, c) in enumerate(ivals) if a - 1e-9 <= left <= c + 1e-9)
        key = (len(s), tuple(sorted(s, reverse=True)))  # more frames, then later frames
        if best_key is None or key > best_key:
            best_key, best_set = key, s
    # Also try every interval endpoint (the grid may straddle a narrow intersection).
    for a, c in ivals:
        for left in (a, c):
            if not 0.0 <= left <= hi:
                continue
            s = tuple(j for j, (a2, c2) in enumerate(ivals) if a2 - 1e-9 <= left <= c2 + 1e-9)
            key = (len(s), tuple(sorted(s, reverse=True)))
            if key > best_key:
                best_key, best_set = key, s
    fallback = None
    if best_set:
        lo_l = max(ivals[j][0] for j in best_set)
        hi_l = min(ivals[j][1] for j in best_set)
        left = (lo_l + hi_l) / 2
    else:
        # No box fits: the window with the most box inside (summed overlap fraction), ties to the end.
        fallback = "overlap"
        best = None
        for k in range(GRID + 1):
            cand = hi * k / GRID
            ov = [max(0.0, min(b.x2, cand + w) - max(b.x1, cand)) / max(b.x2 - b.x1, 1e-9) for b in det]
            # A box wider than the window gives a plateau of equal overlap: centre on the latest box.
            key = (round(sum(ov), 4), -round(abs(cand + w / 2 - det[-1].cx), 6))
            if best is None or key > best[0]:
                best = (key, cand)
        left = best[1]
    left = min(max(left, 0.0), hi)
    cov = [j for j, b in enumerate(det) if _fits(b, left, w)]
    return FollowResult(
        x=round(x_for_left(left, w), 4), left=round(left, 5), width=round(w, 5), frames=frames, detected=len(det),
        covered=len(cov), coverage_pct=round(100.0 * len(cov) / len(det), 1), fallback=fallback,
        covered_times=[round(det[j].t, 2) for j in cov],
        missed_times=[round(b.t, 2) for j, b in enumerate(det) if j not in set(cov)])


def subject_boxes(samples: list[tuple[float, list[tuple[Any, float, float, float]]]]) -> list[Box | None]:
    """Pick the subject per sampled frame from raw detections.

    ``samples``: [(t, [(track_id | None, x1, x2, h), ...])] with x as fractions of width and h the box
    height fraction. The subject track has the largest summed box height; a frame without it takes the
    box nearest the subject's last centre within REJOIN_DIST, else None.
    """
    score: dict[Any, float] = {}
    for _, dets in samples:
        for tid, _x1, _x2, h in dets:
            if tid is not None:
                score[tid] = score.get(tid, 0.0) + h
    subject = max(score, key=lambda k: score[k]) if score else None
    out: list[Box | None] = []
    last_cx: float | None = None
    for t, dets in samples:
        pick = None
        if subject is not None:
            pick = next((d for d in dets if d[0] == subject), None)
        if pick is None and dets:
            if last_cx is None:
                if subject is None:  # no tracks at all: the tallest box
                    pick = max(dets, key=lambda d: d[3])
            else:
                near = min(dets, key=lambda d: abs((d[1] + d[2]) / 2 - last_cx))
                if abs((near[1] + near[2]) / 2 - last_cx) <= REJOIN_DIST:
                    pick = near
        if pick is None:
            out.append(None)
            continue
        b = Box(round(t, 3), max(0.0, float(pick[1])), min(1.0, float(pick[2])))
        last_cx = b.cx
        out.append(b)
    return out


# -- detection (model, proxies) ------------------------------------------------------
class Detector:
    """The nano person detector, loaded once for a build and released with ``close()``."""

    def __init__(self, device: str | None = None):
        from cf.metrics.people import _load_model, model_name  # noqa: PLC0415

        self.device = device or os.environ.get("CF_YOLO_DEVICE", "cpu")
        self.model_name = model_name()
        self._model = _load_model()

    def samples(self, proxy: Path, in_s: float, out_s: float, fps: float = SAMPLE_FPS) -> list[tuple]:
        """Raw detections [(t, [(track_id, x1, x2, h)])] at ``fps`` over [in_s, out_s) of the proxy."""
        import cv2  # noqa: PLC0415

        cap = cv2.VideoCapture(str(proxy))
        if not cap.isOpened():
            raise RuntimeError(f"OpenCV cannot open {proxy}")
        out: list[tuple] = []
        n = max(1, math.floor((out_s - in_s) * fps + 1e-6))
        times = [in_s + (k + 0.5) / fps for k in range(n)]
        try:
            # A fresh tracker per shot (track ids restart; the state lives on the predictor).
            for tr in getattr(getattr(self._model, "predictor", None), "trackers", None) or []:
                tr.reset()
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, in_s - 0.5) * 1000.0)
            k = 0
            while k < len(times) and cap.grab():
                t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
                if t + 1e-3 < times[k]:
                    continue
                ok, frame = cap.retrieve()
                if not ok:
                    continue
                fh, fw = frame.shape[:2]
                res = self._model.track(frame, persist=True, classes=[0], conf=CONF, imgsz=IMGSZ, device=self.device,
                                        tracker="bytetrack.yaml", verbose=False)[0]
                dets = []
                if res.boxes is not None and len(res.boxes):
                    xyxy = res.boxes.xyxy.cpu().numpy()
                    ids = (res.boxes.id.cpu().numpy().astype(int).tolist() if res.boxes.id is not None
                           else [None] * len(xyxy))
                    for (x1, y1, x2, y2), tid in zip(xyxy, ids):
                        dets.append((tid, float(x1 / fw), float(x2 / fw), float((y2 - y1) / fh)))
                out.append((round(t, 3), dets))
                k += 1
        finally:
            cap.release()
        return out

    def close(self) -> None:
        self._model = None
        gc.collect()
