"""Thin Pornhub adapter (ADR 0015): the public Webmasters API for one video, yt-dlp for a channel's list.

Mirrors ``instagram``: every public function takes the ``Store`` and charges the
hourly ``pornhub`` bucket through ``quota.charge`` *before* the call. No key,
no login, no cookies, and never a video download.

- ``video_by_id``: ``/webmasters/video_by_id?id=<viewkey>`` (title, duration,
  views, rating, votes, publish date, tags, categories, thumbnails); a missing
  video answers code 2001/2002, raised as ``PornhubError`` with that ``code``.
- ``list_uploads``: the API cannot list a channel, so yt-dlp's flat extraction of
  ``/<kind>/<slug>/videos`` gives the viewkeys, newest first (the default order,
  checked in spike S2; ``?o=mr`` only costs yt-dlp an extra request). One
  ``ph.list_page`` is charged per ``PAGE_SIZE`` listed.

``transport`` replaces the API call (``(path, params) -> payload``) and
``lister`` the listing (``(url, limit) -> viewkeys``); tests pass fakes. The real
ones keep ``MIN_INTERVAL_S`` between calls in a process and send a fixed desktop
User-Agent. HTTP 429 pauses the bucket for an hour (``quota.record_pressure``).
"""

from __future__ import annotations

import json
import math
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable

from cf.research import quota
from cf.research.store import Store

SITE = "https://www.pornhub.com"
API_PATH = "webmasters/video_by_id"
USER_AGENT = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) "
              "Chrome/130.0 Safari/537.36")
TIMEOUT_S = 30
MIN_INTERVAL_S = 1.0
PAGE_SIZE = 40
YT_DLP_VERSION = "2026.08.19"
NOT_FOUND_CODES = {"2001", "2002"}
RATE_LIMIT_STATUS = 429
PAUSE_MINUTES = 60
VIEWKEY_QUERY_RE = re.compile(r"viewkey=([0-9a-z]+)")

Transport = Callable[[str, dict], dict]
Lister = Callable[[str, int], list[str]]


class PornhubError(Exception):
    """The API or the listing answered with an error, or could not be reached. ``code``: the API's error
    code (``"2002"``: no such video) or the HTTP status."""

    def __init__(self, message: str, code: str | int | None = None):
        super().__init__(message)
        self.code = code


def missing(exc: PornhubError) -> bool:
    """True when the error says the video does not exist (deleted, private or never there)."""
    return str(exc.code) in NOT_FOUND_CODES


_last_call = [0.0]


def _pace() -> None:
    wait = MIN_INTERVAL_S - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()


def http_transport(path: str, params: dict) -> dict:
    """GET ``SITE/<path>?<params>`` with the fixed User-Agent and no cookies; the JSON body."""
    _pace()
    req = urllib.request.Request(f"{SITE}/{path}?{urllib.parse.urlencode(params)}",
                                 headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise PornhubError(f"Pornhub API: HTTP {exc.code}", exc.code) from None
    except urllib.error.URLError as exc:
        raise PornhubError(f"Pornhub API: cannot reach pornhub.com: {exc.reason}") from None
    except ValueError:
        raise PornhubError("Pornhub API: the answer is not JSON") from None


class RateLimited(quota.QuotaExceeded):
    """Pornhub refused an already charged call for its rate limit (HTTP 429)."""


def _refused(store: Store, method: str, exc: PornhubError) -> RateLimited:
    quota.record_pressure(store, "pornhub", 100, PAUSE_MINUTES)
    return RateLimited(f"quota: Pornhub refused {method} for its rate limit ({exc}); the pornhub "
                               f"bucket pauses for an hour")


def video_by_id(store: Store, viewkey: str, *, transport: Transport | None = None) -> dict:
    """The ``video`` object of one viewkey. ``PornhubError`` with ``code`` 2001/2002 when it is missing."""
    quota.charge(store, "ph.video_by_id")
    try:
        out = (transport or http_transport)(API_PATH, {"id": viewkey})
    except PornhubError as exc:
        if exc.code == RATE_LIMIT_STATUS:
            raise _refused(store, "ph.video_by_id", exc) from None
        raise
    video = out.get("video") if isinstance(out, dict) else None
    if not isinstance(video, dict):
        code = str((out or {}).get("code") or "") or None
        raise PornhubError(f"Pornhub API {viewkey}: {(out or {}).get('message') or 'no video in the answer'}"
                           f"{f' (code {code})' if code else ''}", code)
    return video


def viewkeys(info: dict) -> list[str]:
    """The viewkeys of a yt-dlp flat playlist (``entries[*].url`` view links), in its order."""
    out: list[str] = []
    for e in info.get("entries") or []:
        m = VIEWKEY_QUERY_RE.search(str((e or {}).get("url") or ""))
        if m and m.group(1) not in out:
            out.append(m.group(1))
    return out


def ytdlp_lister(url: str, limit: int) -> list[str]:
    """yt-dlp flat extraction of a channel's video list: viewkeys only, no video page, no download."""
    from yt_dlp import YoutubeDL
    from cf.research.ytdlp import _Silent

    _pace()
    opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": "in_playlist",
            "playlistend": limit, "http_headers": {"User-Agent": USER_AGENT}, "logger": _Silent()}
    try:
        with YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
    except Exception as exc:
        text = str(exc).replace("\n", " ")
        limited = f"HTTP Error {RATE_LIMIT_STATUS}" in text
        raise PornhubError(f"yt-dlp {url}: {text}", RATE_LIMIT_STATUS if limited else None) from None
    return viewkeys(info or {})


def pages(limit: int) -> int:
    """List pages a listing of ``limit`` videos reads (and charges)."""
    return max(math.ceil(limit / PAGE_SIZE), 1)


def list_uploads(store: Store, channel_ext_id: str, *, limit: int, lister: Lister | None = None) -> list[str]:
    """Up to ``limit`` viewkeys of a channel (``model/<slug>``, ``channels/<slug>``…), newest first."""
    quota.charge(store, "ph.list_page", calls=pages(limit))
    try:
        got = (lister or ytdlp_lister)(f"{SITE}/{channel_ext_id}/videos", limit)
    except PornhubError as exc:
        if exc.code == RATE_LIMIT_STATUS:
            raise _refused(store, "ph.list_page", exc) from None
        raise
    return list(got)[:limit]


def channel_exists(store: Store, channel_ext_id: str, *, lister: Lister | None = None) -> str | None:
    """The channel's title (its slug: the listing has no other) when it lists at least one video, else None."""
    if not list_uploads(store, channel_ext_id, limit=1, lister=lister):
        return None
    return channel_ext_id.split("/", 1)[-1]
