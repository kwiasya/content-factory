"""Global camera motion from a proxy with OpenCV.

Frames are sampled at ~10 fps by timestamp (VFR-safe). For each consecutive pair:
goodFeaturesToTrack + pyramidal LK -> estimateAffinePartial2D (RANSAC), giving
translation dx/dy, rotation and scale about the frame centre. Then per 1 s bin:

  shake_px   RMS of the camera path minus its 1 s local trend, px at 1080 short side
  roll_deg   RMS of the roll angle minus its 1 s local trend
  dx, dy     mean image translation velocity, px/s at 1080 (scene moves left -> dx < 0)
  div        mean log-scale rate per second (>0: scene expands, camera moves forward)
  speed      median feature flow magnitude / frame width per second ("pace")
  type       locked | pan_left | pan_right | forward_walk | pull_back | drift | handheld
"""

from __future__ import annotations

import math

import cv2
import numpy as np

from cf.metrics.common import ProxyInfo, bin_reduce, fill_gaps, n_bins, rounded

SAMPLE_FPS = 10.0
WORK_SHORT_SIDE = 540  # proxies already are; larger inputs get downscaled
MAX_CORNERS = 300
MIN_TRACKED = 12
MIN_FREE_AREA = 0.15  # ignore the person mask if it leaves less of the frame than this

# Per-second classification thresholds (px/s and px at 1080 short side; div per s).
LOCKED_SPEED = 25.0
LOCKED_DIV = 0.02
PAN_SPEED = 90.0
PAN_RATIO = 1.5
DIV_WALK = 0.04
SHAKE_HANDHELD = 6.0


def _local_trend(x: np.ndarray, t: np.ndarray, window_s: float = 1.0) -> np.ndarray:
    """Smooth camera path: local quadratic fit over a centred 1 s window (VFR-safe).

    A plain moving average biases the edges of the clip and turns any smooth
    acceleration (a pan speeding up) into fake shake; a local quadratic fit
    follows intended moves and leaves the >~2 Hz jitter as residual.
    """
    out = np.empty_like(x)
    half = window_s / 2
    for i, ti in enumerate(t):
        sel = (t >= ti - half) & (t <= ti + half)
        ts, xs = t[sel] - ti, x[sel]
        deg = min(2, len(ts) - 1)
        out[i] = np.polyval(np.polyfit(ts, xs, deg), 0.0) if deg > 0 else xs.mean()
    return out


def exclusion_mask(shape: tuple[int, int], boxes: list[tuple[float, float, float, float]] | None) -> np.ndarray | None:
    """Feature mask (255 = allowed) excluding person boxes (fractions, dilated 10%).

    People attached to the camera (selfies) or walking through frame would
    otherwise pull the global fit; None when no boxes or too little is left.
    """
    if not boxes:
        return None
    h, w = shape
    mask = np.full((h, w), 255, np.uint8)
    for x1, y1, x2, y2 in boxes:
        dx, dy = 0.1 * (x2 - x1), 0.1 * (y2 - y1)
        mask[max(0, int((y1 - dy) * h)) : min(h, int((y2 + dy) * h)), max(0, int((x1 - dx) * w)) : min(w, int((x2 + dx) * w))] = 0
    if np.count_nonzero(mask) < MIN_FREE_AREA * mask.size:
        return None
    return mask


def pair_transform(prev: np.ndarray, cur: np.ndarray, mask: np.ndarray | None = None) -> dict | None:
    """Similarity transform prev->cur about the frame centre; None if tracking fails."""
    pts = None
    if mask is not None:
        pts = cv2.goodFeaturesToTrack(prev, maxCorners=MAX_CORNERS, qualityLevel=0.01, minDistance=12, blockSize=7, mask=mask)
    if pts is None or len(pts) < MIN_TRACKED:
        pts = cv2.goodFeaturesToTrack(prev, maxCorners=MAX_CORNERS, qualityLevel=0.01, minDistance=12, blockSize=7)
    if pts is None or len(pts) < MIN_TRACKED:
        return None
    nxt, status, _ = cv2.calcOpticalFlowPyrLK(
        prev, cur, pts, None, winSize=(21, 21), maxLevel=3,
        criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, 0.01),
    )
    ok = status.reshape(-1) == 1
    p0, p1 = pts.reshape(-1, 2)[ok], nxt.reshape(-1, 2)[ok]
    if len(p0) < MIN_TRACKED:
        return None
    h, w = prev.shape
    c = np.array([w / 2, h / 2], dtype=np.float32)
    m, inliers = cv2.estimateAffinePartial2D(p0 - c, p1 - c, method=cv2.RANSAC, ransacReprojThreshold=2.0)
    if m is None:
        return None
    a, b = float(m[0, 0]), float(m[1, 0])
    flow = np.linalg.norm(p1 - p0, axis=1)
    return {
        "dx": float(m[0, 2]),
        "dy": float(m[1, 2]),
        "rot": math.atan2(b, a),
        "scale": math.hypot(a, b),
        "flow_med": float(np.median(flow)),
        "inliers": int(inliers.sum()) if inliers is not None else 0,
    }


