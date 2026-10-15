"""Deep fetch of one Reference by URL or video id, even outside every Watchlist.

Steps, each skipped when its artifact is already in the Reference folder
(``<shared root>/references/<watchlist or _adhoc>/<video_id>/``) unless ``force``;
``retranscribe`` redoes steps 2, 3 and the Shot log from the media already there.
A video has one Reference folder: a refetch reuses the folder it already has under
any ``references/*/``, whatever Watchlist is given now (nothing moves or doubles).

1. yt-dlp info (always refreshed: fresh view/like/comment counts) and media up
   to 720p (``<video_id>.mp4``, downloaded once), ``info.json`` next to it;
2. ``transcript.json``: stable-ts with word timestamps in the video's own language
   (``transcript_language``: yt-dlp's ``language`` of the video, always checked by
   Whisper's detection on two windows and overridden only when the windows with speech
   agree on another (``detection_verdict``); Whisper's detection alone when the info has
   none; the Watchlist language only as the last fallback, never forcing a translation);
3. subtitles and untranslated auto-captions in that language as WebVTT text
   (``<video_id>.subs.<lang>.vtt``, ``<video_id>.auto.<lang>.vtt``), kept offline;
   captions of any other language are removed;
   then the channel, ingested through ``channels.list`` when the store does not
   know it (no Watchlist membership), the ``video`` row and a ``snapshot``;
4. ``proxy.mp4`` and ``shotlog.json`` through ``cf.proxy.proxy_file`` and
   ``cf.shotlog.analyze_proxy`` (its speech pass reuses the transcript);
5. ``ocr.json``: on-screen text of the first seconds (Apple Vision);
6. the card: ``measured`` from ``cf.research.measure``, ``analysis`` kept; after a new
   transcript, ``steps["analysis"]`` says whether its spoken hook still quotes it.

Adapters (yt-dlp, stable-ts, proxy, Shot log, OCR, Data API transport) come
in through ``Adapters`` so tests replace them; the logic here is pure.

An Instagram reel (a reel or post link, or ``ig:<shortcode>``; ADR 0010) is
fetched from what the store already has from the Graph API (scout, snapshot,
``watchlist add-reference``): counts, caption, owner. yt-dlp then tries the
media without login or cookies; when Instagram refuses, the card is
caption-only (no transcript, Shot log or OCR) and its ``notes.media`` says why.
The Reference folder is named by the shortcode.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, unquote

from cf.research import card, ingest, measure, quota, youtube
from cf.research import watchlist as watchlists
from cf.research.kinds import video_kind
from cf.research.store import Store, dumps, ensure_shared_root, now_iso, shared_root

VIDEO_ID_RE = re.compile(r"[\w-]{11}")  # always fullmatch: ``$`` would let a trailing newline in
VIDEO_PATHS = {"shorts", "live", "embed", "v"}
# Bulky or volatile info keys left out of ``video.raw`` (info.json on disk keeps everything).
RAW_DROP = ("formats", "requested_formats", "requested_downloads", "thumbnails", "automatic_captions",
            "subtitles", "requested_subtitles", "http_headers", "_format_sort_fields", "_version")


DEFAULT_LANGUAGE = "en"
LANGUAGE_RE = re.compile(r"([A-Za-z]{2,3})(?:[-_][\w-]+)?")
LANGUAGE_ALIASES = {"iw": "he", "in": "id", "ji": "yi", "jv": "jw", "mo": "ro", "fil": "tl", "nb": "no"}
NO_LANGUAGE = {"und", "zxx", "mul", "mis"}
DETECT_MIN_PROBABILITY = 0.8
DETECT_MAX_NO_SPEECH = 0.6
ADHOC = "_adhoc"  # folder of References fetched without a Watchlist


class FetchError(Exception):
    """A fetch that cannot be carried out; the message says why."""


@dataclass
class Adapters:
    """The outside world of a fetch. ``default_adapters()`` wires the real ones.

    - ``extract(url) -> info``: yt-dlp metadata, no media;
    - ``download(url, ref_dir, video_id) -> info``: media to ``ref_dir/<video_id>.mp4``;
    - ``transcribe(media, language) -> dict``: stable-ts result as a plain dict;
    - ``proxy(media, dest, force) -> dict``: ``cf.proxy.proxy_file`` result (``status``, ``proxy_path``, ``error``);
    - ``shotlog(proxy, media, transcript) -> dict``: the Shot log, its speech taken from ``transcript``;
    - ``ocr(media) -> frames | None``: ``tools/vision-score --text`` records of the first seconds, None if unavailable;
    - ``transport``: Data API transport for ``channels.list`` (None: HTTP with ``YOUTUBE_API_KEY``);
    - ``captions(info, ref_dir, video_id, language) -> [file name]``: subtitles and auto-captions of
      ``language`` as ``.vtt`` files in ``ref_dir`` (None: not available);
    - ``languages() -> codes``: the language codes ``transcribe`` accepts, called only when a
      transcript is made (None: any well-formed code);
    - ``detect(media) -> {"windows": [{"language", "probability", "no_speech_prob", …}]} | None``:
      Whisper's language detection on 30 s windows of the audio (None: not available or no audio).
    """
    extract: Callable[[str], dict]
    download: Callable[[str, Path, str], dict]
    transcribe: Callable[[Path, str | None], dict]
    proxy: Callable[[Path, Path, bool], dict]
    shotlog: Callable[[Path, Path, dict], dict]
    ocr: Callable[[Path], list | None]
    transport: youtube.Transport | None = None
    captions: Callable[[dict, Path, str, str], list[str]] | None = None
    languages: Callable[[], frozenset[str]] | None = None
    detect: Callable[[Path], dict | None] | None = None


def default_adapters() -> Adapters:
    """yt-dlp, stable-ts, cf.proxy, cf.shotlog and Apple Vision OCR (imported on first use)."""
    from cf.research import ocr, stablets, ytdlp

    def proxy(media: Path, dest: Path, force: bool) -> dict:
        from cf.proxy import proxy_file
        return proxy_file(media, dest, force=force)

    return Adapters(extract=ytdlp.extract, download=ytdlp.download, transcribe=stablets.transcribe,
                    languages=stablets.languages, detect=stablets.detect,
                    proxy=proxy, shotlog=stablets.shotlog, ocr=ocr.first_seconds, captions=ytdlp.captions)


def parse_video_ref(text: str) -> str:
    """The 11-character video id in a bare id or a YouTube video URL (watch, youtu.be, shorts, live, embed)."""
    t = (text or "").strip()
    if VIDEO_ID_RE.fullmatch(t):
        return t
    if "/" not in t:
        raise FetchError(f"not a YouTube video id or URL: {text!r}")
    link = ingest.youtube_link(t)
    vid = None
    if link is not None and link.short_link and link.segments:
        vid = link.segments[0]
    elif link is not None:
        segs = link.segments
        if segs[:1] == ["watch"]:
            vid = (parse_qs(link.query).get("v") or [None])[0]
        elif len(segs) > 1 and segs[0] in VIDEO_PATHS:
            vid = segs[1]
    vid = unquote(vid).strip() if vid is not None else None  # a pasted %0A or space after the id
    if vid is None or not VIDEO_ID_RE.fullmatch(vid):
        raise FetchError(f"not a YouTube video URL: {text!r} (expected watch?v=…, youtu.be/…, /shorts/… or an id)")
    return vid


def _int(value) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def published_at(info: dict) -> str | None:
    """ISO UTC publish time: ``timestamp`` (or ``release_timestamp``), else midnight of ``upload_date``."""
    ts = info.get("timestamp") or info.get("release_timestamp")
    if ts:
        return now_iso(datetime.fromtimestamp(int(ts), timezone.utc))
    d = info.get("upload_date")
    if d and re.fullmatch(r"\d{8}", d):
        return f"{d[:4]}-{d[4:6]}-{d[6:]}T00:00:00Z"
    return None


def video_row_from_info(info: dict) -> dict:
    """Column values of ``video`` from a yt-dlp info dict (channel, own and availability flags not included)."""
    dur = info.get("duration")
    dur = float(dur) if dur else None
    return {
        "platform": "youtube",
        "external_id": info["id"],
        "title": info.get("title"),
        "description": info.get("description"),
        "published_at": published_at(info),
        "duration_s": dur,
        "kind": video_kind(dur),
        "tags": dumps(info.get("tags") or []),
        "url": ingest.video_url(info["id"]),
        "raw": dumps({k: v for k, v in info.items() if k not in RAW_DROP}),
    }


def snapshot_from_info(info: dict) -> dict:
    """View, like and comment counts of the info dict (None when hidden or not reported)."""
    return {"views": _int(info.get("view_count")), "likes": _int(info.get("like_count")),
            "comments": _int(info.get("comment_count"))}


def channel_row_from_info(info: dict) -> dict:
    """A minimal ``channel`` row from the info dict, for when ``channels.list`` cannot be called.

    ``raw`` stays NULL, which marks the row for a ``channels.list`` retry on the next fetch.
    """
    handle = info.get("uploader_id") if str(info.get("uploader_id") or "").startswith("@") else None
    return {"platform": "youtube", "external_id": info["channel_id"], "handle": ingest.normalize_handle(handle),
            "title": info.get("channel") or info.get("uploader"),
            "subscriber_count": _int(info.get("channel_follower_count"))}


def _channel(store: Store, info: dict, transport: youtube.Transport | None, ts: str) -> tuple[int | None, str]:
    """Store id of the video's channel and where its row came from."""
    ext = info.get("channel_id")
    if not ext:
        return None, "unknown (no channel_id in the info)"
    row = store.one("SELECT id, raw FROM channel WHERE platform = 'youtube' AND external_id = ?", (ext,))
    if row is not None and row["raw"] is not None:
        return int(row["id"]), "store"
    try:
        ids = ingest.ingest_channels(store, youtube.channels_list(store, ids=[ext], transport=transport),
                                     fetched_at=ts)
        if ids:
            return ids[0], "channels.list"
        why = "channels.list found no such channel"
    except (youtube.YouTubeError, quota.QuotaExceeded) as exc:
        why = str(exc)
    if row is not None:
        return int(row["id"]), f"store, info only ({why})"
    ch = channel_row_from_info(info) | {"fetched_at": ts}
    with store.transaction() as c:
        cid = c.execute(f"INSERT INTO channel ({', '.join(ch)}) VALUES ({', '.join('?' for _ in ch)})",
                        tuple(ch.values())).lastrowid
    return int(cid), f"yt-dlp info ({why})"


