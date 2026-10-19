"""Meme cut: compose a vertical meme reel from a ``cf-memecut/1`` Script with ffmpeg.

    python -m cf.memecut validate <video folder | script.json> [--no-library] [--local-root P] [--shared-root P]
        [--db P]
    python -m cf.memecut build <video folder> [--dry-run] [--no-text-check] [--local-root P] [--shared-root P]
        [--db P]

A Meme cut (``formats/meme-cut/FORMAT.md``, profile ``formats/meme-cut/style.json``) is: a calm, pretty
clip of the Author with a setup line, then a hard cut to a punch line held over 3–6 Meme inserts of ~1 s;
it ends on the last insert, held longest. Each line marks one key word, ``{words}`` or ``{words|colour}``,
drawn in a ``colors.key_words`` colour by the overlay renderer. A ``finale`` (one more shot after the
inserts) is deprecated: old Scripts with one still build, with a warning. Why ffmpeg and not Resolve: a Meme insert sits over a blurred copy of itself,
and Resolve FX on a clip are outside the scripting API (``docs/resolve-rules.md``, Known gaps).

Pipeline of ``build`` (the folder is a Video folder ``videos/<slug>/`` or a legacy ``<footage>/reels/<reel>/``
holding ``script.json``):

1. ``validate``: the Script's shape and the Format's numbers (pure), then the match rule against the
   Library (every insert's Asset carries the Script's ``situation`` tag).
2. ``resolve_sources``: the setup clip from the manifest of its Footage under the local root
   (``setup.footage``, the legacy ``setup.walk`` still read: a walk, a studio or photo shoot; an HDR clip
   through its Apple SDR mezzanine, ``cf.mezz``), each insert (and a deprecated finale) from the Library under
   the shared root (``cf.assets.placement``), probed for display size and duration.
3. ``build_plan`` (pure): frames per part, a ``Placement`` per segment (``place``), source-length checks.
4. Overlays: the setup and punch lines as specs for ``overlays/render.mjs`` (the profile's
   ``typography.preset``, ``text.size``, the key-word mark with its colour filled in, the Format profile as
   ``style_path``) → ``overlays/setup.mov``, ``overlays/punch.mov``; a line is re-rendered only when its
   spec changed. A line outside the safe zone, or one the renderer had to set smaller to fit, is a problem;
   so is drawn text (its solid pixels, outline included) nearer than ``safe_zone.left/right`` (130 px
   reference) to a side: Instagram crops ~98 px off each side of a 9:16 Reel on a tall phone.
5. The text-clear check: the person detector on three frames of the setup, against the rendered
   setup line's box; closer than ``text.body_clear_px`` is a problem.
6. ``compose``: one ffmpeg run (``ffmpeg_args``) into ``out/<folder name>.mp4`` with a silent stereo AAC
   track; an existing render moves to ``out/prev-<time>/`` first. Then ``cf.render_check`` with the
   silent rule, ``out/render-check.json`` and a contact sheet ``out/sheet.jpg`` (one frame per segment).

``cf.publish <folder>`` then copies it into "Готовые ролики" as for any Reel.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from cf.canvas import Canvas, for_reel

REPO_ROOT = Path(__file__).resolve().parents[2]
FORMAT_ID = "meme-cut"
PROFILE_PATH = REPO_ROOT / "formats" / FORMAT_ID / "style.json"
SCHEMA = "cf-memecut/1"
FITS = ("auto", "blur-fill", "fill")
TRIM_KEYS = ("left", "right", "top", "bottom")
MIN_SIDE = 8  # px a trim must leave of the source
TOP_KEYS = {"schema", "title", "concept", "reference", "situation", "setup", "punch", "inserts", "finale", "ending",
            "caption", "hashtags", "location_tag", "note"}
FORBIDDEN = {"cta": "no CTA in a Meme cut caption", "alt_text": "no alt text in a Meme cut"}
SETUP_KEYS = {"footage", "walk", "clip", "in_s", "dur_s", "text", "anchor", "size", "style", "trim"}
PUNCH_KEYS = {"text", "anchor", "size", "style"}
INSERT_KEYS = {"ref", "in_s", "dur_s", "fit", "trim", "shows"}
FINALE_KEYS = {"ref", "in_s", "dur_s", "fit", "trim", "shows"}
CYRILLIC = re.compile(r"[Ѐ-ӿ]")
MARK = re.compile(r"\{([^{}|]*)(?:\|([^{}]*))?\}")  # a key word: {words} or {words|colour}; twin of overlays/src/layout.ts
EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF]")
HASHTAG = re.compile(r"#[^\s#]+")
SIDE_CROP_WHY = ("Instagram crops about 98 px (reference) off each side of a 9:16 Reel on a tall phone "
                 "(19.5:9), so text nearer the side is cut")
LENGTH_TOLERANCE_S = 0.02  # a source may end this much before the cut asks (container rounding)


# -- placement maths (pure) -------------------------------------------------------------
@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    w: int
    h: int


@dataclass(frozen=True)
class Placement:
    """How one source fills the canvas.

    ``crop``: the trimmed source region (source px). ``window``: a canvas-aspect window inside the crop,
    relative to it: the picture for ``fill``, the blurred background for ``blur-fill``. ``fg``: the whole
    trimmed picture on the canvas (canvas px), ``blur-fill`` only. ``upscale``: canvas px per source px of
    the sharp picture."""
    fit: str
    crop: Rect
    window: Rect
    fg: Rect | None
    upscale: float


def _int(v: Any) -> bool:
    return isinstance(v, int) and not isinstance(v, bool)


def trim_rect(src_w: int, src_h: int, trim: Any = None) -> Rect:
    """The source region left after cutting ``trim`` px off its edges; ValueError for a bad trim."""
    trim = {} if trim is None else trim
    if not isinstance(trim, dict):
        raise ValueError(f"trim must be an object of {', '.join(TRIM_KEYS)} in source px, got {trim!r}")
    unknown = set(trim) - set(TRIM_KEYS)
    if unknown:
        raise ValueError(f"trim: unknown edges {sorted(unknown)}; one of {', '.join(TRIM_KEYS)}")
    t = {k: trim.get(k, 0) for k in TRIM_KEYS}
    for k, v in t.items():
        if not _int(v) or v < 0:
            raise ValueError(f"trim.{k} must be a whole number of source px >= 0, got {v!r}")
    w, h = src_w - t["left"] - t["right"], src_h - t["top"] - t["bottom"]
    if w < MIN_SIDE or h < MIN_SIDE:
        raise ValueError(f"trim {trim} leaves {w}x{h} of a {src_w}x{src_h} source")
    return Rect(t["left"], t["top"], w, h)


def cover_window(w: int, h: int, canvas_w: int, canvas_h: int, zoom: float = 1.0) -> Rect:
    """The largest canvas-aspect window inside ``w x h``, shrunk by ``zoom``, centred; whole px."""
    aspect = canvas_w / canvas_h
    if w / h >= aspect:  # wider than the canvas: height-limited; the other side follows the rounded one
        wh = min(h, max(1, round(h / zoom)))
        ww = min(w, max(1, round(wh * aspect)))
    else:
        ww = min(w, max(1, round(w / zoom)))
        wh = min(h, max(1, round(ww / aspect)))
    return Rect((w - ww) // 2, (h - wh) // 2, ww, wh)


def contain_box(w: int, h: int, canvas_w: int, canvas_h: int) -> Rect:
    """``w x h`` scaled to full canvas width (full height when taller than the canvas), centred."""
    if w / h >= canvas_w / canvas_h:
        fw, fh = canvas_w, round(canvas_w * h / w)
    else:
        fw, fh = round(canvas_h * w / h), canvas_h
    return Rect((canvas_w - fw) // 2, (canvas_h - fh) // 2, fw, fh)


def choose_fit(w: int, h: int, canvas_w: int, canvas_h: int) -> str:
    """``fill`` for a source whose short side is at least the canvas short side, else ``blur-fill``."""
    return "fill" if min(w, h) >= min(canvas_w, canvas_h) else "blur-fill"


def place(src_w: int, src_h: int, canvas_w: int, canvas_h: int, fit: str = "auto", trim: Any = None,
          bg_zoom: float = 1.2) -> Placement:
    """Where a ``src_w x src_h`` source goes on the canvas. Never stretched: every scale keeps the aspect."""
    if fit not in FITS:
        raise ValueError(f"fit {fit!r}: one of {', '.join(FITS)}")
    crop = trim_rect(src_w, src_h, trim)
    if fit == "auto":
        fit = choose_fit(crop.w, crop.h, canvas_w, canvas_h)
    if fit == "fill":
        win = cover_window(crop.w, crop.h, canvas_w, canvas_h)
        return Placement("fill", crop, win, None, canvas_h / win.h)
    fg = contain_box(crop.w, crop.h, canvas_w, canvas_h)
    return Placement("blur-fill", crop, cover_window(crop.w, crop.h, canvas_w, canvas_h, bg_zoom), fg,
                     fg.w / crop.w)


# -- Script validation (pure) -------------------------------------------------------------
@dataclass
class Validation:
    problems: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    frames: dict = field(default_factory=dict)


def load_profile(path: Path = PROFILE_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _num(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def words(text: str) -> int:
    """Words that carry a letter (an emoji or a lone colon is not a word)."""
    return sum(1 for t in text.split() if any(c.isalpha() for c in t))


def frames_of(seconds: float, fps: float) -> int:
    return round(seconds * fps)


def _range(pacing: dict, key: str) -> tuple[float, float]:
    r = pacing[key]
    return float(r["min"]), float(r["max"])


def plain(text: str) -> str:
    """The text without its key-word marks (``{words}`` / ``{words|colour}`` → ``words``)."""
    return MARK.sub(lambda m: m.group(1), text)


def key_text(text: str, default_color: str) -> str:
    """The text with every bare key-word mark given ``default_color``: what the overlay spec carries."""
    def fill(m: re.Match) -> str:
        return m.group(0) if (m.group(2) or "").strip() else "{" + m.group(1) + "|" + default_color + "}"
    return MARK.sub(fill, text)


def text_size(part: dict, key: str, profile: dict) -> float:
    """The line's font size in reference px: the Script's ``size``, else the profile's."""
    size = part.get("size") if isinstance(part, dict) else None
    return float(size) if _num(size) else float(profile["text"]["size"][key])


