"""Thin yt-dlp adapter for the deep fetch: info dict and media up to 720p. No unit tests (manual smoke).

``res:720`` is a format *sort* key on the smaller side, not a height filter, so a
vertical Short comes as 720x1280 and a landscape video as 1280x720; H.264 and
AAC are preferred so ffmpeg/VideoToolbox decode it. YouTube needs a JS runtime
(deno, default) and the ``yt-dlp-ejs`` scripts (``yt-dlp[default]``). Sign-in
walls are reported, never worked around with browser cookies.
"""

from __future__ import annotations

from pathlib import Path

from cf.research.fetch import FetchError

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