def record_info(store: Store, info: dict, *, transport: youtube.Transport | None = None, media: bool = False,
                transcript: bool = False, taken_at: str | None = None) -> dict:
    """Upsert the video of an info dict, its channel (no Watchlist membership) and a snapshot.

    A channel the store knows from ``channels.list`` costs nothing; an unknown one
    is fetched (1 quota unit); without the Data API (no key, quota spent) a minimal
    row is made from the info dict and retried next time. As in ``ingest``, a video
    of an own channel is own and an own video stays own.
    Returns ``{"video_id", "channel_id", "channel_source"}`` (store ids).
    """
    ts = taken_at or now_iso()
    channel_id, source = _channel(store, info, transport, ts)
    row = video_row_from_info(info) | {"has_media": int(media), "has_transcript": int(transcript), "fetched_at": ts}
    with store.transaction() as c:
        own = 0
        if channel_id is not None:
            own = int(c.execute("SELECT own FROM channel WHERE id = ?", (channel_id,)).fetchone()[0])
        vid = ingest.upsert_video(c, row, channel_id, own)
        snap = snapshot_from_info(info)
        c.execute("INSERT INTO snapshot (video_id, taken_at, views, likes, comments) VALUES (?, ?, ?, ?, ?) "
                  "ON CONFLICT (video_id, taken_at) DO UPDATE SET views = excluded.views, "
                  "likes = excluded.likes, comments = excluded.comments",
                  (vid, ts, snap["views"], snap["likes"], snap["comments"]))
    return {"video_id": vid, "channel_id": channel_id, "channel_source": source}


