"""Shared test builders: synthetic videos.list payloads and snapshots (Outlier score, feed),
card analyses, Ideas and the store cases the summary, hooks, ideas and brief tests build on."""

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from cf.research import card, ideas, ingest
from cf.research import store as st
from cf.research import watchlist as wl

NOW = datetime(2026, 10, 11, 12, 0, 0, tzinfo=timezone.utc)


def iso(t: datetime) -> str:
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")


def ago(days: float = 0, hours: float = 0) -> str:
    return iso(NOW - timedelta(days=days, hours=hours))


def video_item(vid: str, channel: str, published_at: str, duration_s: int, views: int | None,
               title: str | None = None, channel_title: str | None = None) -> dict:
    m, s = divmod(duration_s, 60)
    h, m = divmod(m, 60)
    dur = "PT" + (f"{h}H" if h else "") + (f"{m}M" if m else "") + (f"{s}S" if s else "")
    stats = {"likeCount": "1", "favoriteCount": "0"}
    if views is not None:
        stats["viewCount"] = str(views)
    return {"kind": "youtube#video", "id": vid,
            "snippet": {"publishedAt": published_at, "channelId": channel, "title": title or f"video {vid}",
                        "description": "", "channelTitle": channel_title or channel},
            "contentDetails": {"duration": dur}, "statistics": stats}


def add_videos(store, items: list[dict], taken_at: str | None = None) -> None:
    """Ingest ``items`` and record one snapshot of them at ``taken_at`` (default: NOW)."""
    p = {"items": items}
    ingest.ingest_videos(store, p)
    ingest.ingest_snapshots(store, p, taken_at=taken_at or iso(NOW))


def channel_payload(channel: str, handle: str, title: str | None = None) -> dict:
    """A ``channels.list`` payload for one synthetic channel."""
    return {"items": [{"id": channel,
                       "snippet": {"title": title or handle.lstrip("@").title(), "customUrl": handle},
                       "contentDetails": {"relatedPlaylists": {"uploads": "UU" + channel[2:]}},
                       "statistics": {"subscriberCount": "1000", "videoCount": "10", "viewCount": "100000"}}]}


def add_member(store, watchlist: str, channel: str, handle: str) -> None:
    p = channel_payload(channel, handle)
    wl.add_channel(store, watchlist, channel, transport=lambda m, params: p)