def text_preset(part: dict, profile: dict) -> str:
    """The overlay preset of one text: its ``style`` variant (``"stroke"``) or the profile's preset."""
    ty = profile["typography"]
    style = part.get("style") if isinstance(part, dict) else None
    if style:
        return str(ty["variants"][style]["preset"])
    return str(ty["preset"])


def line_height(profile: dict) -> float:
    return float(profile["typography"].get("line_height") or 1.2)


def validate(script: Any, profile: dict) -> Validation:
    """The Script's shape and the Format's rules; durations are checked in frames at the canvas fps."""
    v = Validation()
    p, w = v.problems, v.warnings
    if not isinstance(script, dict):
        p.append("the Script is a JSON object")
        return v
    fps = float(profile["canvas"]["fps"])
    pacing, text_rules, cap = profile["pacing"], profile["text"], profile["caption"]
    palette = profile["colors"]["key_words"]
    if script.get("schema") != SCHEMA:
        p.append(f"schema must be {SCHEMA!r}, got {script.get('schema')!r}")
    for key, why in FORBIDDEN.items():
        if key in script:
            p.append(f"{key}: {why}")
    unknown = set(script) - TOP_KEYS - set(FORBIDDEN)
    if unknown:
        p.append(f"unknown keys {sorted(unknown)}")
    for key in ("title", "situation"):
        if not isinstance(script.get(key), str) or not script[key].strip():
            p.append(f"{key}: a non-empty string is required")
    sit = script.get("situation")
    if isinstance(sit, str) and (sit != sit.lower() or " " in sit.strip()):
        p.append(f"situation {sit!r}: one lowercase Library tag (e.g. 'свидание', 'монтаж')")
    if "reference" in script and (not isinstance(script["reference"], str) or not script["reference"].strip()):
        p.append("reference: the reel this cut adapts (account, link or name), a non-empty string")
    elif not script.get("reference") and not script.get("concept"):
        w.append("no reference: name the reel this cut adapts in 'reference' (or 'concept')")

    def seconds(where: str, part: dict, key: str, rng: tuple[float, float] | None) -> int | None:
        val = part.get(key)
        if not _num(val) or val < 0:
            p.append(f"{where}.{key}: a number of seconds >= 0 is required, got {val!r}")
            return None
        if rng is None:
            return None
        n, lo, hi = frames_of(val, fps), frames_of(rng[0], fps), frames_of(rng[1], fps)
        if not lo <= n <= hi:
            p.append(f"{where}.dur_s {val} s = {n} frames; the Format wants {rng[0]}–{rng[1]} s ({lo}–{hi} frames)")
        return n

    emoji = 0

    def check_text(where: str, key: str, part: dict, max_words: int) -> None:
        nonlocal emoji
        raw = part.get("text")
        if not isinstance(raw, str) or not raw.strip():
            p.append(f"{where}.text: a non-empty line is required")
            return
        t = plain(raw)
        if CYRILLIC.search(t):
            p.append(f"{where}.text {t!r}: the text is in English")
        if t != t.lower():
            p.append(f"{where}.text {t!r}: the text is lowercase")
        if "!" in t:
            p.append(f"{where}.text {t!r}: deadpan, no exclamation marks")
        if words(t) > max_words:
            p.append(f"{where}.text {t!r}: {words(t)} words, at most {max_words}")
        emoji += len(EMOJI.findall(t))
        if "{" in t or "}" in t:
            p.append(f"{where}.text {raw!r}: a brace outside a key-word mark {{words}} or {{words|colour}}")
        marks = MARK.findall(raw)
        want = int(text_rules["key_word"]["per_text"])
        for words_, colour in marks:
            if not words_.strip():
                p.append(f"{where}.text: an empty key-word mark")
            if colour.strip() and colour.strip() not in palette:
                p.append(f"{where}.text: key-word colour {colour.strip()!r}; one of {', '.join(palette)}")
        if not marks:
            w.append(f"{where}.text {t!r}: no key word; mark {want} as {{words}} (FORMAT.md, Text)")
        elif len(marks) > want:
            p.append(f"{where}.text {raw!r}: {len(marks)} key words, the Format wants {want} in the whole text")
        variants = profile["typography"].get("variants") or {}
        style = part.get("style")
        if style is not None and style not in variants:
            p.append(f"{where}.style {style!r}: one of {', '.join(variants) or 'none'} (or omit it for the default look)")
        sizes = text_rules["size"]
        size = part.get("size")
        if size is not None and (not _num(size) or size <= 0):
            p.append(f"{where}.size: a font size in reference px, got {size!r}")
            return
        px = text_size(part, key, profile)
        if not float(sizes["min"]) <= px <= float(sizes["max"]):
            p.append(f"{where}.size {px:g} px: the Format sets text at {sizes['min']}–{sizes['max']} px (reference); "
                     "a line too wide is broken with \\n, not set smaller")
        check_anchor(where, part.get("anchor"), px * line_height(profile), t.count("\n") + 1)
        band = text_rules.get(f"{key}_band")
        anchor = part.get("anchor")
        if band and isinstance(anchor, dict) and _num(anchor.get("y")) \
                and not str(anchor.get("anchor", "")).startswith(("bottom", "center", "middle")):
            ref_h = profile["canvas"]["height"] * float(profile["canvas"]["reference_width"]) / profile["canvas"]["width"]
            lo, hi = float(band["from"]) * ref_h, float(band["to"]) * ref_h
            if not lo - 0.5 <= float(anchor["y"]) <= hi + 0.5:
                w.append(f"{where}.anchor y {anchor['y']}: the {key} text starts at {lo:.0f}–{hi:.0f} px "
                         f"({band['from']:.0%}–{band['to']:.0%} of the height)")

    def check_anchor(where: str, anchor: Any, px: float, lines: int) -> None:
        """An explicit anchor keeps the estimated text box (``px``: one line's height) inside the safe zone
        (render.mjs measures it)."""
        if not isinstance(anchor, dict) or not _num(anchor.get("y")):
            return
        z = profile["safe_zone"]
        ref_h = profile["canvas"]["height"] * float(profile["canvas"]["reference_width"]) / profile["canvas"]["width"]
        top = float(anchor["y"]) - (lines * px if str(anchor.get("anchor", "")).startswith("bottom") else 0)
        if top < float(z["top"]):
            p.append(f"{where}.anchor y {anchor['y']}: the text starts above the safe zone (top {z['top']} px "
                     "reference); it would sit under the Instagram header")
        if top + lines * px > ref_h - float(z["bottom"]):
            p.append(f"{where}.anchor y {anchor['y']}: the text reaches the bottom {z['bottom']} px (reference) "
                     "under the caption and buttons")
        x, kind = anchor.get("x"), str(anchor.get("anchor", ""))
        ref_w = float(profile["canvas"]["reference_width"])
        if _num(x) and kind.endswith("left") and x < float(z["left"]):
            p.append(f"{where}.anchor x {x}: left of the safe zone ({z['left']} px reference); {SIDE_CROP_WHY}")
        if _num(x) and (kind.endswith("left") or kind.endswith("right")) and x > ref_w - float(z["right"]):
            p.append(f"{where}.anchor x {x}: right of the safe zone (x <= {ref_w - float(z['right']):g}, "
                     f"{z['right']} px reference from the right edge); {SIDE_CROP_WHY}")

    def check_fit_trim(where: str, part: dict) -> None:
        if "fit" in part and part["fit"] not in FITS:
            p.append(f"{where}.fit {part['fit']!r}: one of {', '.join(FITS)}")
        if "trim" in part:
            try:
                trim_rect(10**6, 10**6, part["trim"])
            except ValueError as exc:
                p.append(f"{where}.trim: {exc}")

    def part_of(key: str) -> dict | None:
        val = script.get(key)
        if not isinstance(val, dict):
            p.append(f"{key}: an object is required")
            return None
        return val

    def extra(where: str, part: dict, allowed: set) -> None:
        bad = set(part) - allowed
        if bad:
            p.append(f"{where}: unknown keys {sorted(bad)}")

    total = 0
    setup = part_of("setup")
    if setup is not None:
        extra("setup", setup, SETUP_KEYS)
        if "footage" in setup and "walk" in setup and setup["footage"] != setup["walk"]:
            p.append("setup: footage and walk differ; keep footage")
        for key in ("footage", "clip"):
            val = setup_footage(setup) if key == "footage" else setup.get(key)
            if not isinstance(val, str) or not val.strip():
                p.append(f"setup.{key}: required (the Footage id with a clip_manifest.json, e.g. a walk or a "
                         "shoot, and the clip file name in that manifest)")
        seconds("setup", setup, "in_s", None)
        n = seconds("setup", setup, "dur_s", _range(pacing, "setup_s"))
        v.frames["setup"] = n
        total += n or 0
        check_text("setup", "setup", setup, int(text_rules["setup_max_words"]))
        check_fit_trim("setup", setup)
    punch = part_of("punch")
    if punch is not None:
        extra("punch", punch, PUNCH_KEYS)
        check_text("punch", "punch", punch, int(text_rules["punch_max_words"]))
    if emoji > int(text_rules["emoji_max"]):
        p.append(f"{emoji} emoji on screen; at most {text_rules['emoji_max']}, and only when it fits the video or text")
    finale = script.get("finale")
    inserts = script.get("inserts")
    lo, hi = int(pacing["inserts"]["min"]), int(pacing["inserts"]["max"])
    if not isinstance(inserts, list) or not lo <= len(inserts) <= hi:
        p.append(f"inserts: {lo}–{hi} Meme inserts, got {len(inserts) if isinstance(inserts, list) else inserts!r}")
    v.frames["inserts"] = []
    ins_list = inserts if isinstance(inserts, list) else []
    for i, ins in enumerate(ins_list):
        where = f"inserts[{i}]"
        if not isinstance(ins, dict):
            p.append(f"{where}: an object is required")
            continue
        extra(where, ins, INSERT_KEYS)
        if not isinstance(ins.get("ref"), str) or not ins["ref"].startswith("@"):
            p.append(f"{where}.ref: a Library Asset ref (@meme/<name>) is required")
        if not isinstance(ins.get("shows"), str) or not ins["shows"].strip():
            p.append(f"{where}.shows: say what the meme literally shows (the match rule)")
        seconds(where, ins, "in_s", None)
        last = i == len(ins_list) - 1 and finale is None
        n = seconds(where, ins, "dur_s", _range(pacing, "last_insert_s" if last else "insert_s"))
        v.frames["inserts"].append(n)
        total += n or 0
        check_fit_trim(where, ins)
    if finale is not None:
        w.append("finale: deprecated; a Meme cut ends on its last Meme insert (no finale, no return to her "
                 "footage). This old Script still builds")
        if not isinstance(finale, dict):
            p.append("finale: an object is required")
        else:
            extra("finale", finale, FINALE_KEYS)
            if not isinstance(finale.get("ref"), str) or not finale["ref"].startswith("@"):
                p.append("finale.ref: a Library Asset ref is required")
            seconds("finale", finale, "in_s", None)
            n = seconds("finale", finale, "dur_s", _range(pacing, "finale_s"))
            v.frames["finale"] = n
            total += n or 0
            check_fit_trim("finale", finale)
    v.frames["total"] = total
    tlo, thi = _range(pacing, "target_length_s")
    if not p and not frames_of(tlo, fps) <= total <= frames_of(thi, fps):
        p.append(f"total {total} frames = {total / fps:.2f} s ({len(ins_list)} inserts); the Format wants "
                 f"{tlo:g}–{thi:g} s")
    ending = profile["ending"]
    if script.get("ending", ending["default"]) not in (ending["default"], *ending.get("aliases", [])):
        p.append(f"ending {script.get('ending')!r}: a Meme cut ends {ending['default']!r} (on its last Meme insert)")
    caption = script.get("caption")
    if not isinstance(caption, str) or not caption.strip():
        p.append("caption: one short line is required")
    else:
        if "\n" in caption.strip():
            p.append("caption: one line, no paragraphs")
        if words(caption) > int(cap["max_words"]):
            p.append(f"caption: {words(caption)} words, at most {cap['max_words']}")
        if CYRILLIC.search(caption):
            p.append("caption: in English")
        if "#" in caption:
            p.append("caption: hashtags go in 'hashtags'")
    tags = script.get("hashtags")
    if not isinstance(tags, list) or len(tags) > int(cap["hashtags_max"]) \
            or not all(isinstance(t, str) and HASHTAG.fullmatch(t) for t in tags):
        p.append(f"hashtags: a list of at most {cap['hashtags_max']} '#tag' strings")
    if not isinstance(script.get("location_tag"), str) or not script["location_tag"].strip():
        p.append("location_tag: the geotag is required")
    return v