def info_language(info: dict, supported: frozenset[str] | None = None) -> str | None:
    """The Whisper code of yt-dlp's ``language``: base code (``en-US`` gives ``en``), legacy
    aliases mapped (``iw`` gives ``he``); None when absent, malformed, undetermined (``und``,
    ``zxx``, ``mul``) or not in ``supported``."""
    m = LANGUAGE_RE.fullmatch(str(info.get("language") or "").strip())
    if not m:
        return None
    lang = m.group(1).lower()
    lang = LANGUAGE_ALIASES.get(lang, lang)
    if lang in NO_LANGUAGE or (supported is not None and lang not in supported):
        return None
    return lang


def transcript_language(info: dict, supported: frozenset[str] | None = None) -> tuple[str | None, str]:
    """The language to transcribe in and where it came from: the video's own (``info``) or None
    with ``whisper``, which leaves the language to Whisper's detection."""
    lang = info_language(info, supported)
    return (lang, "info") if lang else (None, "whisper")


def detection_verdict(det: dict | None, info_lang: str,
                      supported: frozenset[str] | None = None) -> tuple[str | None, str]:
    """The language Whisper's detection puts in place of ``info_lang`` (None: keep the info) and why.

    Only windows with speech (``no_speech_prob`` below 0.6) count; they must all name the same
    other language, each with probability 0.8 or more.
    """
    if not det:
        return None, "no detection (no audio)"
    heard = [w for w in det.get("windows") or []
             if w.get("no_speech_prob") is not None and float(w["no_speech_prob"]) < DETECT_MAX_NO_SPEECH]
    if not heard:
        return None, "ignored: no speech in the detection windows"
    langs = sorted({info_language({"language": w.get("language")}, supported) or str(w.get("language")) for w in heard})
    if len(langs) > 1:
        return None, f"ignored: the windows disagree ({', '.join(langs)})"
    lang = info_language({"language": langs[0]}, supported)
    if lang == info_lang:
        return None, "agrees with the info"
    if lang is None:
        return None, f"ignored: {langs[0]} is not a supported language"
    low = min(float(w.get("probability") or 0) for w in heard)
    if low < DETECT_MIN_PROBABILITY:
        return None, f"ignored: not sure enough ({lang} at {low:.2f})"
    return lang, f"overrides the info ({info_lang} -> {lang})"


