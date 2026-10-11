"""Deep fetch of one Reference by URL or video id, even outside every Watchlist.

Steps, each skipped when its artifact is already in the Reference folder
(``<footage root>/references/<watchlist or _adhoc>/<video_id>/``) unless ``force``:

1. yt-dlp info (always refreshed: fresh view/like/comment counts) and media up
   to 720p (``<video_id>.mp4``, downloaded once), ``info.json`` next to it;
2. the channel, ingested through ``channels.list`` when the store does not know
   it (no Watchlist membership), the ``video`` row and a ``snapshot``;
3. ``transcript.json``: stable-ts with word timestamps, language of the
   Watchlist (English without one);
4. ``proxy.mp4`` and ``shotlog.json`` through ``cf.proxy.proxy_file`` and
   ``cf.shotlog.analyze_proxy`` (its speech pass reuses the transcript);
5. ``ocr.json``: on-screen text of the first seconds (Apple Vision);
6. the card: ``measured`` from ``cf.research.measure``, ``analysis`` kept.

Adapters (yt-dlp, stable-ts, proxy, Shot log, OCR, Data API transport) come
in through ``Adapters`` so tests replace them; the logic here is pure.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import parse_qs, urlsplit

from cf.research import card, ingest, measure, quota, youtube
from cf.research import watchlist as watchlists
from cf.research.kinds import video_kind
from cf.research.store import Store, dumps, footage_root, now_iso

VIDEO_ID_RE = re.compile(r"^[\w-]{11}$")
YOUTUBE_HOSTS = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com"}
VIDEO_PATHS = {"shorts", "live", "embed", "v"}
# Bulky or volatile info keys left out of ``video.raw`` (info.json on disk keeps everything).
RAW_DROP = ("formats", "requested_formats", "requested_downloads", "thumbnails", "automatic_captions",
            "subtitles", "requested_subtitles", "http_headers", "_format_sort_fields", "_version")


DEFAULT_LANGUAGE = "en"
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
    - ``transport``: Data API transport for ``channels.list`` (None: HTTP with ``YOUTUBE_API_KEY``).
    """
    extract: Callable[[str], dict]
    download: Callable[[str, Path, str], dict]
    transcribe: Callable[[Path, str | None], dict]
    proxy: Callable[[Path, Path, bool], dict]
    shotlog: Callable[[Path, Path, dict], dict]
    ocr: Callable[[Path], list | None]
    transport: youtube.Transport | None = None


def default_adapters() -> Adapters:
    """yt-dlp, stable-ts, cf.proxy, cf.shotlog and Apple Vision OCR (imported on first use)."""
    from cf.research import ocr, stablets, ytdlp

    def proxy(media: Path, dest: Path, force: bool) -> dict:
        from cf.proxy import proxy_file
        return proxy_file(media, dest, force=force)

    return Adapters(extract=ytdlp.extract, download=ytdlp.download, transcribe=stablets.transcribe,
                    proxy=proxy, shotlog=stablets.shotlog, ocr=ocr.first_seconds)


def parse_video_ref(text: str) -> str:
    """The 11-character video id in a bare id or a YouTube video URL (watch, youtu.be, shorts, live, embed)."""
    t = (text or "").strip()
    if VIDEO_ID_RE.match(t):
        return t
    if "/" not in t:
        raise FetchError(f"not a YouTube video id or URL: {text!r}")
    parts = urlsplit(t if "://" in t else "https://" + t)
    host = (parts.hostname or "").lower()
    segs = [s for s in parts.path.split("/") if s]
    vid = None
    if host in {"youtu.be", "www.youtu.be"} and segs:
        vid = segs[0]
    elif host in YOUTUBE_HOSTS:
        if segs[:1] == ["watch"]:
            vid = (parse_qs(parts.query).get("v") or [None])[0]
        elif len(segs) > 1 and segs[0] in VIDEO_PATHS:
            vid = segs[1]
    if vid is None or not VIDEO_ID_RE.match(vid):
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
        return datetime.fromtimestamp(int(ts), timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
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
        vid = ingest._upsert_video(c, row, channel_id, own)
        snap = snapshot_from_info(info)
        c.execute("INSERT INTO snapshot (video_id, taken_at, views, likes, comments) VALUES (?, ?, ?, ?, ?) "
                  "ON CONFLICT (video_id, taken_at) DO UPDATE SET views = excluded.views, "
                  "likes = excluded.likes, comments = excluded.comments",
                  (vid, ts, snap["views"], snap["likes"], snap["comments"]))
    return {"video_id": vid, "channel_id": channel_id, "channel_source": source}


def reference_dir(video_id: str, watchlist: str | None = None, root: Path | None = None) -> Path:
    """``<footage root>/references/<watchlist or _adhoc>/<video_id>/``."""
    return Path(root or footage_root()) / "references" / (watchlist or ADHOC) / video_id


def _read(path: Path):
    return json.loads(path.read_text())


def _write(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n")
    tmp.replace(path)


def fetch(store: Store, ref: str, *, watchlist: str | None = None, force: bool = False,
          adapters: Adapters | None = None, root: Path | None = None) -> dict:
    """Deep fetch of one Reference (see the module docstring); returns what was done and the card.

    Result: ``video_id`` (YouTube id), ``video`` (store id), ``dir``, ``channel_source``,
    ``steps`` (per artifact: made, kept, downloaded, FAILED: …), ``card``.
    """
    vid = parse_video_ref(ref)
    language = DEFAULT_LANGUAGE
    if watchlist is not None:
        language = watchlists.get(store, watchlist).language or DEFAULT_LANGUAGE
    a = adapters or default_adapters()
    d = reference_dir(vid, watchlist, root)
    d.mkdir(parents=True, exist_ok=True)
    media = d / f"{vid}.mp4"
    url = f"https://www.youtube.com/watch?v={vid}"
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

    tr_path = d / "transcript.json"
    if force or not tr_path.exists():
        transcript = a.transcribe(media, language)
        _write(tr_path, transcript)
        steps["transcript"] = "made"
    else:
        transcript = _read(tr_path)
        steps["transcript"] = "kept"

    rec = record_info(store, info, transport=a.transport, media=True, transcript=True)

    shotlog = None
    sl_path = d / "shotlog.json"
    px = a.proxy(media, d / "proxy.mp4", force)
    if px.get("status") == "FAILED" or not px.get("proxy_path"):
        steps["proxy"] = f"FAILED: {px.get('error') or 'no proxy'}"
        steps["shotlog"] = "skipped (no proxy)"
    else:
        steps["proxy"] = px["status"]
        if force or px["status"] == "made" or not sl_path.exists():
            shotlog = a.shotlog(Path(px["proxy_path"]), media, transcript)
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

    measured = measure.measure(info, transcript, shotlog, frames)
    saved = card.save(store, rec["video_id"], measured, path=d / "card.json")
    return {"video_id": vid, "video": rec["video_id"], "title": info.get("title"), "dir": str(d),
            "watchlist": watchlist, "language": language, "channel_source": rec["channel_source"],
            "steps": steps, "card": saved}
