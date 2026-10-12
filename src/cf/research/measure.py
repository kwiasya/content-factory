"""The ``measured`` section of a Reference card (``cf-reference-card/1``), pure.

Inputs are plain dicts already on disk in the Reference folder: the yt-dlp
info dict (``info.json``), the stable-ts result (``transcript.json``, the
``to_dict()`` shape: ``segments[*].words[*]`` with ``word``, ``start``, ``end``),
the Shot log (``shotlog.json``, ``reel-shotlog/1.2``) and the OCR frames of the
first seconds (``tools/vision-score --text`` records, or None when OCR did not run).
"""

from __future__ import annotations

import re

from cf.research.kinds import video_kind
from cf.scoring import DEFAULT as SCORING

CUT_SCORE = SCORING.scd_spike  # ffmpeg scdet score (0-100) above which a second holds a hard cut
HOOK_WINDOW_S = 3.0            # the spoken hook: words begun within the first 3 s
PEAK_SHARE = 0.5               # a heatmap point belongs to a peak at >= half the curve's maximum
MAX_PEAKS = 5
QUOTE_MAX_WORDS = 60
SECTION_GAP_S = 1.5            # a pause longer than this ends a transcript section
SENTENCE_END = re.compile(r"[.?!…。？！][\"'”’)\]]*$")
# words whose final dot is not a sentence end (compared lowercased, without brackets and quotes)
ABBREVIATIONS = frozenset({"e.g.", "i.e.", "etc.", "vs.", "mr.", "mrs.", "ms.", "dr.", "st."})
OCR_MIN_CONF = 0.5             # Vision text line confidence that counts as on-screen text
OCR_MIN_CHARS = 3              # letters or digits in a line; drops stray glyphs read off textures


def cut_times(per_second: dict, threshold: float = CUT_SCORE) -> list[float]:
    """Seconds (bin starts) holding a hard cut: ``scd_score`` above ``threshold``.

    Consecutive seconds above it are one cut; second 0 is the first frame, never a cut.
    Resolution is 1 s (the Shot log keeps only the per-second maximum).
    """
    out: list[float] = []
    prev = False
    for t, score in zip(per_second.get("t") or [], per_second.get("scd_score") or []):
        hit = score is not None and score > threshold and t > 0
        if hit and not prev:
            out.append(float(t))
        prev = hit
    return out


def first_second(per_second: dict, key: str) -> float | None:
    """First second whose ``key`` count is above zero (None: never, or the metric is missing)."""
    for t, v in zip(per_second.get("t") or [], per_second.get(key) or []):
        if v is not None and v > 0:
            return float(t)
    return None


def words(transcript: dict | None) -> list[dict]:
    """Every word of a stable-ts result in time order: ``{"word", "start", "end"}`` (word keeps its leading space)."""
    out = []
    for seg in (transcript or {}).get("segments") or []:
        for w in seg.get("words") or []:
            if w.get("start") is None or not (w.get("word") or "").strip():
                continue
            out.append({"word": w["word"], "start": float(w["start"]), "end": float(w.get("end") or w["start"])})
    out.sort(key=lambda w: w["start"])
    return out


def join_words(ws: list[dict]) -> str:
    """Words back into text: Whisper words carry their own leading spaces."""
    return "".join(w["word"] for w in ws).strip()


def words_between(ws: list[dict], start: float, end: float) -> list[dict]:
    """Words that begin in ``[start, end)``."""
    return [w for w in ws if start <= w["start"] < end]


def sections(ws: list[dict], max_gap: float = SECTION_GAP_S) -> list[dict]:
    """Transcript sections ``{start_s, end_s, text}``: a section ends at a word ending a
    sentence (``. ? !``, not a common abbreviation such as ``e.g.`` or ``Dr.``) or before a
    pause longer than ``max_gap`` seconds."""
    out: list[dict] = []
    cur: list[dict] = []

    def close() -> None:
        if cur:
            out.append({"start_s": cur[0]["start"], "end_s": cur[-1]["end"], "text": join_words(cur)})
            cur.clear()

    for w in ws:
        if cur and w["start"] - cur[-1]["end"] > max_gap:
            close()
        cur.append(w)
        word = w["word"].strip()
        if SENTENCE_END.search(word) and word.strip("\"'“”‘’()[]").lower() not in ABBREVIATIONS:
            close()
    close()
    return out


def chapters(info: dict) -> list[dict]:
    """yt-dlp chapters as ``{start_s, end_s, title}``; [] when the video has none."""
    return [{"start_s": float(c["start_time"]),
             "end_s": None if c.get("end_time") is None else float(c["end_time"]),
             "title": c.get("title") or ""}
            for c in info.get("chapters") or [] if c.get("start_time") is not None]


