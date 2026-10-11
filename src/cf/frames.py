"""Source frames on the timeline: which source frame Resolve shows on each timeline frame (pure).

Probe (2026-10-11, Resolve 21.1.1, ``smoke-2997``): a DJI clip at 30000/1001 fps on a 30 fps
timeline. Resolve reads its ``FPS`` as ``29.97`` but maps with the exact NTSC ratio: an item
appended at ``startFrame`` S has ``GetLeftOffset(True)`` = S x 1001/1000 timeline frames. A
fractional ``startFrame`` is rounded (3572.039 -> 3572), so an item always starts on a whole
source frame. ``GetSourceStartFrame()``/``GetSourceEndFrame()`` floor a float, so they read one
frame low for some in-points (3572 reads back 3571, 3611 reads 3611): use the left offset.

Timeline frame j of an item shows source frame ``S + floor(j x r + DISPLAY_EPS)``, r = clip fps /
timeline fps (stills matched against the decoded source, correlation 0.98): from S = 3572,
j = 34..38 showed 3605..3609; in the Mallorca reel-01 build (fresh exports, the playhead moved away
between them) S = 3605 and S = 3567 both repeated their third frame (j = 2 and 3 show S + 2) and the
run-up's last frame showed 3604, the hook's first 3605. With
r = 0.999 a source frame repeats near the start of every item (j = 3), and a run-up of n frames
from S continues seamlessly into S' only when ``S + floor(n x r + DISPLAY_EPS) == S'``. At
r = 1 that is S + n = S' (out_s = the next in_s); at 29.97 on 30 it is one source frame less
than the seconds suggest: a 39-frame run-up into 3611 must start at 3573, not 3572 (which
skips frame 3610 at the seam).
"""

from __future__ import annotations

import math
from fractions import Fraction

# Script times are written with 4 decimals, so a time within 1/100 of a frame of a frame
# boundary counts as on it (1/3 ms at 30 fps): 6.8667 s at 60 fps is frame 412, not 413.
FRAME_EPS = 0.01
# Resolve's phase when it picks the source frame for a timeline frame (see the module doc).
DISPLAY_EPS = 0.0025
NTSC = (24, 30, 48, 60, 120)


def exact_fps(fps: float) -> Fraction:
    """The exact rate behind a rounded one: 29.97 / 29.97003 -> 30000/1001; 30 -> 30; 23.976 -> 24000/1001."""
    f = float(fps)
    for base in NTSC:
        ntsc = Fraction(base * 1000, 1001)
        if abs(f - float(ntsc)) < 0.005:
            return ntsc
    return Fraction(f).limit_denominator(1001)


def first_frame(in_s: float, fps: float) -> int:
    """The first whole source frame at or after ``in_s`` (within FRAME_EPS)."""
    return math.ceil(in_s * float(exact_fps(fps)) - FRAME_EPS)


def snap_frames(seconds: float, fps: float) -> int:
    """Whole timeline frames that fit in ``seconds`` (floor, within FRAME_EPS)."""
    return max(0, math.floor(seconds * fps + FRAME_EPS))


def ratio(clip_fps: float, timeline_fps: float, speed: float = 1.0) -> Fraction:
    """Source frames per timeline frame."""
    return exact_fps(clip_fps) * Fraction(speed).limit_denominator(1000) / exact_fps(timeline_fps)


def shown(src_start: int, j: int, clip_fps: float, timeline_fps: float) -> int:
    """The source frame Resolve shows on timeline frame ``j`` of an item starting at ``src_start``."""
    return src_start + math.floor(j * ratio(clip_fps, timeline_fps) + DISPLAY_EPS)


def next_frame(src_start: int, frames: int, clip_fps: float, timeline_fps: float) -> int:
    """The source frame the item would show one timeline frame after its last one."""
    return shown(src_start, frames, clip_fps, timeline_fps)


def run_up_start(seam_frame: int, frames: int, clip_fps: float, timeline_fps: float) -> int:
    """In-point of a ``frames``-long run-up whose next frame is ``seam_frame`` (the loop seam)."""
    return seam_frame - math.floor(frames * ratio(clip_fps, timeline_fps) + DISPLAY_EPS)


def start_from_left_offset(left_offset: float, clip_fps: float, timeline_fps: float) -> int:
    """True source in-point from ``GetLeftOffset(True)`` (timeline frames)."""
    return round(left_offset * float(ratio(clip_fps, timeline_fps)))