def _caption_language(name: str, video_id: str) -> str | None:
    parts = name[len(video_id) + 1:].split(".")
    return info_language({"language": parts[1]}) if len(parts) == 3 else None


def reference_dir(video_id: str, watchlist: str | None = None, root: Path | None = None) -> Path:
    """``<shared root>/references/<watchlist or _adhoc>/<video_id>/``."""
    return Path(root or shared_root()) / "references" / (watchlist or ADHOC) / video_id


def folder_for(video_id: str, watchlist: str | None = None, root: Path | None = None) -> Path:
    """The Reference folder a fetch uses: the video's existing folder under any ``references/*/``
    (the one of ``watchlist`` when there are several), else a new one for ``watchlist``. Without ``root`` the
    shared root must be mounted (``StoreError`` with the mount hint otherwise)."""
    root = Path(root) if root is not None else ensure_shared_root()
    wanted = reference_dir(video_id, watchlist, root)
    existing = card.reference_dirs(video_id, root)
    if wanted in existing or not existing:
        return wanted
    return existing[0]


def _read(path: Path):
    return json.loads(path.read_text())


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(path)


def fetch(store: Store, ref: str, *, watchlist: str | None = None, force: bool = False,
          retranscribe: bool = False, adapters: Adapters | None = None, root: Path | None = None) -> dict:
    """Deep fetch of one Reference (see the module docstring); returns what was done and the card.

    ``retranscribe`` makes the transcript, the captions and the Shot log again from the media
    already in the folder (no download); the analysis is kept as always.
    Result: ``video_id`` (YouTube id), ``video`` (store id), ``dir``, ``channel_source``,
    ``language`` and ``language_source`` (``info``, ``whisper``, ``watchlist`` or ``default``),
    ``steps`` (per artifact: made, kept, downloaded, FAILED: …), ``captions`` (``.vtt`` file
    names in ``dir``), ``card``. An Instagram link goes to ``fetch_instagram``.
    """
    code = instagram_ref(ref)
    if code is not None:
        return fetch_instagram(store, code, watchlist=watchlist, force=force, adapters=adapters, root=root)
    vid = parse_video_ref(ref)
    a = adapters or default_adapters()
    hint = DEFAULT_LANGUAGE
    if watchlist is not None:
        hint = info_language({"language": watchlists.get(store, watchlist).language}) or DEFAULT_LANGUAGE
    d = folder_for(vid, watchlist, root)
    d.mkdir(parents=True, exist_ok=True)
    media = d / f"{vid}.mp4"
    url = ingest.video_url(vid)
    steps: dict[str, str] = {}

    if force or not media.exists():
        info = a.download(url, d, vid)
        steps["media"] = "downloaded"
    else:
        info = a.extract(url)
        steps["media"] = "kept"
    if not media.exists():
        raise FetchError(f"yt-dlp finished but {media} is missing")
    _write(d / "info.json", info)

    redo = force or retranscribe
    fallback = "watchlist" if watchlist is not None else "default"
    tr_path = d / "transcript.json"
    made = redo or not tr_path.exists()
    if made:
        supported = a.languages() if a.languages is not None else None
        if supported is not None and hint not in supported:
            hint = DEFAULT_LANGUAGE
        language, source = transcript_language(info, supported)
        extra: dict = {"_info_language": info_language(info)}
        if language is not None and a.detect is not None:
            try:
                det = a.detect(media)
            except Exception as exc:
                extra["_language_detection"] = {"error": str(exc) or type(exc).__name__}
            else:
                heard, why = detection_verdict(det, language, supported)
                extra["_language_detection"] = (det or {}) | {"verdict": why}
                if heard:
                    language, source = heard, "whisper"
        transcript = a.transcribe(media, language)
        detected = info_language({"language": transcript.get("language")})
        if language is None and detected:
            language = detected
        elif language is None:
            language, source = hint, fallback
        transcript |= extra | {"_language": language, "_language_source": source}
        _write(tr_path, transcript)
        note = f"{language} from {source}"
        det = extra.get("_language_detection")
        if det is not None:
            note += f"; detection failed: {det['error']}" if "error" in det else f"; detection {det['verdict']}"
        steps["transcript"] = f"made ({note})"
    else:
        transcript = _read(tr_path)
        steps["transcript"] = "kept"
        language = info_language({"language": transcript.get("language") or transcript.get("_language")})
        if language is None:
            language, source = hint, fallback
        else:
            source = transcript.get("_language_source") or "transcript"
        own = info_language(info)
        if own and own != language and transcript.get("_language_source") != "whisper":
            steps["transcript"] = f"kept (in {language}, the video is in {own}: fetch --retranscribe)"

    for p in d.glob(f"{vid}.*.vtt"):
        if _caption_language(p.name, vid) != language:
            p.unlink()
    have = sorted(p.name for p in d.glob(f"{vid}.*.vtt"))
    if a.captions is None:
        steps["captions"] = "unavailable"
    elif redo or not have:
        try:
            got = a.captions(info, d, vid, language)
            steps["captions"] = "made" if got else "none on YouTube"
        except FetchError as exc:
            steps["captions"] = f"FAILED: {exc}"
    else:
        steps["captions"] = "kept"
    captions = sorted(p.name for p in d.glob(f"{vid}.*.vtt"))

    rec = record_info(store, info, transport=a.transport, media=True, transcript=True)
    shotlog, frames = _shotlog_ocr(a, d, media, transcript, force, redo, steps)

    measured = measure.measure(info, transcript, shotlog, frames) | {"language": language, "language_source": source}
    saved = card.save(store, rec["video_id"], measured, path=d / "card.json")
    if saved.get("analysis") is None:
        steps["analysis"] = "none yet"
    elif made:
        problem = card.spoken_hook_problem(saved, transcript)
        steps["analysis"] = (f"kept; stale: hook.spoken_hook {problem} — re-run analyze-reference"
                             if problem else "kept; hook.spoken_hook found in the new transcript")
    else:
        steps["analysis"] = "kept"
    return {"video_id": vid, "video": rec["video_id"], "title": info.get("title"), "dir": str(d),
            "watchlist": watchlist, "language": language, "language_source": source,
            "channel_source": rec["channel_source"],
            "steps": steps, "captions": captions, "card": saved}