def check_match(script: dict, lookup: Callable[[str], Any]) -> list[str]:
    """The match rule: every insert's Asset, the last one too, is tagged with the Script's ``situation``
    (Author or agent tags). A deprecated finale of an old Script only has to be in the Library."""
    out = []
    sit = str(script.get("situation") or "").strip().lower()
    parts = [(f"inserts[{i}]", ins) for i, ins in enumerate(script.get("inserts") or []) if isinstance(ins, dict)]
    if isinstance(script.get("finale"), dict):
        parts.append(("finale", script["finale"]))
    for where, part in parts:
        ref = part.get("ref")
        if not isinstance(ref, str):
            continue
        asset = lookup(ref)
        if asset is None:
            out.append(f"{where}: {ref} is not in the Library")
            continue
        if where == "finale":
            continue
        tags = [t.lower() for t in asset.all_tags()]
        if sit not in tags:
            out.append(f"{where}: {ref} is not tagged {sit!r} (its tags: {', '.join(tags) or 'none'}); every meme "
                       "shows the situation of the setup and punch text literally. Pick another meme, or tag "
                       "this one only if it really shows that situation")
    return out


# -- the plan (pure) ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Source:
    path: Path
    width: int     # display size (rotation applied)
    height: int
    duration_s: float


@dataclass(frozen=True)
class Segment:
    id: str            # setup, m1…m6, finale (deprecated)
    label: str         # where in the Script (setup, inserts[0], finale)
    source: Source
    in_s: float
    frames: int
    placement: Placement