class FakeYouTube:
    """A Data API stand-in: channel uploads, videos, search pages and channels from in-memory data.

    ``uploads[channel_id]`` is a list of ``videos.list`` items, newest first;
    ``searches[q]`` a list of ``search.list`` payloads (pages); ``channels`` maps a
    channel id to its ``channels.list`` item. Every call is recorded in ``calls``.
    """

    def __init__(self):
        self.uploads: dict[str, list[dict]] = {}
        self.searches: dict[str, list[dict]] = {}
        self.channels: dict[str, dict] = {}
        self.extra_videos: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []

    def methods(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for m, _ in self.calls:
            out[m] = out.get(m, 0) + 1
        return out

    def _videos(self) -> dict[str, dict]:
        allv = dict(self.extra_videos)
        for items in self.uploads.values():
            allv.update({v["id"]: v for v in items})
        return allv

    def __call__(self, method: str, params: dict) -> dict:
        self.calls.append((method, dict(params)))
        if method == "playlistItems.list":
            items = self.uploads.get("UC" + params["playlistId"][2:], [])
            start = int(params.get("pageToken") or 0)
            size = int(params.get("maxResults") or 50)
            page = items[start:start + size]
            out = {"items": [{"snippet": {"title": v["snippet"]["title"],
                                          "resourceId": {"kind": "youtube#video", "videoId": v["id"]}},
                              "contentDetails": {"videoId": v["id"], "videoPublishedAt": v["snippet"]["publishedAt"]}}
                             for v in page]}
            if start + size < len(items):
                out["nextPageToken"] = str(start + size)
            return out
        if method == "videos.list":
            allv = self._videos()
            return {"items": [allv[i] for i in params["id"].split(",") if i in allv]}
        if method == "search.list":
            pages = self.searches.get(params["q"], [{"items": []}])
            return pages[int(params.get("pageToken") or 0)]
        if method == "channels.list":
            return {"items": [self.channels[i] for i in params["id"].split(",") if i in self.channels]}
        raise AssertionError(f"unexpected call {method}")


# --- card analyses --------------------------------------------------------------

TRANSCRIPT = ("So this is Alfama, the oldest part of Lisbon. Watch the stairs. "
              "Okay, sunset time.")
MEASURED = {"duration_s": 95.0, "spoken_hook": "So this is Alfama, the oldest part of Lisbon."}


def analysis(**over) -> dict:
    a = {
        "summary": "A slow evening walk through Alfama that ends on the river at sunset.",
        "idea_analysis": {
            "topic": "Walking Lisbon's oldest district",
            "idea_seed": "The old town is best seen on foot at golden hour",
            "unique_angle": "No narration after the first line; the stairs carry the story",
            "common_belief": "Alfama is a tourist trap",
            "contrarian_reality": "Ten minutes off the tram line it is empty",
            "supporting_evidence": "Empty alleys from 0:40 on; the sunset viewpoint at 1:30",
        },
        "hook": {
            "category": "visual_payoff",
            "formula": "Place name + superlative, said over the best view",
            "spoken_hook": "So this is Alfama, the oldest part of Lisbon",
            "alignment": "The promise of the oldest part pays off in the stairs and alleys",
        },
        "storytelling_format": {
            "category": "pov",
            "description": "First-person walk from the top of the hill to the river",
            "analysis": "The descent gives a natural arc that ends at the payoff",
        },
        "visual_layout": {"category": "pov_walk", "sub_category": "vlog_pov"},
    }
    for path, value in over.items():
        node = a
        *head, last = path.split("__")
        for k in head:
            node = node[k]
        node[last] = value
    return a


# --- Ideas ----------------------------------------------------------------------

CHANNEL_A = "UCaaaaaaaaaaaaaaaaaaaaaa"  # Reference channel with a baseline of 1 000 views per short
CHANNEL_B = "UCbbbbbbbbbbbbbbbbbbbbbb"  # Reference channel without a baseline: no Outlier score
CHANNEL_C = "UCcccccccccccccccccccccc"  # another Watchlist's channel
V1, V2, V3 = "alfamaDusk1", "portoStair2", "sintraFog03"


def fields(**over) -> dict:
    f = {
        "title": "Lisbon's oldest district at golden hour, no narration",
        "summary": "A silent descent through Alfama that ends on the river at sunset.",
        "content_positioning": "The empty side of a district everyone calls a tourist trap",
        "storytelling_format": {"category": "pov", "why": "The descent is the arc; the river is the payoff"},
        "contrast_mechanism": {"common_belief": "Alfama is a tourist trap",
                               "contrarian_reality": "Ten minutes off the tram line it is empty"},
        "hook_alignment": "Open on the best view and name the place; the stairs keep the promise",
        "personalizations": ["Do it in Tbilisi's old town", "Shoot at dawn instead of dusk",
                             "Say the hook in Russian over the first view"],
    }
    f.update(over)
    return f


def add_card(store, external_id: str, a: dict | None = None) -> None:
    vid = store.one("SELECT id FROM video WHERE external_id = ?", (external_id,))["id"]
    with store.transaction() as c:
        c.execute("INSERT INTO card (video_id, schema, measured, analysis, written_at) "
                  "VALUES (?, 'cf-reference-card/1', '{}', ?, ?)",
                  (vid, None if a is None else json.dumps(a), ago(hours=1)))


class IdeasCase(unittest.TestCase):
    """Watchlist lisbon (Author's Channel travelwalks) with channel A: a baseline and V1 (9x), V2 (5x), V3 (3x)."""
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        s = self.store = st.open_store(Path(self.tmp.name) / "f.db", create=True)
        self.addCleanup(s.close)
        wl.create(s, "lisbon", format_id="walk_reel", author_channel="travelwalks")
        wl.create(s, "other", format_id="travel_long")
        add_member(s, "lisbon", CHANNEL_A, "@alpha")
        add_videos(s, [video_item(f"base{i:07d}", CHANNEL_A, ago(days=10 + i), 40, 1000) for i in range(5)]
                   + [video_item(V1, CHANNEL_A, ago(days=2), 40, 9000, title="Alfama at dusk"),
                      video_item(V2, CHANNEL_A, ago(days=3), 40, 5000, title="Porto stairs"),
                      video_item(V3, CHANNEL_A, ago(days=4), 40, 3000, title="Sintra fog")])

    def add(self, sources=(V1,), wlname="lisbon", **over):
        return ideas.add(self.store, wlname, list(sources), fields(**over))


# --- summaries ------------------------------------------------------------------

def put_card(store, external_id: str, a: dict | None, spoken_hook: str | None = "measured words") -> None:
    """A card as the store holds it; the analysis goes in unvalidated, as an old card might."""
    vid = store.one("SELECT id FROM video WHERE external_id = ?", (external_id,))["id"]
    card.save(store, vid, {"duration_s": 40.0, "spoken_hook": spoken_hook})
    if a is not None:
        store.conn.execute("UPDATE card SET analysis = ? WHERE video_id = ?", (json.dumps(a), vid))
        store.conn.commit()


def hook(category: str, formula: str = "a formula", spoken: str | None = "a spoken hook", **over) -> dict:
    return analysis(hook__category=category, hook__formula=formula, hook__spoken_hook=spoken, **over)


class SummaryCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s = self.store = st.open_store(Path(self.tmp.name) / "f.db", create=True)
        wl.create(s, "lisbon", format_id="walk-reel")
        wl.create(s, "other", format_id="tech-explainer")
        add_member(s, "lisbon", CHANNEL_A, "@alpha")
        add_member(s, "lisbon", CHANNEL_B, "@beta")
        add_member(s, "other", CHANNEL_C, "@gamma")
        add_videos(s, [video_item(f"baseline0{i:02d}", CHANNEL_A, ago(days=20 + i), 40, 1000) for i in range(6)]
                   + [video_item("oldHit00001", CHANNEL_A, ago(days=20), 40, 1000),
                      video_item("alfamaDawn1", CHANNEL_A, ago(days=2), 40, 5000, title="Alfama at dawn"),
                      video_item("gracaStair2", CHANNEL_A, ago(days=2), 40, 3000, title="Graça stairs"),
                      video_item("steepLisbn3", CHANNEL_A, ago(days=1), 40, 9000, title="Why is Lisbon so steep?"),
                      video_item("sunsetSoon4", CHANNEL_A, ago(days=1), 40, 2000, title="Sunset soon"),
                      video_item("waitForSun5", CHANNEL_A, ago(days=1), 40, 1500, title="Wait for the sun"),
                      video_item("uncardHit01", CHANNEL_A, ago(days=1), 40, 6000, title="Uncarded hit"),
                      video_item("uncardMeh02", CHANNEL_A, ago(days=1), 40, 1500, title="Uncarded meh"),
                      video_item("measuredOn3", CHANNEL_A, ago(days=1), 40, 2500, title="Measured only"),
                      video_item("fiveViewpt1", CHANNEL_B, ago(days=1), 40, 70_000, title="Five viewpoints"),
                      video_item("threeCafes2", CHANNEL_B, ago(days=1), 40, 80_000, title="Three cafes"),
                      video_item("elsewhere01", CHANNEL_C, ago(days=1), 40, 1_000_000, title="Elsewhere")])
        put_card(s, "oldHit00001", hook("contrast"))
        put_card(s, "alfamaDawn1", hook("visual_payoff", "Place name + superlative", "So this is Alfama",
                               idea_analysis__topic="Walking Lisbon's oldest district"))
        put_card(s, "gracaStair2", hook("visual_payoff", "Stairs + count", "Two hundred steps",
                               idea_analysis__topic="  walking   lisbon's OLDEST district ",
                               storytelling_format__category="listicle"))
        put_card(s, "steepLisbn3", hook("question", "Why is <place> <adjective>?", "Why is Lisbon so steep",
                               idea_analysis__topic="Lisbon hills",
                               visual_layout__category="talking_head"))
        put_card(s, "sunsetSoon4", hook("proposed:sunset_tease", "Sunset in N minutes", "Sunset in ten minutes",
                               idea_analysis__topic="Sunset spots"))
        put_card(s, "waitForSun5", hook("sunset_tease", "Wait for it", None, idea_analysis__topic="sunset spots"))
        put_card(s, "fiveViewpt1", hook("list", "N viewpoints", "Five viewpoints", idea_analysis__topic="Viewpoints",
                               storytelling_format__category="listicle",
                               visual_layout__category="proposed:map_overlay"))
        put_card(s, "threeCafes2", hook("list", "N cafes", "Three cafes", idea_analysis__topic="Cafes",
                               storytelling_format__category="listicle",
                               visual_layout__category="map_overlay"))
        put_card(s, "measuredOn3", None)
        put_card(s, "elsewhere01", hook("contrast"))

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def section(self, result, kind):
        return next(sec for sec in result.sections if sec.kind == kind)
