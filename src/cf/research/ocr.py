"""On-screen text of a Reference's first seconds: Apple Vision via ``tools/vision-score --text``.

Thin adapter, no unit tests: ``cf.research.measure.first_text`` reads the frames.
Returns None (and the card notes it) when the binary is not built or fails;
build it with ``cd tools/vision-score && swift build -c release``.
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from cf.metrics.vision import binary

SECONDS = 5.0  # how far into the video OCR looks for the first on-screen text
FPS = 4.0      # frames per second sampled in that window (0.25 s resolution)


def first_seconds(media: Path, seconds: float = SECONDS, fps: float = FPS) -> list[dict] | None:
    """``[{"t", "text": [{"s", "conf", "h"}]}]`` for frames at 0, 1/fps, … ≤ seconds; None if OCR is unavailable."""
    exe = binary()
    if not exe.exists():
        return None
    proc = subprocess.run([str(exe), str(media), "--text", "--fps", f"{fps:g}", "--until", f"{seconds:g}"],
                          capture_output=True, text=True, timeout=300)
    if proc.returncode != 0 or not proc.stdout.strip():
        return None
    try:
        frames = json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None
    return [{"t": f["t"], "text": f.get("text") or []} for f in frames]