def classify(dx: float, dy: float, div: float, shake: float) -> str:
    """Per-second motion type from velocity (px/s @1080), divergence (/s) and shake (px)."""
    speed = math.hypot(dx, dy)
    if speed < LOCKED_SPEED and abs(div) < LOCKED_DIV and shake < SHAKE_HANDHELD / 2:
        return "locked"
    if abs(dx) > PAN_SPEED and abs(dx) > PAN_RATIO * abs(dy) and abs(div) < DIV_WALK * 1.5:
        # image content moves left when the camera pans right
        return "pan_right" if dx < 0 else "pan_left"
    if div > DIV_WALK:
        return "forward_walk"
    if div < -DIV_WALK:
        return "pull_back"
    if shake > SHAKE_HANDHELD:
        return "handheld"
    return "drift"


def _sample_frames(info: ProxyInfo):
    """Yield (t_seconds, gray_frame) at ~SAMPLE_FPS, chosen by frame timestamp."""
    cap = cv2.VideoCapture(str(info.path))
    if not cap.isOpened():
        raise RuntimeError(f"OpenCV cannot open {info.path}")
    scale = min(1.0, WORK_SHORT_SIDE / info.short_side)
    next_t = 0.0
    try:
        while cap.grab():
            t = cap.get(cv2.CAP_PROP_POS_MSEC) / 1000.0
            if t + 1e-6 < next_t:
                continue
            ok, frame = cap.retrieve()
            if not ok:
                continue
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if scale < 1.0:
                gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
            yield t, gray
            next_t = max(next_t + 1 / SAMPLE_FPS, t + 0.5 / SAMPLE_FPS)
    finally:
        cap.release()


def _boxes_at(person_boxes, t: float, max_dt: float = 0.4):
    if not person_boxes:
        return None
    ts, boxes = min(person_boxes, key=lambda pb: abs(pb[0] - t))
    return boxes if abs(ts - t) <= max_dt else None


def analyze(info: ProxyInfo, person_boxes: list | None = None) -> dict:
    """person_boxes: optional [(t, [(x1, y1, x2, y2) fractions])] from cf.metrics.people to mask out."""
    nb = n_bins(info.duration_s)
    work_short = min(info.short_side, WORK_SHORT_SIDE)
    px = 1080.0 / work_short

    times, dts, dxs, dys, rots, logs, flows = [], [], [], [], [], [], []
    prev, prev_t, width = None, None, None
    failed = masked = 0
    for t, gray in _sample_frames(info):
        width = gray.shape[1]
        if prev is not None:
            mask = exclusion_mask(prev.shape, _boxes_at(person_boxes, prev_t))
            if mask is not None:
                masked += 1
            r = pair_transform(prev, gray, mask)
            dt = max(t - prev_t, 1e-3)
            tm = (t + prev_t) / 2
            if r is None:
                failed += 1
                r = {"dx": np.nan, "dy": np.nan, "rot": np.nan, "scale": np.nan, "flow_med": np.nan}
            times.append(tm)
            dts.append(dt)
            dxs.append(r["dx"] * px)
            dys.append(r["dy"] * px)
            rots.append(r["rot"])
            logs.append(math.log(r["scale"]) if r["scale"] == r["scale"] and r["scale"] > 0 else np.nan)
            flows.append(r["flow_med"] / width / dt if r["flow_med"] == r["flow_med"] else np.nan)
        prev, prev_t = gray, t

    if not times:
        empty = [None] * nb
        return {"shake_px": empty, "roll_deg": empty, "motion": [None] * nb, "pace": empty, "_pairs": 0, "_failed": failed}

    t = np.asarray(times)
    dt = np.asarray(dts)
    dx = np.nan_to_num(np.asarray(dxs))
    dy = np.nan_to_num(np.asarray(dys))
    rot = np.nan_to_num(np.asarray(rots))
    lg = np.nan_to_num(np.asarray(logs))
    flow = np.asarray(flows)

    # Camera path (cumulative), residual against its 1 s moving average.
    path_x, path_y, path_r = np.cumsum(dx), np.cumsum(dy), np.cumsum(rot)
    res_x = path_x - _local_trend(path_x, t)
    res_y = path_y - _local_trend(path_y, t)
    res_r = np.degrees(path_r - _local_trend(path_r, t))
    res2 = res_x**2 + res_y**2

    shake = bin_reduce(t, res2, nb, lambda v: math.sqrt(v.mean()))
    roll = bin_reduce(t, res_r**2, nb, lambda v: math.sqrt(v.mean()))
    vx = bin_reduce(t, dx / dt, nb)
    vy = bin_reduce(t, dy / dt, nb)
    div = bin_reduce(t, lg / dt, nb)
    pace = bin_reduce(t, flow, nb, np.median)

    shake, roll, vx, vy, div, pace = (fill_gaps(a) for a in (shake, roll, vx, vy, div, pace))
    motion = []
    for i in range(nb):
        if vx[i] is None:
            motion.append(None)
            continue
        motion.append(
            {
                "type": classify(vx[i], vy[i], div[i], shake[i]),
                "speed": round(pace[i], 4) if pace[i] is not None else None,
                "dx": round(vx[i], 1),
                "dy": round(vy[i], 1),
                "div": round(div[i], 4),
            }
        )
    return {
        "shake_px": rounded(shake, 2),
        "roll_deg": rounded(roll, 2),
        "motion": motion,
        "pace": rounded(pace, 4),
        "_pairs": len(times),
        "_failed": failed,
        "_masked": masked,
    }


if __name__ == "__main__":
    import json
    import sys
    from pathlib import Path

    from cf.metrics.common import probe_proxy

    print(json.dumps(analyze(probe_proxy(Path(sys.argv[1])))))