@dataclass
class Plan:
    canvas: Canvas
    profile: dict
    segments: list[Segment]
    texts: dict          # {"setup": {text, anchor, size, frames}, "punch": {...}}; text with key-word colours
    problems: list[str]
    warnings: list[str]

    @property
    def total_frames(self) -> int:
        return sum(s.frames for s in self.segments)


def build_plan(script: dict, profile: dict, canvas: Canvas, sources: dict[str, Source]) -> Plan:
    """Segments with frames and placements. ``sources``: ``"setup"`` and each insert (or old finale) ref →
    Source."""
    val = validate(script, profile)
    problems, warnings = list(val.problems), list(val.warnings)
    fps = float(canvas.fps)
    blur = profile["inserts"]["blur_fill"]
    max_up = float(profile["inserts"]["fill_max_upscale"])
    parts = [("setup", "setup", script.get("setup"), "fill")]
    parts += [(f"m{i + 1}", f"inserts[{i}]", ins, profile["inserts"]["default_fit"])
              for i, ins in enumerate(script.get("inserts") or [])]
    if script.get("finale") is not None:  # deprecated: old Scripts only
        parts.append(("finale", "finale", script.get("finale"), profile["inserts"]["finale_fit"]))
    segments = []
    for sid, where, part, default_fit in parts:
        if not isinstance(part, dict) or not _num(part.get("dur_s")):
            continue
        key = "setup" if sid == "setup" else part.get("ref")
        src = sources.get(key) if isinstance(key, str) else None
        if src is None:
            problems.append(f"{where}: no source for {key}")
            continue
        n = frames_of(part["dur_s"], fps)
        in_s = float(part.get("in_s") or 0)
        if in_s + n / fps > src.duration_s + LENGTH_TOLERANCE_S:
            problems.append(f"{where}: {key} ({src.path.name}) is too short: {src.duration_s:.2f} s, the cut needs "
                            f"{in_s:.2f}–{in_s + n / fps:.2f} s; move in_s or pick another")
            continue
        try:
            pl = place(src.width, src.height, canvas.width, canvas.height, part.get("fit", default_fit),
                       part.get("trim"), float(blur["bg_zoom"]))
        except ValueError as exc:
            problems.append(f"{where}: {exc}")
            continue
        if pl.fit == "fill" and pl.upscale > max_up + 1e-6:
            warnings.append(f"{where}: fill upscales {src.path.name} x{pl.upscale:.2f} (over x{max_up:g}): soft; "
                            "use a larger shot or blur-fill")
        segments.append(Segment(sid, where, src, in_s, n, pl))
    tp = profile["text"]
    setup_n = next((s.frames for s in segments if s.id == "setup"), 0)
    rest_n = sum(s.frames for s in segments if s.id != "setup")
    texts = {}
    for key, frames in (("setup", setup_n), ("punch", rest_n)):
        part = script.get(key)
        if isinstance(part, dict) and isinstance(part.get("text"), str):
            texts[key] = {"text": key_text(part["text"], tp["key_word"]["default_color"][key]), "frames": frames,
                          "anchor": part.get("anchor") or default_anchor(key, profile, canvas, segments),
                          "size": text_size(part, key, profile), "preset": text_preset(part, profile)}
    return Plan(canvas, profile, segments, texts, problems, warnings)


