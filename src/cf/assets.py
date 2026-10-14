"""Library Assets in a Script: where a Script's Video folder is, the refs its md files hold, the Library
context the validator and the build read, which file of an Asset is placed, and where on the canvas.

This module is the one seam between the Editor (``cf.script_schema``, ``cf.build``) and ``cf.library``: the
Editor picks files, positions and levels only through this module; it reads an Asset's public fields (id, ref,
category, rights, duration_s, pack) directly. Rules: ``docs/script-schema.md`` (Assets).

CLI::

    python -m cf.assets refs <video folder | script.json> [--footage-root PATH] [--db PATH] [--json]
    python -m cf.assets font <script.json> [--footage-root PATH] [--db PATH] [--style F] [--formats DIR]
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from cf import library as lib
from cf.library import refs as librefs
from cf.library.errors import LibraryError, RefError
from cf.research.store import default_db_path, footage_root

LANE_OF = {"sfx": "audio", "meme": "video", "img": "video", "emoji": "video", "face": "video",
           "footage": "video", "fx": "video"}
PLACEABLE = tuple(LANE_OF)
POS_PRESETS = ("center", "top", "bottom", "top-left", "top-right", "bottom-left", "bottom-right", "full", "fit")
FULL_MODES = {"full": "cover", "fit": "contain"}
CUE_DB_RANGE = (-24.0, 12.0)
CUE_TRACKS: dict[str, tuple[int, ...]] = {"audio": (3, 4), "video": (4, 5)}
TILT_SIGN = 1
IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg")
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULTS: dict[str, Any] = {
    "default_pos": {"meme": "center", "img": "center", "footage": "center", "emoji": "bottom-left",
                    "face": "bottom-left", "fx": "full"},
    "still_s": 1.5,
    "still_max_s": 5.0,
    "sfx_free_max_s": 2.0,
    "sfx_below_track_db": -6.0,
    "loop_clear_s": 0.5,
    "gain_range_db": [-40.0, 12.0],
}


def settings(style: dict | None) -> dict:
    """``style.json`` ``assets`` with the defaults filled in."""
    got = (style or {}).get("assets") or {}
    out = {**DEFAULTS, **{k: v for k, v in got.items() if not k.startswith("_")}}
    out["default_pos"] = {**DEFAULTS["default_pos"], **(got.get("default_pos") or {})}
    return out


# -- Video folders and md refs ------------------------------------------------------
@dataclass(frozen=True)
class VideoFolder:
    path: Path
    slug: str
    footage: Path
    legacy: bool
    format: str | None


def video_folder(path: Path) -> VideoFolder | None:
    """The Video a folder is: ``<F>/videos/<slug>/`` with a video.json, or a legacy ``<F>/<walk>/reels/<reel>/``."""
    path = Path(path)
    if path.parent.name == "videos" and (path / "video.json").is_file():
        try:
            fmt = json.loads((path / "video.json").read_text(encoding="utf-8")).get("format")
        except (OSError, ValueError, AttributeError):
            fmt = None
        return VideoFolder(path, path.name, path.parent.parent, False, fmt if isinstance(fmt, str) else None)
    if path.parent.name == "reels" and path.parent.parent != path.parent:
        walk = path.parent.parent
        return VideoFolder(path, f"{walk.name}~{path.name}", walk.parent, True, "walk-reel")
    return None


def video_of(script_path: Path) -> VideoFolder | None:
    return video_folder(Path(script_path).parent)


SCRIPT_FILE = re.compile(r"^script(?:[._-][^/]*)?\.(?i:md|json)$")


def is_script_file(name: str) -> bool:
    """A Script file of a Video folder (Desk's ``script`` file kind): ``script.md``/``.json`` or ``script``
    followed by ``.``, ``-`` or ``_`` (``script.v2.md``, ``script-long.json``); ``scripting-notes.md`` is not."""
    return bool(SCRIPT_FILE.match(name))


def md_refs(folder: Path) -> dict[str, list[str]]:
    """Refs in the folder's top-level, non-hidden ``*.md`` files: ``{ref as written: [file names]}``. Scripts
    (``is_script_file``, written by the Editor) are left out: only the Author's notes unlock an Asset."""
    out: dict[str, set[str]] = {}
    try:
        files = sorted(p for p in Path(folder).iterdir() if p.suffix == ".md" and not p.name.startswith(".")
                       and not is_script_file(p.name) and p.is_file())
    except OSError:
        return {}
    for p in files:
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for r in librefs.find(text):
            out.setdefault(r, set()).add(p.name)
    return {r: sorted(f) for r, f in out.items()}


# -- the Library context --------------------------------------------------------------
@dataclass(frozen=True)
class AssetContext:
    library: lib.Library | None
    library_problem: str | None
    video: VideoFolder | None
    md_refs: dict[str, list[str]]
    cli: bool = True  # messages may name CLI flags (False: the caller is Desk)


def load_library(footage: Path, db_path: Path) -> tuple[lib.Library | None, str | None]:
    try:
        store = lib.open_readonly(db_path)
    except LibraryError as exc:
        return None, str(exc)
    if store is None:
        return None, f"no factory.db at {db_path}"
    try:
        return lib.load(footage, store), None
    except Exception as exc:  # noqa: BLE001 - an unreadable store is a reason, not a crash
        return None, f"cannot read the Library from {db_path}: {exc}"
    finally:
        store.close()


def context(script_path: Path | None, *, footage: Path | None = None, db_path: Path | None = None,
            library: lib.Library | None = None, video: VideoFolder | None = None) -> AssetContext:
    """The Library and the Video's md refs for a Script. The store is opened read-only."""
    video = video or (video_of(script_path) if script_path is not None else None)
    refs_in = md_refs(video.path) if video else {}
    if library is not None:
        return AssetContext(library, None, video, refs_in)
    root = Path(footage) if footage else (video.footage if video else footage_root())
    found, problem = load_library(root, Path(db_path) if db_path is not None else default_db_path(root))
    return AssetContext(found, problem, video, refs_in)


# -- Assets as the Editor sees them -----------------------------------------------------
class BadRef(ValueError):
    """Not an Asset ref by its grammar."""


def lookup(library: lib.Library, ref: str) -> Any | None:
    try:
        return library.resolve(ref)
    except RefError as exc:
        raise BadRef(ref) from exc


def nearest_refs(library: lib.Library, ref: str, limit: int = 5) -> list[str]:
    return [a.ref for a in library.nearest(ref, limit)]


def lane_kind(asset: Any) -> str | None:
    return LANE_OF.get(asset.category)


def finite(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool) and math.isfinite(x)


def loudness(asset: Any) -> dict | None:
    lo = asset.loudness
    return lo if isinstance(lo, dict) and finite(lo.get("i")) else None


@dataclass(frozen=True)
class Placement:
    path: Path | None
    role: str
    width: int | None
    height: int | None
    fps: float | None
    still: bool
    note: str | None = None
    problem: str | None = None


NOT_PLACED_SUFFIXES = (".webm", ".gif")
STILL_NOTE = "placing the still png (no ProRes alpha variant)"


def _suffix(asset: Any) -> str:
    return Path(asset.primary["path"]).suffix.lower()


def _still(a: Any, note: str | None) -> Placement | None:
    still = a.variant("still")
    if still is not None:
        return Placement(a.root / still["path"], "still", still.get("width") or a.width,
                         still.get("height") or a.height, None, True, note)
    png = a.derived.get("png")
    if png:
        return Placement(a.cache / png, "png", a.width, a.height, None, True, note)
    return None


def placement(asset: Any) -> Placement:
    """Which file of an Asset goes on the timeline (first rule that applies). A ``.webm`` or ``.gif`` is never
    placed itself (Resolve does not take VP9 alpha; a gif goes through its converted file)."""
    a = asset
    w, h, fps = a.width, a.height, a.fps
    if a.kind == "audio":
        return Placement(a.path, "original", None, None, None, False)
    alpha = a.variant("alpha")
    if alpha is not None:
        return Placement(a.root / alpha["path"], "alpha", alpha.get("width") or w, alpha.get("height") or h,
                         alpha.get("fps") or fps, False)
    if a.green_screen:
        keyed = a.derived.get("alpha")
        if not keyed:
            return Placement(None, "keyed", w, h, fps, False,
                             problem="green screen not keyed yet: run python -m cf.library index "
                                     f"{a.pack} (without --no-key)")
        return Placement(a.cache / keyed, "keyed", w, h, fps, False)
    conv = a.derived.get("converted")
    if conv and a.kind == "video":
        return Placement(a.cache / conv, "converted", w, h, fps, False)
    webm = _suffix(a) == ".webm"
    if a.kind == "image":
        if _suffix(a) in IMAGE_SUFFIXES:
            return Placement(a.path, "original", w, h, None, True)
        got = _still(a, STILL_NOTE if webm else None)
        if got is not None:
            return got
        return Placement(None, "png", w, h, None, True,
                         problem="only a VP9 .webm with alpha, which Resolve does not take: no ProRes or png variant"
                         if webm else f"no png conversion yet: run python -m cf.library index {a.pack}")
    if webm:
        got = _still(a, STILL_NOTE)
        if got is not None:
            return got
        return Placement(None, "original", w, h, fps, False,
                         problem="only a VP9 .webm with alpha, which Resolve does not take: no ProRes or png variant")
    if _suffix(a) in NOT_PLACED_SUFFIXES:
        return Placement(None, "converted", w, h, fps, False,
                         problem=f"animated gif not converted yet: run python -m cf.library index {a.pack}")
    p = a.primary
    return Placement(a.path, "original", p.get("width") or w, p.get("height") or h, p.get("fps") or fps, False)


def has_sound(asset: Any, place: Placement | None = None) -> bool:
    if asset.kind == "audio":
        return True
    place = place or placement(asset)
    return bool(asset.has_audio) and not place.still and place.role in ("original", "alpha")


def default_dur_s(asset: Any, place: Placement, style: dict) -> float | None:
    if place.still:
        return float(settings(style)["still_s"])
    return float(asset.duration_s) if finite(asset.duration_s) else None


# -- positions -------------------------------------------------------------------------
@dataclass(frozen=True)
class Box:
    x: float
    y: float
    w: float
    h: float


def pos_table(style: dict, canvas: Any) -> dict:
    from cf.canvas import presets  # noqa: PLC0415

    preset = presets(style).get(canvas.preset or "") or {}
    return preset.get("asset_pos") or (style.get("assets") or {}).get("pos") or {}


def pos_box(style: dict, canvas: Any, pos: str) -> Box | str:
    """A preset's box in canvas px, or ``"cover"`` / ``"contain"`` for the full-frame modes."""
    if pos in FULL_MODES:
        return FULL_MODES[pos]
    table = pos_table(style, canvas)
    b = table.get(pos)
    if not isinstance(b, dict):
        raise ValueError(f"pos {pos!r}: style.json has no box for it on the {canvas.name} canvas")
    s = canvas.scale
    return Box(b["x"] * s, b["y"] * s, b["w"] * s, b["h"] * s)


def transform(w: float, h: float, box: Box | str, canvas_w: float, canvas_h: float,
              mismatch: str = "scaleToFit") -> dict:
    """Inspector ZoomX/ZoomY (ganged), Pan and Tilt that fit a ``w×h`` file inside ``box``."""
    from cf.reframe import base_scale  # noqa: PLC0415

    base = base_scale(w, h, canvas_w, canvas_h, mismatch)
    if box == "cover":
        s, cx, cy = max(canvas_w / w, canvas_h / h), canvas_w / 2, canvas_h / 2
    elif box == "contain":
        s, cx, cy = min(canvas_w / w, canvas_h / h), canvas_w / 2, canvas_h / 2
    else:
        s = min(box.w / w, box.h / h)
        cx, cy = box.x + box.w / 2, box.y + box.h / 2
    zoom = round(s / base, 4)
    return {"ZoomX": zoom, "ZoomY": zoom, "Pan": round(cx - canvas_w / 2, 1) + 0.0,
            "Tilt": round(TILT_SIGN * (canvas_h / 2 - cy), 1) + 0.0}


# -- overlay font ------------------------------------------------------------------------
FONT_LINE_RE = re.compile(r"^\W*Overlay font:\s*`?(@font/[^\s`]+)`?\s*$", re.MULTILINE)
FONT_SUFFIXES = (".ttf", ".otf")


class AssetFontError(ValueError):
    """The overlay font named by the Format or style.json cannot be used."""


@dataclass(frozen=True)
class FontChoice:
    ref: str
    path: Path
    source: str


def format_font(format_text: str | None) -> str | None:
    m = FONT_LINE_RE.search(format_text or "")
    return m.group(1) if m else None


def overlay_font(style: dict | None, format_text: str | None, library: lib.Library | None, *,
                 format_id: str | None = None, library_problem: str | None = None) -> FontChoice | None:
    """The font file every overlay role uses: the Format's ``Overlay font:`` line, else ``typography.font``."""
    ref = format_font(format_text)
    source = f"format {format_id}" if format_id else "format"
    if ref is None:
        ref = ((style or {}).get("typography") or {}).get("font")
        source = "style.json"
    if not ref:
        return None
    if library is None:
        raise AssetFontError(f"overlay font {ref} ({source}) needs the Library: {library_problem or 'not loaded'}")
    try:
        a = lookup(library, ref)
    except BadRef as exc:
        raise AssetFontError(f"overlay font {ref!r} ({source}) is not an Asset ref (expected @font/<name>)") from exc
    if a is None:
        near = nearest_refs(library, ref, 5)
        raise AssetFontError(f"overlay font ({source}): no such Asset {ref}; nearest: {', '.join(near) or 'none'}")
    if a.category != "font":
        raise AssetFontError(f"overlay font {ref} ({source}) is a {a.category} Asset, not a font")
    path = a.path
    if path.suffix.lower() not in FONT_SUFFIXES:
        raise AssetFontError(f"overlay font {ref} ({source}): {path.name} is not a .ttf or .otf file")
    if not path.is_file():
        raise AssetFontError(f"overlay font {ref} ({source}): file missing: {path}")
    return FontChoice(a.ref, path, source)


def font_for_script(script_path: Path, style: dict, formats_dir: Path, *, footage: Path | None = None,
                    db_path: Path | None = None) -> FontChoice | None:
    video = video_of(script_path)
    fmt = video.format if video else None
    text = None
    if fmt:
        f = Path(formats_dir) / fmt / "FORMAT.md"
        text = f.read_text(encoding="utf-8") if f.is_file() else None
    if format_font(text) is None and not ((style.get("typography") or {}).get("font")):
        return None
    ctx = context(script_path, footage=footage, db_path=db_path)
    return overlay_font(style, text, ctx.library, format_id=fmt, library_problem=ctx.library_problem)


# -- CLI -------------------------------------------------------------------------------
def resolved_refs(ctx: AssetContext) -> list[dict]:
    out = []
    for ref, files in sorted(ctx.md_refs.items()):
        row: dict[str, Any] = {"ref": ref, "files": files}
        a = None
        if ctx.library is not None:
            try:
                a = lookup(ctx.library, ref)
            except BadRef:
                a = None
        if a is None:
            row.update(ok=False, nearest=nearest_refs(ctx.library, ref) if ctx.library else [])
        else:
            row.update(ok=True, canonical=a.ref, category=a.category, duration_s=a.duration_s, rights=a.rights,
                       caption=a.caption or a.agent_caption)
        out.append(row)
    return out


def _folder_arg(text: str) -> Path:
    p = Path(text).expanduser().resolve()
    return p.parent if p.is_file() else p


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.assets", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    rp = sub.add_parser("refs", help="the Asset refs in a Video folder's md files, resolved against the Library")
    rp.add_argument("target", help="a Video folder or a script.json in one")
    rp.add_argument("--json", action="store_true")
    fp = sub.add_parser("font", help="the overlay font file for a Script's Video (Format line, else style.json)")
    fp.add_argument("script")
    fp.add_argument("--style", default=str(REPO_ROOT / "style.json"))
    fp.add_argument("--formats", default=str(REPO_ROOT / "formats"), help="the formats/ folder")
    for p in (rp, fp):
        p.add_argument("--footage-root", help="footage root (default: the Video's, else CF_FOOTAGE_ROOT)")
        p.add_argument("--db", help="factory.db (default: CF_FACTORY_DB, else <footage>/factory.db)")
    args = ap.parse_args(argv)
    footage = Path(args.footage_root).expanduser() if args.footage_root else None
    db = Path(args.db).expanduser() if args.db else None
    if args.cmd == "font":
        try:
            style = json.loads(Path(args.style).read_text(encoding="utf-8"))
            got = font_for_script(Path(args.script).expanduser().resolve(), style, Path(args.formats),
                                  footage=footage, db_path=db)
        except (AssetFontError, OSError, ValueError) as exc:
            print(str(exc), file=sys.stderr)
            return 1
        print(json.dumps({"ref": got.ref, "path": str(got.path), "source": got.source} if got else {"ref": None},
                         ensure_ascii=False))
        return 0
    folder = _folder_arg(args.target)
    video = video_folder(folder)
    if video is None:
        video = VideoFolder(folder, folder.name, folder.parent, False, None)
    ctx = context(None, footage=footage, db_path=db, video=video)
    rows = resolved_refs(ctx)
    if args.json:
        print(json.dumps({"library_problem": ctx.library_problem, "refs": rows}, ensure_ascii=False))
    else:
        if ctx.library_problem:
            print(f"no Library: {ctx.library_problem}")
        for r in rows:
            where = ", ".join(r["files"])
            if r["ok"]:
                print(f"ok   {r['ref']} -> {r['canonical']} ({r['rights']}) in {where}")
            else:
                print(f"BAD  {r['ref']} in {where}; nearest: {', '.join(r['nearest']) or 'none'}")
    return 1 if ctx.library_problem or any(not r["ok"] for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main())
