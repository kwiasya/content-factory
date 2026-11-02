"""Thin yt-dlp adapter for the deep fetch: info dict, media up to 720p, captions. No unit tests (manual smoke).

``res:720`` is a format *sort* key on the smaller side, not a height filter, so a
vertical Short comes as 720x1280 and a landscape video as 1280x720; H.264 and
AAC are preferred so ffmpeg/VideoToolbox decode it. YouTube needs a JS runtime
(deno, default) and the ``yt-dlp-ejs`` scripts (``yt-dlp[default]``). Sign-in
walls are reported, never worked around with browser cookies. The same holds for
Instagram (ADR 0010): no cookies, no login; a refusal makes the card caption-only.
"""

from __future__ import annotations

import copy
import re
from pathlib import Path

from cf.research.fetch import LANGUAGE_ALIASES, FetchError

FORMAT = "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b"
FORMAT_SORT = ["res:720", "vcodec:h264", "acodec:aac"]
NOT_VOD = {"is_live", "is_upcoming", "post_live"}


def _base() -> dict:
    return {"quiet": True, "no_warnings": True, "noprogress": True, "retries": 3, "noplaylist": True}


def _check(info: dict) -> None:
    if info.get("live_status") in NOT_VOD:
        raise FetchError(f"{info.get('id')}: {info['live_status']}; only finished videos can be fetched")


def extract(url: str) -> dict:
    """The info dict (chapters, heatmap, captions list, counts) without downloading media."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    try:
        # same format choice as download(), so info.json describes the media on disk
        with YoutubeDL(_base() | {"skip_download": True, "format": FORMAT, "format_sort": FORMAT_SORT}) as ydl:
            info = ydl.sanitize_info(ydl.extract_info(url, download=False))
    except (DownloadError, ExtractorError) as exc:
        raise FetchError(f"yt-dlp: {exc}".replace("\n", " ")) from exc
    _check(info)
    return info


class _Silent:
    """A yt-dlp logger that drops everything: the error comes back as ``FetchError``."""

    def debug(self, msg: str) -> None:
        pass

    warning = error = info = debug


def metadata(url: str) -> dict:
    """Metadata only (no format choice, no download, no cookies, no login): what an Instagram owner
    lookup needs (``channel`` is the owner's username, ``description`` the caption, counts)."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    try:
        with YoutubeDL(_base() | {"skip_download": True, "logger": _Silent()}) as ydl:
            return ydl.sanitize_info(ydl.extract_info(url, download=False, process=False))
    except (DownloadError, ExtractorError) as exc:
        raise FetchError(f"yt-dlp: {exc}".replace("\n", " ")) from exc


def download(url: str, ref_dir: Path, video_id: str) -> dict:
    """Download the media to ``ref_dir/<video_id>.mp4`` (replacing an older file); return the info dict."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    from cf.metrics.common import ffmpeg_bin

    ref_dir.mkdir(parents=True, exist_ok=True)
    opts = _base() | {
        "format": FORMAT, "format_sort": FORMAT_SORT, "merge_output_format": "mp4",
        "postprocessors": [{"key": "FFmpegVideoRemuxer", "preferedformat": "mp4"}],
        "outtmpl": {"default": str(ref_dir / f"{video_id}.%(ext)s")},
        "ffmpeg_location": ffmpeg_bin(), "overwrites": True, "sleep_interval_requests": 1,
    }
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            _check(info)
            info = ydl.process_ie_result(info, download=True)
            info = ydl.sanitize_info(info)
    except (DownloadError, ExtractorError) as exc:
        raise FetchError(f"yt-dlp: {exc}".replace("\n", " ")) from exc
    media = ref_dir / f"{video_id}.mp4"
    if not media.exists():
        got = [Path(d["filepath"]) for d in info.get("requested_downloads") or [] if d.get("filepath")]
        if got and got[0].exists():
            got[0].replace(media)
    return info


# subtitles first, then auto-captions: each pass names its files apart, since yt-dlp
# would otherwise write the uploader's subtitles and YouTube's captions to the same name
CAPTION_PASSES = (("subs", {"writesubtitles": True}), ("auto", {"writeautomaticsub": True}))


def caption_codes(language: str | None) -> list[str]:
    """The Whisper code and YouTube's legacy aliases of it (``he`` gives ``he`` and ``iw``)."""
    lang = language or "en"
    return [lang] + sorted(k for k, v in LANGUAGE_ALIASES.items() if v == lang)


def _translated(formats: list) -> bool:
    return any("tlang=" in (f.get("url") or "") for f in formats or [])


def caption_langs(info: dict, language: str | None) -> dict[str, list[str]]:
    """``subtitleslangs`` per caption pass: the uploader's subtitles in any variant of the language,
    YouTube's auto-captions only untranslated ones, ``<lang>-orig`` alone when it is listed."""
    codes = caption_codes(language)
    auto = [k for k, f in (info.get("automatic_captions") or {}).items()
            if re.split(r"[-_]", k)[0].lower() in codes and not _translated(f)]
    orig = [k for k in auto if k.endswith("-orig")]
    return {"subs": [re.escape(c) + r"(-[\w-]+)?" for c in codes],
            "auto": [re.escape(k) for k in sorted(orig or auto)]}


def captions(info: dict, ref_dir: Path, video_id: str, language: str) -> list[str]:
    """Write the subtitles and auto-captions of ``language`` listed in ``info`` as WebVTT text:
    ``<video_id>.subs.<lang>.vtt`` and ``<video_id>.auto.<lang>.vtt`` (``caption_langs`` picks which;
    YouTube's machine translations are never taken). No media is downloaded. Returns the file names
    written (empty when YouTube has none)."""
    from yt_dlp import YoutubeDL
    from yt_dlp.utils import DownloadError, ExtractorError

    ref_dir.mkdir(parents=True, exist_ok=True)
    langs = caption_langs(info, language)
    written: list[str] = []
    for tag, flags in CAPTION_PASSES:
        if not langs[tag]:
            continue
        opts = _base() | flags | {
            "skip_download": True, "format": FORMAT, "format_sort": FORMAT_SORT,
            "subtitleslangs": langs[tag], "subtitlesformat": "vtt/best", "overwrites": True,
            "outtmpl": {"default": str(ref_dir / f"{video_id}.{tag}.%(ext)s")},
        }
        try:
            with YoutubeDL(opts) as ydl:
                ydl.process_ie_result(copy.deepcopy(info), download=True)
        except (DownloadError, ExtractorError) as exc:
            raise FetchError(f"yt-dlp captions: {exc}".replace("\n", " ")) from exc
        written += sorted(p.name for p in ref_dir.glob(f"{video_id}.{tag}.*.vtt"))
    return written