def default_anchor(key: str, profile: dict, canvas: Canvas, segments: list[Segment]) -> dict:
    """The profile's anchor for ``key``. The punch with ``above_meme_px`` sits that far (reference px) above the
    top edge of the highest blur-fill insert, centred in the blurred band; ``y`` when every insert fills."""
    a = dict(profile["text"][f"{key}_anchor"])
    above = a.pop("above_meme_px", None)
    a.pop("note", None)
    tops = [s.placement.fg.y for s in segments if s.id != "setup" and s.placement.fg is not None]
    if above is not None and tops:
        a["y"] = round(min(tops) / canvas.scale - float(above), 1)
    return a


def _segment_filter(i: int, seg: Segment, canvas: Canvas, fps: float, blur: dict) -> str:
    W, H = canvas.width, canvas.height
    pl, c = seg.placement, seg.placement.crop
    fmt = "yuv444p10le" if seg.id == "setup" else "yuv444p"
    head = f"[{i}:v]setpts=PTS-STARTPTS,fps={fps:g},trim=end_frame={seg.frames},format={fmt},"
    if pl.fit == "fill":
        w = pl.window
        return (head + f"crop={w.w}:{w.h}:{c.x + w.x}:{c.y + w.y}:exact=1,scale={W}:{H}:flags=lanczos,"
                f"setsar=1,format=yuv420p[s{i}];")
    w, fg = pl.window, pl.fg
    ws = float(blur["work_scale"])
    bw, bh = max(2, round(W * ws)), max(2, round(H * ws))
    sigma = float(blur["blur_sigma"]) * bw / 540
    d = float(blur["darken"])
    return (head + f"crop={c.w}:{c.h}:{c.x}:{c.y}:exact=1,split[f{i}][b{i}];"
            f"[b{i}]crop={w.w}:{w.h}:{w.x}:{w.y}:exact=1,scale={bw}:{bh}:flags=bilinear,gblur=sigma={sigma:.2f},"
            f"colorchannelmixer=rr={d:g}:gg={d:g}:bb={d:g},scale={W}:{H}:flags=bicubic,format={fmt}[g{i}];"
            f"[f{i}]scale={fg.w}:{fg.h}:flags=lanczos[h{i}];"
            f"[g{i}][h{i}]overlay={fg.x}:{fg.y},setsar=1,format=yuv420p[s{i}];")


