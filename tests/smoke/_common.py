"""Shared setup for the Resolve smoke tests S1-S10.

Every test runs only inside the project ``smoke-2026-10-10``, prints one of
PASS / FAIL / SKIP plus the raw values it read back, and writes them to
``tests/smoke/out/<test>.json``.
"""

from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from cf.resolve_driver import ResolveDriver, ResolveError, same_value  # noqa: E402,F401

PROJECT = "smoke-2026-10-10"
MEDIA_DIR = Path("/Users/anastasiiahlushchenko/Projects/Instagram/1")
HLG_CLIP = MEDIA_DIR / "IMG_0332.MOV"  # iPhone HLG / Dolby Vision 1080p60, rotated
SDR_CLIP = MEDIA_DIR / "IMG_1621.mov"  # iPhone SDR 4K30, rotated
OUT_DIR = Path(__file__).resolve().parent / "out"
RENDER_DIR = Path.home() / "Movies" / "content-factory" / "smoke"
FPS = 30


def driver() -> ResolveDriver:
    d = ResolveDriver(timeout=60)
    d.connect()
    d.get_or_create_project(PROJECT)
    return d


def media(d: ResolveDriver):
    """Return (hlg_item, sdr_item) MediaPoolItems, importing once."""
    return tuple(d.import_media([HLG_CLIP, SDR_CLIP]))


def try_call(fn, *args):
    """Call and capture result or exception text (for recording raw API behaviour)."""
    try:
        return {"ok": True, "value": fn(*args)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, (str, int, float, bool)) or x is None:
        return x
    return repr(x)


def run(name: str, body) -> None:
    """Run ``body(record)``; it returns 'PASS' / 'FAIL' / 'SKIP'. Prints and saves."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    record: dict = {}
    try:
        result = body(record)
    except Exception as exc:  # noqa: BLE001
        result = "FAIL"
        record["exception"] = f"{type(exc).__name__}: {exc}"
        record["traceback"] = traceback.format_exc()
    record = jsonable(record)
    (OUT_DIR / f"{name}.json").write_text(json.dumps({"result": result, **record}, indent=2, ensure_ascii=False))
    print(f"{name}: {result}")
    print(json.dumps(record, indent=2, ensure_ascii=False))
    sys.exit(0 if result in ("PASS", "SKIP") else 1)