def _transcript(a: Adapters, d: Path, media: Path, language: str, force: bool, steps: dict) -> dict:
    tr_path = d / "transcript.json"
    if force or not tr_path.exists():
        transcript = a.transcribe(media, language)
        _write(tr_path, transcript)
        steps["transcript"] = "made"
    else:
        transcript = _read(tr_path)
        steps["transcript"] = "kept"
    return transcript


def _relative_clip_path(shotlog: dict, d: Path) -> None:
    """A Reference's Shot log names its media relative to the Reference folder: the folder lives on the
    share and its absolute path differs per Mac (ADR 0013)."""
    clip = shotlog.get("clip") if isinstance(shotlog, dict) else None
    if not isinstance(clip, dict) or not isinstance(clip.get("path"), str):
        return
    try:
        clip["path"] = Path(clip["path"]).resolve().relative_to(d.resolve()).as_posix()
    except ValueError:
        clip["path"] = Path(clip["path"]).name


def _shotlog_ocr(a: Adapters, d: Path, media: Path, transcript: dict, force: bool, redo: bool,
                 steps: dict) -> tuple[dict | None, list | None]:
    """Proxy, Shot log and OCR of the media in ``d``, each kept unless ``force`` (the Shot log also on ``redo``)."""
    shotlog = None
    sl_path = d / "shotlog.json"
    px = a.proxy(media, d / "proxy.mp4", force)
    if px.get("status") == "FAILED" or not px.get("proxy_path"):
        steps["proxy"] = f"FAILED: {px.get('error') or 'no proxy'}"
        steps["shotlog"] = "skipped (no proxy)"
    else:
        steps["proxy"] = px["status"]
        if redo or px["status"] == "made" or not sl_path.exists():
            shotlog = a.shotlog(Path(px["proxy_path"]), media, transcript)
            _relative_clip_path(shotlog, d)
            _write(sl_path, shotlog)
            steps["shotlog"] = "made"
        else:
            shotlog = _read(sl_path)
            steps["shotlog"] = "kept"

    ocr_path = d / "ocr.json"
    if force or not ocr_path.exists():
        frames = a.ocr(media)
        if frames is not None:
            _write(ocr_path, frames)
        steps["ocr"] = "made" if frames is not None else "unavailable"
    else:
        frames = _read(ocr_path)
        steps["ocr"] = "kept"
    return shotlog, frames