def ffmpeg_args(plan: Plan, out: Path, overlays: dict[str, Path] | None) -> list[str]:
    """The one ffmpeg command: segments placed, the setup line over the setup, the punch line over the rest,
    concatenated, a silent stereo AAC track. ``overlays``: ``{"setup": mov, "punch": mov}`` or None."""
    fps = float(plan.canvas.fps)
    blur = plan.profile["inserts"]["blur_fill"]
    render = plan.profile["render"]
    args: list[str] = ["ffmpeg", "-y", "-v", "error", "-stats"]
    for seg in plan.segments:
        args += ["-ss", f"{seg.in_s:.4f}", "-t", f"{seg.frames / fps + 0.5:.4f}", "-i", str(seg.source.path)]
    n = len(plan.segments)
    ov = overlays or {}
    ov_in = {}
    for key in ("setup", "punch"):
        if key in ov:
            ov_in[key] = n + len(ov_in)
            args += ["-i", str(ov[key])]
    audio_in = n + len(ov_in)
    args += ["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"]
    fc = "".join(_segment_filter(i, s, plan.canvas, fps, blur) for i, s in enumerate(plan.segments))
    rest = [f"[s{i}]" for i, s in enumerate(plan.segments) if s.id != "setup"]
    setup_i = next(i for i, s in enumerate(plan.segments) if s.id == "setup")
    if "setup" in ov_in:
        fc += f"[s{setup_i}][{ov_in['setup']}:v]overlay=format=yuv444,format=yuv420p,setsar=1[ss];"
    else:
        fc += f"[s{setup_i}]null[ss];"
    fc += "".join(rest) + f"concat=n={len(rest)}:v=1:a=0[mm];"
    if "punch" in ov_in:
        fc += f"[mm][{ov_in['punch']}:v]overlay=format=yuv444,format=yuv420p,setsar=1[mt];"
    else:
        fc += "[mm]null[mt];"
    # tag the frames themselves: untagged meme sources otherwise leave primaries/transfer unset in the file
    fc += ("[ss][mt]concat=n=2:v=1:a=0,format=yuv420p,"
           "setparams=range=tv:color_primaries=bt709:color_trc=bt709:colorspace=bt709[v]")
    total = plan.total_frames
    mbps = float(render["bitrate_mbps"])
    maxrate = float(render.get("maxrate_mbps", mbps))
    args += ["-filter_complex", fc, "-map", "[v]", "-map", f"{audio_in}:a", "-frames:v", str(total),
             "-t", f"{total / fps:.6f}", "-c:v", "libx264", "-profile:v", "high",
             "-preset", str(render.get("preset", "slow")), "-b:v", f"{mbps:g}M", "-maxrate", f"{maxrate:g}M",
             "-bufsize", f"{maxrate * 1.5:g}M", "-pix_fmt", "yuv420p", "-r", f"{fps:g}",
             "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
             "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-movflags", "+faststart", str(out)]
    return args


def compose(plan: Plan, out: Path, overlays: dict[str, Path] | None = None) -> Path:
    """Run ``ffmpeg_args``; raises RuntimeError with ffmpeg's tail on failure."""
    if plan.problems:
        raise ValueError("the plan has problems:\n- " + "\n- ".join(plan.problems))
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(ffmpeg_args(plan, out, overlays), capture_output=True, text=True)
    if res.returncode:
        raise RuntimeError(f"ffmpeg failed: {res.stderr[-2000:]}")
    return out


