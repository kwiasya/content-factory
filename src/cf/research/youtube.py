"""Thin YouTube Data API v3 adapter: API key from ``YOUTUBE_API_KEY``, urllib, no logic.

Every public function takes the ``Store`` (quota is charged through ``quota.charge``
*before* the call, so a refused call is never made) and returns the raw JSON
payload, which ``ingest`` turns into rows. ``transport`` replaces the HTTP call:
a function ``(method, params) -> payload`` such as ``"channels.list"`` and its
query parameters (without the key). Tests pass recorded payloads through it.
Manual smoke only (no unit tests): one real channel, quota before and after.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Iterable

from cf.research import quota
from cf.research.store import Store

BASE_URL = "https://www.googleapis.com/youtube/v3/"
TIMEOUT_S = 30
CHANNEL_PARTS = "snippet,statistics,contentDetails,topicDetails"
VIDEO_PARTS = "snippet,statistics,contentDetails,topicDetails"
MAX_IDS = 50

Transport = Callable[[str, dict], dict]


class YouTubeError(Exception):
    """The Data API answered with an error, or could not be reached."""


def http_transport(method: str, params: dict) -> dict:
    """GET ``BASE_URL/<resource>`` with the key from ``YOUTUBE_API_KEY``; return the JSON body."""
    key = os.environ.get("YOUTUBE_API_KEY")
    if not key:
        raise YouTubeError("YOUTUBE_API_KEY is not set; create an API key for YouTube Data API v3 "
                           "in Google Cloud Console and export it")
    resource = method.split(".")[0]
    query = urllib.parse.urlencode({**{k: v for k, v in params.items() if v is not None}, "key": key})
    try:
        with urllib.request.urlopen(f"{BASE_URL}{resource}?{query}", timeout=TIMEOUT_S) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            err = json.loads(exc.read().decode("utf-8")).get("error", {})
            reasons = ",".join(e.get("reason", "") for e in err.get("errors", []))
            msg = f"{err.get('message', exc.reason)} ({reasons})" if reasons else err.get("message", exc.reason)
        except (ValueError, AttributeError):
            msg = str(exc.reason)
        raise YouTubeError(f"{method}: HTTP {exc.code}: {msg}") from exc
    except urllib.error.URLError as exc:
        raise YouTubeError(f"{method}: cannot reach the YouTube API: {exc.reason}") from exc


def _call(store: Store, method: str, params: dict, transport: Transport | None) -> dict:
    if transport is None:  # fail on a missing key before charging a unit
        if not os.environ.get("YOUTUBE_API_KEY"):
            raise YouTubeError("YOUTUBE_API_KEY is not set; create an API key for YouTube Data API v3 "
                               "in Google Cloud Console and export it")
        transport = http_transport
    quota.charge(store, method)
    return transport(method, params)


def channels_list(store: Store, *, ids: Iterable[str] | None = None, handle: str | None = None,
                  username: str | None = None, part: str = CHANNEL_PARTS,
                  transport: Transport | None = None) -> dict:
    """``channels.list`` by up to 50 channel ids, one ``@handle`` or one legacy username."""
    params: dict = {"part": part}
    if ids is not None:
        ids = list(ids)
        if not 1 <= len(ids) <= MAX_IDS:
            raise ValueError(f"channels.list takes 1-{MAX_IDS} ids, got {len(ids)}")
        params["id"] = ",".join(ids)
        params["maxResults"] = len(ids)
    elif handle is not None:
        params["forHandle"] = handle
    elif username is not None:
        params["forUsername"] = username
    else:
        raise ValueError("channels.list needs ids, handle or username")
    return _call(store, "channels.list", params, transport)


def playlist_items_list(store: Store, playlist_id: str, *, page_token: str | None = None,
                        max_results: int = 50, transport: Transport | None = None) -> dict:
    """One page of ``playlistItems.list`` (a channel's uploads playlist, newest first)."""
    params = {"part": "snippet,contentDetails", "playlistId": playlist_id,
              "maxResults": max_results, "pageToken": page_token}
    return _call(store, "playlistItems.list", params, transport)


def videos_list(store: Store, ids: Iterable[str], *, part: str = VIDEO_PARTS,
                transport: Transport | None = None) -> dict:
    """``videos.list`` for up to 50 video ids (missing or private ids are absent from ``items``)."""
    ids = list(ids)
    if not 1 <= len(ids) <= MAX_IDS:
        raise ValueError(f"videos.list takes 1-{MAX_IDS} ids, got {len(ids)}")
    return _call(store, "videos.list", {"part": part, "id": ",".join(ids)}, transport)


def search_list(store: Store, q: str, *, published_after: str | None = None, order: str = "viewCount",
                relevance_language: str | None = None, region_code: str | None = None,
                video_duration: str | None = None, page_token: str | None = None,
                max_results: int = 50, transport: Transport | None = None) -> dict:
    """One page of ``search.list`` for videos matching ``q`` (own quota bucket: 100 calls a day)."""
    params = {"part": "snippet", "type": "video", "q": q, "order": order,
              "publishedAfter": published_after, "relevanceLanguage": relevance_language,
              "regionCode": region_code, "videoDuration": video_duration,
              "pageToken": page_token, "maxResults": max_results}
    return _call(store, "search.list", params, transport)