# --- Instagram ------------------------------------------------------------------

CAPTION_ONLY = ("caption-only: yt-dlp could not get the video without login ({why}); no transcript, Shot log "
                "or OCR. Cookies and login are never used (ADR 0010)")


def instagram_ref(text: str) -> str | None:
    """The shortcode of an Instagram reel or post link or of ``ig:<shortcode>``; None for anything else."""
    t = (text or "").strip()
    if t.lower().startswith("ig:") and ingest.SHORTCODE_RE.fullmatch(t[3:].strip()):
        return t[3:].strip()
    if ingest.instagram_segments(t) is None:
        return None
    code = ingest.instagram_shortcode(t)
    if code is None:
        raise FetchError(f"not an Instagram reel or post link: {text!r}")
    return code


def fetch_instagram(store: Store, code: str, *, watchlist: str | None = None, force: bool = False,
                    adapters: Adapters | None = None, root: Path | None = None) -> dict:
    """Deep fetch of one Instagram Reference the store has (see the module docstring)."""
    row = store.one("SELECT v.*, c.handle FROM video v LEFT JOIN channel c ON c.id = v.channel_id "
                    "WHERE v.platform = 'instagram' AND v.external_id = ?", (code,))
    if row is None:
        raise FetchError(f"Instagram Reference {code} is not in the store: scout its account, or add the link with "
                         f"`watchlist add-reference <watchlist> <link>`")
    language = DEFAULT_LANGUAGE
    if watchlist is not None:
        language = watchlists.get(store, watchlist).language or DEFAULT_LANGUAGE
    a = adapters or default_adapters()
    d = folder_for(code, watchlist, root)
    d.mkdir(parents=True, exist_ok=True)
    media = d / f"{code}.mp4"
    url = row["url"] or ingest.instagram_url(code)
    snap = store.one("SELECT taken_at, views, likes, comments FROM snapshot WHERE video_id = ? "
                     "ORDER BY views IS NULL, taken_at DESC LIMIT 1", (row["id"],)) or {}
    info = {"id": code, "title": row["title"], "description": row["description"], "webpage_url": url,
            "uploader_id": row["handle"], "view_count": snap.get("views"), "like_count": snap.get("likes"),
            "comment_count": snap.get("comments")}
    steps: dict[str, str] = {}
    why = None
    if force or not media.exists():
        try:
            got = a.download(url, d, code)
            steps["media"] = "downloaded"
            info["duration"] = got.get("duration")
        except FetchError as exc:
            why = str(exc)
            steps["media"] = f"unavailable: {why}"
    else:
        steps["media"] = "kept"
        old = d / "info.json"
        if old.exists():
            info["duration"] = _read(old).get("duration")
    has_media = media.exists()
    _write(d / "info.json", info)
    steps["captions"] = "none on Instagram"
    transcript = shotlog = frames = None
    if has_media:
        transcript = _transcript(a, d, media, language, force, steps)
        shotlog, frames = _shotlog_ocr(a, d, media, transcript, force, force, steps)
    else:
        for step in ("transcript", "proxy", "shotlog", "ocr"):
            steps[step] = "skipped (caption-only)"
    measured = measure.measure(info, transcript, shotlog, frames)
    measured["kind"] = measured["kind"] or row["kind"]
    measured["platform"] = "instagram"
    measured["caption"] = row["description"]
    measured["counts"] = {k: snap.get(k) for k in ("taken_at", "views", "likes", "comments")}
    if not has_media:
        measured["notes"]["media"] = CAPTION_ONLY.format(why=why or "no media file")
    with store.transaction() as c:
        c.execute("UPDATE video SET has_media = ?, has_transcript = ?, duration_s = COALESCE(?, duration_s) "
                  "WHERE id = ?", (int(has_media), int(transcript is not None), measured["duration_s"], row["id"]))
    saved = card.save(store, row["id"], measured, path=d / "card.json")
    return {"video_id": code, "video": row["id"], "title": row["title"], "dir": str(d), "watchlist": watchlist,
            "language": language, "channel_source": f"store ({row['handle'] or 'owner unknown'})",
            "platform": "instagram", "steps": steps, "captions": [], "card": saved}