def rect_gap(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    """Distance between two boxes (x1, y1, x2, y2); 0 when they touch or overlap."""
    dx = max(b[0] - a[2], a[0] - b[2], 0.0)
    dy = max(b[1] - a[3], a[1] - b[3], 0.0)
    return (dx * dx + dy * dy) ** 0.5


def side_problems(key: str, box: tuple[float, float, float, float] | None, profile: dict,
                  canvas: Canvas) -> list[str]:
    """The drawn text (``box``: its solid pixels, canvas px) keeps ``safe_zone.left/right`` (reference px) to the
    frame's sides; the renderer's own check measures the layout box, this one the pixels (outline included)."""
    if box is None:
        return []
    z, k = profile["safe_zone"], canvas.scale
    left, right = box[0] / k, canvas.width / k - (box[2] + 1) / k
    out = []
    for side, gap in (("left", left), ("right", right)):
        if gap < float(z[side]) - 1e-6:
            out.append(f"{key} text is {gap:.0f} px from the {side} edge (reference), at least {z[side]}: "
                       f"{SIDE_CROP_WHY}; move {key}.anchor or break the line")
    return out


# -- the world: sources, overlays, the text check, build -------------------------------------
class MemecutError(RuntimeError):
    pass


def script_path(target: Path) -> Path:
    target = Path(target).expanduser().resolve()
    return target if target.is_file() else target / "script.json"


def probe(path: Path) -> Source:
    from cf.probe import probe_clip  # noqa: PLC0415

    c = probe_clip(Path(path), {})
    return Source(Path(path), int(c["display_width"]), int(c["display_height"]), float(c["duration_s"] or 0))


def setup_footage(setup: dict) -> Any:
    """The setup's Footage id: ``footage``, else the legacy ``walk``."""
    return setup.get("footage", setup.get("walk"))


def setup_source(root: Path, setup: dict) -> Path:
    """The setup clip's file from the manifest of its Footage ``<local root>/<setup.footage>/`` (a walk, a
    studio or photo shoot): the raw path, an HDR clip through its Apple SDR mezzanine."""
    from cf import mezz  # noqa: PLC0415

    footage_id = setup_footage(setup)
    footage = Path(root) / footage_id
    try:
        manifest = json.loads((footage / "clip_manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise MemecutError(f"setup: cannot read {footage}/clip_manifest.json ({exc}); run /ingest-footage on that "
                           "Footage") from exc
    clip = next((c for c in manifest.get("clips", []) if c.get("file") == setup["clip"]), None)
    if clip is None:
        raise MemecutError(f"setup: {setup['clip']} is not in the {footage_id} manifest")
    raw = Path(clip["path"])
    if not mezz.is_hdr(clip):
        return raw
    dst = mezz.mezz_path(footage, clip["file"])
    mezz.make_mezz(raw, dst)
    return dst


def library_lookup(shared: Path | None, db: Path | None):
    """``(lookup(ref) -> Asset | None, problem)`` over the Library under the shared root, read-only."""
    from cf import assets  # noqa: PLC0415
    from cf.research.store import default_db_path  # noqa: PLC0415

    lib_root = assets.library_root(shared)
    lib, problem = assets.load_library(lib_root, db or default_db_path(lib_root))
    if lib is None:
        return None, problem

    def lookup(ref: str):
        try:
            return assets.lookup(lib, ref)
        except assets.BadRef:
            return None
    return lookup, None


def resolve_sources(script: dict, root: Path, lookup) -> tuple[dict[str, Source], list[str]]:
    from cf import assets  # noqa: PLC0415

    sources: dict[str, Source] = {}
    problems: list[str] = []
    try:
        sources["setup"] = probe(setup_source(root, script["setup"]))
    except (MemecutError, OSError, ValueError, KeyError, TypeError) as exc:
        problems.append(str(exc))
    parts = [*(script.get("inserts") or []), script.get("finale") or {}]
    for part in parts:
        ref = part.get("ref") if isinstance(part, dict) else None
        if not isinstance(ref, str) or ref in sources:
            continue
        a = lookup(ref)
        if a is None:
            continue  # check_match reports it
        pl = assets.placement(a)
        if pl.path is None or pl.still:
            problems.append(f"{ref}: no video file to place ({pl.problem or 'a still'})")
            continue
        try:
            sources[ref] = probe(pl.path)
        except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as exc:
            problems.append(f"{ref}: cannot probe {pl.path}: {exc}")
    return sources, problems


def overlay_spec(entry: dict, fps: float, profile: dict) -> dict:
    """The ``render.mjs`` spec of one line: the key-word mark passes through (``{words|colour}``, a
    ``colors.key_words`` name the renderer reads from the same profile)."""
    return {"text": entry["text"], "type": "line", "duration_s": round(entry["frames"] / fps, 6),
            "style_path": str(PROFILE_PATH), "preset": entry.get("preset") or profile["typography"]["preset"],
            "size": entry["size"],
            "anchor": entry["anchor"], "in_frames": 0, "out_frames": 0}


def _summary(stdout: str) -> dict:
    """``render.mjs``'s last stdout line (a JSON summary), or {}."""
    for line in reversed(stdout.strip().splitlines()):
        try:
            return json.loads(line)
        except ValueError:
            continue
    return {}


def render_overlays(plan: Plan, folder: Path, log=print) -> dict[str, Path]:
    """``overlays/<key>.mov`` per text; re-rendered only when ``overlays/specs/<key>.json`` changed. A line
    the renderer measures outside the safe zone is a MemecutError (its spec is dropped, so it renders again)."""
    out: dict[str, Path] = {}
    specs = folder / "overlays" / "specs"
    specs.mkdir(parents=True, exist_ok=True)
    for key, entry in plan.texts.items():
        spec = overlay_spec(entry, float(plan.canvas.fps), plan.profile)
        text = json.dumps(spec, ensure_ascii=False, indent=1)
        spec_file, mov = specs / f"{key}.json", folder / "overlays" / f"{key}.mov"
        if mov.exists() and spec_file.exists() and spec_file.read_text(encoding="utf-8") == text:
            log(f"overlay {key}: unchanged")
        else:
            spec_file.write_text(text, encoding="utf-8")
            log(f"overlay {key}: rendering")
            res = subprocess.run(["node", str(REPO_ROOT / "overlays" / "render.mjs"), "--spec", str(spec_file),
                                  "--out", str(mov)], capture_output=True, text=True)
            if res.returncode:
                spec_file.unlink(missing_ok=True)
                raise MemecutError(f"overlay {key}: render.mjs failed: {res.stderr[-1500:]}")
            warns = _summary(res.stdout).get("warnings", [])
            bad = [w for w in warns if w.startswith("SAFE_ZONE_VIOLATION")]
            if bad:
                spec_file.unlink(missing_ok=True)
                raise MemecutError(f"overlay {key}: outside the Reels safe zone ({'; '.join(bad)}); move "
                                   f"{key}.anchor or shorten the line")
            shrunk = [w for w in warns if w.startswith("FONT_SHRUNK")]
            if shrunk:
                spec_file.unlink(missing_ok=True)
                raise MemecutError(f"overlay {key}: {shrunk[0]}; a line wider than the safe zone is broken into "
                                   f"more lines with \\n, not set smaller")
        out[key] = mov
    return out


def _alpha_box(mov: Path, canvas: Canvas) -> tuple[float, float, float, float] | None:
    """Box of the text's solid pixels (alpha > 50 %) in the overlay's first frame, canvas px."""
    import numpy as np  # noqa: PLC0415

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(mov), "-frames:v", "1", "-f", "rawvideo",
                          "-pix_fmt", "rgba", "-"], capture_output=True, check=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(canvas.height, canvas.width, 4)[:, :, 3]
    ys, xs = np.nonzero(a > 128)
    return (float(xs.min()), float(ys.min()), float(xs.max()), float(ys.max())) if len(xs) else None


def text_clearance(plan: Plan, setup_mov: Path) -> tuple[float | None, str | None]:
    """Smallest gap (reference px) between the setup line and a person in three setup frames."""
    import cv2  # noqa: PLC0415

    seg = next(s for s in plan.segments if s.id == "setup")
    box = _alpha_box(setup_mov, plan.canvas)
    if box is None:
        return None, "the setup overlay has no visible text"
    try:
        from cf.metrics.people import _load_model  # noqa: PLC0415
        model = _load_model()
    except Exception as exc:  # noqa: BLE001 - the check degrades to a warning
        return None, f"person detector unavailable: {exc}"
    fps, pl, cv = float(plan.canvas.fps), seg.placement, plan.canvas
    s = cv.height / pl.window.h
    ox, oy = pl.crop.x + pl.window.x, pl.crop.y + pl.window.y
    cap = cv2.VideoCapture(str(seg.source.path))
    gaps = []
    try:
        for k in (0.1, 0.5, 0.9):
            cap.set(cv2.CAP_PROP_POS_MSEC, (seg.in_s + k * seg.frames / fps) * 1000)
            ok, frame = cap.read()
            if not ok:
                continue
            fh, fw = frame.shape[:2]
            sx, sy = seg.source.width / fw, seg.source.height / fh
            res = model(frame, classes=[0], conf=0.25, verbose=False)[0]
            for x1, y1, x2, y2 in (res.boxes.xyxy.cpu().numpy() if res.boxes is not None else []):
                person = ((x1 * sx - ox) * s, (y1 * sy - oy) * s, (x2 * sx - ox) * s, (y2 * sy - oy) * s)
                gaps.append(float(rect_gap(box, tuple(float(v) for v in person))) / cv.scale)
    finally:
        cap.release()
    if not gaps:
        return None, "no person found in the setup frames"
    return min(gaps), None


def _move_old_render(out: Path) -> Path | None:
    if not out.exists():
        return None
    prev = out.parent / f"prev-{time.strftime('%Y%m%d-%H%M%S', time.localtime(out.stat().st_mtime))}"
    prev.mkdir(exist_ok=True)
    for f in out.parent.glob(out.stem + "*"):
        if f.is_file():
            shutil.move(str(f), prev / f.name)
    rc_json = out.parent / "render-check.json"
    if rc_json.exists():
        shutil.move(str(rc_json), prev / rc_json.name)
    return prev


def contact_sheet(plan: Plan, video: Path, dest: Path) -> Path:
    """One frame from the middle of each segment, side by side, 270 px wide each."""
    picks, start = [], 0
    for seg in plan.segments:
        picks.append(start + seg.frames // 2)
        start += seg.frames
    sel = "+".join(f"eq(n\\,{n})" for n in picks)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vf",
                    f"select='{sel}',scale=270:-2,tile={len(picks)}x1", "-frames:v", "1", "-fps_mode", "passthrough",
                    str(dest)], check=True)
    return dest