def quote(ws: list[dict], start: float, end: float, max_words: int = QUOTE_MAX_WORDS) -> str:
    """Transcript words begun in ``[start, end)``, cut to ``max_words`` with an ellipsis."""
    inside = words_between(ws, start, end)
    text = join_words(inside[:max_words])
    return text + " …" if len(inside) > max_words else text


def heatmap_peaks(heatmap: list[dict] | None, ws: list[dict] | None = None,
                  share: float = PEAK_SHARE, limit: int = MAX_PEAKS) -> list[dict]:
    """Peaks of the "Most replayed" curve, strongest first.

    A peak is a run of consecutive heatmap points with value >= ``share`` of the
    curve's maximum; it spans the run and carries the run's highest value and the
    transcript words begun inside it (``quote``; None without a transcript).
    """
    pts = sorted((p for p in heatmap or [] if p.get("value") is not None), key=lambda p: p["start_time"])
    if not pts:
        return []
    top = max(p["value"] for p in pts)
    if top <= 0:
        return []
    runs: list[list[dict]] = []
    inside = False
    for p in pts:
        hit = p["value"] >= share * top
        if hit and inside:
            runs[-1].append(p)
        elif hit:
            runs.append([p])
        inside = hit
    peaks = []
    for run in runs:
        start, end = float(run[0]["start_time"]), float(run[-1]["end_time"])
        peaks.append({"start_s": start, "end_s": end, "value": max(p["value"] for p in run),
                      "quote": None if ws is None else quote(ws, start, end)})
    peaks.sort(key=lambda p: (-p["value"], p["start_s"]))
    return peaks[:limit]


def _readable(line: dict) -> bool:
    return (line.get("conf") or 0) >= OCR_MIN_CONF and len(re.findall(r"\w", line.get("s") or "")) >= OCR_MIN_CHARS


def first_text(frames: list[dict]) -> tuple[float, str] | None:
    """Time and text of the first OCR frame holding a confident readable line, or None.

    Frames are ``tools/vision-score --text`` records ``{"t", "text": [{"s", "conf", "h"}]}``.
    Street signs count as text too: the card keeps the text so the Editor can tell.
    """
    for f in sorted(frames, key=lambda f: f["t"]):
        lines = [ln["s"].strip() for ln in f.get("text") or [] if _readable(ln)]
        if lines:
            return float(f["t"]), " / ".join(lines)
    return None


def duration_s(info: dict, shotlog: dict | None = None) -> float | None:
    """yt-dlp ``duration``, else the Shot log clip duration."""
    d = info.get("duration")
    if d is None and shotlog:
        d = (shotlog.get("clip") or {}).get("duration_s")
    return float(d) if d else None


def measure(info: dict, transcript: dict | None, shotlog: dict | None,
            ocr_frames: list[dict] | None = None) -> dict:
    """The ``measured`` section of a ``cf-reference-card/1`` card."""
    dur = duration_s(info, shotlog)
    ps = (shotlog or {}).get("per_second") or {}
    cuts = cut_times(ps) if shotlog else None
    ws = words(transcript) if transcript is not None else None
    notes: dict[str, str] = {}
    text_at = None
    if cuts is None:
        notes["cut_count"] = notes["first_person_s"] = "no Shot log"
    if ws is None:
        notes["speech_onset_s"] = notes["spoken_hook"] = "no transcript"
    if ocr_frames is None:
        notes["first_text_s"] = "OCR did not run (tools/vision-score not built or failed)"
    else:
        text_at = first_text(ocr_frames)
        if text_at is None:
            looked = max((f["t"] for f in ocr_frames), default=0.0)
            notes["first_text_s"] = f"no on-screen text in the first {looked:.1f} s sampled"
    out: dict = {
        "duration_s": dur,
        "kind": video_kind(dur),
        "cut_count": None if cuts is None else len(cuts),
        "cuts_per_min": None if cuts is None or not dur else round(len(cuts) / (dur / 60.0), 2),
        "cut_times_s": cuts,
        "first_shot_s": None if cuts is None else (cuts[0] if cuts else dur),
        "first_person_s": first_second(ps, "persons"),
        "first_face_s": first_second(ps, "faces"),
        "speech_onset_s": ws[0]["start"] if ws else None,
        "spoken_hook": None if ws is None else join_words(words_between(ws, 0.0, HOOK_WINDOW_S)),
        "language": (transcript or {}).get("language") or info.get("language"),
        "first_text_s": text_at[0] if text_at else None,
        "first_text": text_at[1] if text_at else None,
        "sections": None if ws is None else sections(ws),
        "chapters": chapters(info),
        "heatmap_peaks": heatmap_peaks(info.get("heatmap"), ws),
        "notes": notes,
    }
    return out
