"""Reference kind (short or long) and ISO 8601 durations, shared by scout and fetch.

A Reference is ``short`` when its duration is at most ``SHORT_MAX_S`` seconds
(YouTube Shorts are up to 3 minutes), otherwise ``long``. The spec (issue #1,
"Kind") fixes the threshold; the feed's max-duration filter narrows further.
"""

from __future__ import annotations

import re

SHORT_MAX_S = 180
KINDS = ("short", "long")

_ISO = re.compile(r"^P(?:(?P<d>\d+)D)?(?:T(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?(?:(?P<s>\d+(?:\.\d+)?)S)?)?$")


def video_kind(duration_s: float | None) -> str | None:
    """``short`` / ``long`` for a duration in seconds; None when unknown (live, upcoming)."""
    if duration_s is None or duration_s <= 0:
        return None
    return "short" if duration_s <= SHORT_MAX_S else "long"


def parse_iso_duration(text: str | None) -> float | None:
    """Seconds for a Data API ``contentDetails.duration`` such as ``PT1M3S``; None for ``P0D`` or junk."""
    if not text:
        return None
    m = _ISO.match(text.strip())
    if not m or not any(m.groupdict().values()):
        return None
    d, h, mi = (int(m.group(k) or 0) for k in ("d", "h", "m"))
    s = float(m.group("s") or 0)
    total = d * 86400 + h * 3600 + mi * 60 + s
    return total or None