@dataclass
class Context:
    folder: Path
    script: dict
    profile: dict
    canvas: Canvas
    root: Path
    lookup: Any
    problems: list[str]
    warnings: list[str]


def load(target: Path, root: Path | None, db: Path | None, library: bool = True,
         shared: Path | None = None) -> Context:
    from cf.assets import video_folder  # noqa: PLC0415
    from cf.research.store import local_root  # noqa: PLC0415

    sp = script_path(target)
    script = json.loads(sp.read_text(encoding="utf-8"))
    profile = load_profile()
    vf = video_folder(sp.parent)
    local = Path(root) if root else (vf.root if vf else local_root())
    val = validate(script, profile)
    problems, warnings = list(val.problems), list(val.warnings)
    lookup = None
    if library:
        lookup, problem = library_lookup(shared, db)
        if lookup is None:
            problems.append(f"no Library: {problem}")
        else:
            problems += check_match(script, lookup)
    return Context(sp.parent, script, profile, for_reel(profile, None, None), local, lookup, problems, warnings)


def build(target: Path, root: Path | None = None, db: Path | None = None, dry_run: bool = False,
          text_check: bool = True, log=print, shared: Path | None = None) -> dict:
    from cf import render_check as rc  # noqa: PLC0415

    ctx = load(target, root, db, shared=shared)
    report: dict[str, Any] = {"folder": str(ctx.folder), "problems": ctx.problems, "warnings": ctx.warnings}
    if ctx.problems:
        return report
    sources, problems = resolve_sources(ctx.script, ctx.root, ctx.lookup)
    plan = build_plan(ctx.script, ctx.profile, ctx.canvas, sources)
    report["problems"] = problems + plan.problems
    report["warnings"] = ctx.warnings + plan.warnings
    report["segments"] = [{"id": s.id, "where": s.label, "file": str(s.source.path), "in_s": s.in_s,
                           "frames": s.frames, "fit": s.placement.fit, "crop": vars(s.placement.crop),
                           "upscale": round(s.placement.upscale, 2)} for s in plan.segments]
    report["frames"] = plan.total_frames
    if report["problems"] or dry_run:
        return report
    overlays = render_overlays(plan, ctx.folder, log)
    sides = [m for key, mov in overlays.items()
             for m in side_problems(key, _alpha_box(mov, plan.canvas), plan.profile, plan.canvas)]
    if sides:
        report["problems"] += sides
        return report
    if text_check:
        gap, why = text_clearance(plan, overlays["setup"])
        need = float(ctx.profile["text"]["body_clear_px"])
        report["text_gap_px"] = None if gap is None else round(gap, 1)
        if gap is None:
            report["warnings"].append(f"text-clear check not done: {why}; look at the sheet")
        elif gap < need:
            report["problems"].append(f"setup text is {gap:.0f} px from her body (reference px), at least {need:g}: "
                                      "set setup.anchor off the frames")
            return report
    out = ctx.folder / "out" / f"{ctx.folder.name}.mp4"
    prev = _move_old_render(out)
    if prev:
        report["previous"] = str(prev)
    log(f"composing {out}")
    compose(plan, out, overlays)
    expected = rc.expected_for(ctx.canvas)
    code = rc.run(out, expect_duration=plan.total_frames / float(ctx.canvas.fps),
                  report=out.parent / "render-check.json", expected=expected, silent=True)
    report["render"] = str(out)
    report["render_check"] = "PASS" if code == 0 else "FAIL"
    report["sheet"] = str(contact_sheet(plan, out, out.parent / "sheet.jpg"))
    if code:
        report["problems"].append("render_check failed (out/render-check.json)")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m cf.memecut", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    vp = sub.add_parser("validate", help="check a Meme cut Script (shape, Format numbers, the match rule)")
    vp.add_argument("target", help="a Video folder or its script.json")
    vp.add_argument("--no-library", action="store_true", help="skip the Library and the match rule")
    bp = sub.add_parser("build", help="overlays, compose, render_check, contact sheet")
    bp.add_argument("target")
    bp.add_argument("--dry-run", action="store_true", help="resolve and plan only; print the plan")
    bp.add_argument("--no-text-check", action="store_true", help="skip the person-vs-text check")
    for p in (vp, bp):
        p.add_argument("--local-root", help="local root holding the Footage (default: the Video folder's root, "
                       "else CF_LOCAL_ROOT)")
        p.add_argument("--shared-root", dest="shared_root",
                       help="shared root holding library/ (default: CF_SHARED_ROOT)")
        p.add_argument("--footage-root", dest="shared_root", help=argparse.SUPPRESS)
        p.add_argument("--db", help="factory.db (default: CF_FACTORY_DB, else <shared root>/factory.db)")
    a = ap.parse_args(argv)
    local = Path(a.local_root).expanduser() if a.local_root else None
    shared = Path(a.shared_root).expanduser() if a.shared_root else None
    db = Path(a.db).expanduser() if a.db else None
    try:
        if a.cmd == "validate":
            ctx = load(Path(a.target), local, db, library=not a.no_library, shared=shared)
            for w in ctx.warnings:
                print(f"- WARN {w}")
            for p in ctx.problems:
                print(f"- {p}")
            print("OK" if not ctx.problems else f"{len(ctx.problems)} problem(s)")
            return 1 if ctx.problems else 0
        rep = build(Path(a.target), local, db, a.dry_run, not a.no_text_check,
                    log=lambda m: print(m, file=sys.stderr), shared=shared)
    except (MemecutError, OSError, ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(rep, ensure_ascii=False, indent=1))
    return 1 if rep["problems"] else 0


if __name__ == "__main__":
    sys.exit(main())
