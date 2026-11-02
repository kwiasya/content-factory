"""Videos and snapshots from recorded Data API payloads; scout and snapshot over a fake transport. No network."""

import json
import tempfile
import unittest
from pathlib import Path

from cf.research import feed, ingest, scout
from cf.research import store as st
from datetime import timedelta
from unittest import mock

from cf.research import quota, youtube
from research_synth import NOW, FakeYouTube, add_member, add_videos, ago, channel_payload, iso, video_item
from cf.research import watchlist as wl

FIX = Path(__file__).parent / "fixtures" / "research"
SLOW = "UCxR9mXyZbC1dEf2GhIjKlMn"
LENS = "UCq1W2e3R4t5Y6u7I8o9P0aS"


def payload(name: str) -> dict:
    return json.loads((FIX / name).read_text())


class StoreCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db", create=True)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def watchlist_with_slowwalks(self, name="lisbon", queries=()):
        wl.create(self.store, name, format_id="walk_reel", language="en", region="US", queries=list(queries))
        ch = payload("channels_list_handle.json")
        wl.add_channel(self.store, name, "@slowwalks", transport=lambda m, p: ch)


class IngestVideosTest(StoreCase):
    def test_videos_list_items_become_references_of_their_channel(self):
        self.watchlist_with_slowwalks()
        ingest.ingest_videos(self.store, payload("videos_list_slowwalks_p1.json"))
        long_ = feed.reference(self.store, "dQw4w9WgXcQ")
        short = feed.reference(self.store, "Ab3dEf6hIj0")
        self.assertEqual((long_.title, long_.kind, long_.duration_s, long_.handle, long_.date),
                         ("Lisbon Alfama at Golden Hour — 4K Walk", "long", 2467.0, "@slowwalks", "2026-10-09"))
        self.assertEqual(long_.url, "https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual((short.kind, short.duration_s), ("short", 58.0))
        self.assertFalse(short.analyzed)
        self.assertIsNone(feed.reference(self.store, "nope"))

    def test_a_video_from_an_unknown_channel_brings_a_candidate_channel_outside_the_watchlist(self):
        self.watchlist_with_slowwalks()
        ingest.ingest_videos(self.store, payload("videos_list_lisbonlens.json"))
        self.assertEqual(feed.reference(self.store, "Lm4nOp5qRs6").channel_title, "Lisbon Lens")
        self.assertEqual([c.external_id for c in wl.channels(self.store, "lisbon")], [SLOW])

    def test_ingesting_twice_keeps_one_reference(self):
        self.watchlist_with_slowwalks()
        first = ingest.ingest_videos(self.store, payload("videos_list_slowwalks_p1.json"))
        again = ingest.ingest_videos(self.store, payload("videos_list_slowwalks_p1.json"))
        self.assertEqual(first, again)


class IngestSnapshotsTest(StoreCase):
    def test_each_run_adds_one_snapshot_per_video_and_keeps_the_history(self):
        self.watchlist_with_slowwalks()
        p1 = payload("videos_list_slowwalks_p1.json")
        ingest.ingest_videos(self.store, p1)
        ingest.ingest_snapshots(self.store, p1, taken_at="2026-10-10T07:00:00Z")
        p1["items"][1]["statistics"]["viewCount"] = "1300000"
        ingest.ingest_snapshots(self.store, p1, taken_at="2026-10-11T07:00:00Z")
        hist = scout.snapshot_history(self.store, "Ab3dEf6hIj0")
        self.assertEqual([(h.taken_at, h.views, h.likes, h.comments) for h in hist],
                         [("2026-10-10T07:00:00Z", 1_203_344, 88_120, None),
                          ("2026-10-11T07:00:00Z", 1_300_000, 88_120, None)])
        self.assertEqual(feed.reference(self.store, "Ab3dEf6hIj0").views, 1_300_000)
        self.assertEqual(feed.reference(self.store, "dQw4w9WgXcQ").comments, 402)

    def test_unknown_videos_get_no_snapshot(self):
        self.watchlist_with_slowwalks()
        got = ingest.ingest_snapshots(self.store, payload("videos_list_slowwalks_p1.json"),
                                      taken_at="2026-10-10T07:00:00Z")
        self.assertEqual(got, [])
        self.assertEqual(scout.snapshot_history(self.store, "Ab3dEf6hIj0"), [])


class IngestSearchTest(StoreCase):
    def test_search_results_become_references_of_the_watchlist_and_new_channels_candidates(self):
        self.watchlist_with_slowwalks(queries=["lisbon walk"])
        got = ingest.ingest_search(self.store, payload("search_list_lisbon.json"), watchlist="lisbon",
                                   query="lisbon walk", found_at="2026-10-11T07:00:00Z")
        self.assertEqual(got, ["Ab3dEf6hIj0", "Lm4nOp5qRs6"])
        lens = feed.reference(self.store, "Lm4nOp5qRs6")
        self.assertEqual((lens.title, lens.channel_title, lens.kind), (
            "Lisbon's 7 hills & the tram you should skip", "Lisbon Lens", None))
        self.assertEqual([c.external_id for c in wl.channels(self.store, "lisbon")], [SLOW])
        [cand] = scout.candidates(self.store, "lisbon")
        self.assertEqual((cand.external_id, cand.title, cand.hits, cand.queries),
                         (LENS, "Lisbon Lens", 1, ["lisbon walk"]))

    def test_search_hits_show_in_the_feed_marked_as_candidates_once_details_are_in(self):
        self.watchlist_with_slowwalks(queries=["lisbon walk"])
        ingest.ingest_search(self.store, payload("search_list_lisbon.json"), watchlist="lisbon",
                             query="lisbon walk")
        for name in ("videos_list_lisbonlens.json", "videos_list_slowwalks_p1.json"):
            ingest.ingest_videos(self.store, payload(name))
            ingest.ingest_snapshots(self.store, payload(name), taken_at="2026-10-11T07:00:00Z")
        rows = {r.external_id: r for r in feed.feed(self.store, "lisbon", lookback_days=30, now=NOW)}
        self.assertEqual(set(rows), {"Lm4nOp5qRs6", "Ab3dEf6hIj0", "dQw4w9WgXcQ"})
        self.assertTrue(rows["Lm4nOp5qRs6"].candidate)
        self.assertFalse(rows["Ab3dEf6hIj0"].candidate)
        self.assertEqual(rows["Lm4nOp5qRs6"].kind, "short")

    def test_repeating_a_search_does_not_duplicate(self):
        self.watchlist_with_slowwalks(queries=["lisbon walk"])
        for _ in range(2):
            ingest.ingest_search(self.store, payload("search_list_lisbon.json"), watchlist="lisbon",
                                 query="lisbon walk")
        [cand] = scout.candidates(self.store, "lisbon")
        self.assertEqual(cand.hits, 1)


class RecordedTransport:
    """Answers with recorded payloads keyed by method and page token or ids; remembers the calls."""

    def __init__(self, routes: dict):
        self.routes = routes
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, method, params):
        self.calls.append((method, dict(params)))
        key = params.get("pageToken") if method in ("playlistItems.list", "search.list") else params.get("id")
        return payload(self.routes[(method, key)])

    def methods(self):
        out = {}
        for m, _ in self.calls:
            out[m] = out.get(m, 0) + 1
        return out


SLOW_ROUTES = {
    ("playlistItems.list", None): "playlist_items_slowwalks_p1.json",
    ("playlistItems.list", "EAAaBlBUOkNESQ"): "playlist_items_slowwalks_p2.json",
    ("videos.list", "dQw4w9WgXcQ,Ab3dEf6hIj0"): "videos_list_slowwalks_p1.json",
    ("videos.list", "Zx9yW8vU7tS"): "videos_list_slowwalks_p2.json",
}


class ScoutUploadsTest(StoreCase):
    def test_first_scout_pages_the_whole_short_history_and_snapshots_what_it_found(self):
        self.watchlist_with_slowwalks()
        t = RecordedTransport(SLOW_ROUTES)
        r = scout.scout(self.store, "lisbon", transport=t, now=NOW)
        self.assertIsNone(r.stopped)
        self.assertEqual(t.methods(), {"playlistItems.list": 2, "videos.list": 2})
        [ch] = r.channels
        self.assertEqual((ch.handle, ch.mode, ch.pages, ch.new_videos, ch.shorts, ch.longs, ch.backfilled),
                         ("@slowwalks", "backfill", 2, 3, 1, 2, True))
        rows = feed.feed(self.store, "lisbon", lookback_days=60, now=NOW)
        self.assertEqual({x.external_id: x.views for x in rows},
                         {"dQw4w9WgXcQ": 184_022, "Ab3dEf6hIj0": 1_203_344, "Zx9yW8vU7tS": 40_210})
        self.assertEqual(len(scout.snapshot_history(self.store, "Zx9yW8vU7tS")), 1)

    def test_next_scout_reads_only_new_uploads_and_duplicates_nothing(self):
        self.watchlist_with_slowwalks()
        scout.scout(self.store, "lisbon", transport=RecordedTransport(SLOW_ROUTES), now=NOW)
        t = RecordedTransport(SLOW_ROUTES)
        r = scout.scout(self.store, "lisbon", transport=t, now=NOW)
        self.assertEqual(t.methods(), {"playlistItems.list": 1})
        self.assertEqual((r.channels[0].mode, r.channels[0].new_videos), ("new", 0))
        self.assertEqual(len(feed.feed(self.store, "lisbon", lookback_days=60, now=NOW)), 3)

    def synthetic_channel(self, yt, channel, n, *, kinds=("short", "long"), start_days=4):
        dur = {"short": 40, "long": 900}
        yt.uploads[channel] = [video_item(f"{channel[-4:]}{i:04d}", channel, ago(days=start_days + i),
                                          dur[kinds[i % len(kinds)]], 1000 + i) for i in range(n)]

    def test_first_scout_stops_once_thirty_of_each_kind_are_known(self):
        wl.create(self.store, "w", format_id="walk_reel")
        ch = "UCaaaaaaaaaaaaaaaaaa0001"
        add_member(self.store, "w", ch, "@mixed")
        yt = FakeYouTube()
        self.synthetic_channel(yt, ch, 200)
        r = scout.scout(self.store, "w", transport=yt, now=NOW)
        c = r.channels[0]
        self.assertEqual((c.pages, c.new_videos, c.shorts, c.longs, c.backfilled), (2, 100, 50, 50, True))
        yt.uploads[ch][:0] = [video_item(f"new{i}", ch, ago(hours=i + 1), 40, 5) for i in range(3)]
        yt.calls.clear()
        r = scout.scout(self.store, "w", transport=yt, now=NOW)
        self.assertEqual((r.channels[0].mode, r.channels[0].pages, r.channels[0].new_videos), ("new", 1, 3))
        self.assertEqual(yt.methods(), {"playlistItems.list": 1, "videos.list": 1})

    def test_a_channel_short_of_one_kind_is_paged_to_the_end_once(self):
        wl.create(self.store, "w", format_id="walk_reel")
        ch = "UCaaaaaaaaaaaaaaaaaa0002"
        add_member(self.store, "w", ch, "@shortsonly")
        yt = FakeYouTube()
        self.synthetic_channel(yt, ch, 120, kinds=("short",))
        c = scout.scout(self.store, "w", transport=yt, now=NOW).channels[0]
        self.assertEqual((c.pages, c.new_videos, c.shorts, c.longs, c.history_end, c.backfilled),
                         (3, 120, 120, 0, True, True))
        yt.calls.clear()
        c = scout.scout(self.store, "w", transport=yt, now=NOW).channels[0]
        self.assertEqual((c.mode, c.pages, c.new_videos), ("new", 1, 0))


    def backfilled_channel(self, yt, ch):
        """A Watchlist ``w`` whose one channel has 20 old uploads, already backfilled."""
        wl.create(self.store, "w", format_id="walk_reel")
        add_member(self.store, "w", ch, "@gappy")
        yt.uploads[ch] = [video_item(f"old{i:08d}", ch, ago(days=200 + i), 30, 1000) for i in range(20)]
        scout.scout(self.store, "w", search=False, transport=yt, now=NOW)

    def missing(self, items):
        have = {r["external_id"] for r in self.store.query("SELECT external_id FROM video")}
        return [v["id"] for v in items if v["id"] not in have]

    def test_an_upload_known_from_a_search_hit_does_not_end_the_paging(self):
        yt, ch = FakeYouTube(), "UCaaaaaaaaaaaaaaaaaa0003"
        self.backfilled_channel(yt, ch)
        new = [video_item(f"new{i:08d}", ch, ago(days=i * 0.1), 30, 1000) for i in range(70)]
        yt.uploads[ch] = new + yt.uploads[ch]
        add_videos(self.store, [new[10]])  # found earlier by a search query or a fetch
        c = scout.scout(self.store, "w", search=False, transport=yt, now=NOW).channels[0]
        self.assertEqual(self.missing(new), [])
        self.assertEqual((c.mode, c.pages, c.new_videos), ("new", 2, 69))

    def test_a_new_uploads_run_cut_by_the_quota_is_finished_by_the_next_run(self):
        yt, ch = FakeYouTube(), "UCaaaaaaaaaaaaaaaaaa0004"
        self.backfilled_channel(yt, ch)
        new = [video_item(f"new{i:08d}", ch, ago(days=i * 0.1), 30, 1000) for i in range(100)]
        yt.uploads[ch] = new + yt.uploads[ch]
        used = next(b.used for b in quota.usage(self.store).buckets if b.bucket == "default")
        with mock.patch.dict("os.environ", {"CF_QUOTA_DEFAULT": str(used + 2)}):  # page 1 and its videos
            r = scout.scout(self.store, "w", search=False, transport=yt, now=NOW)
        self.assertIn("quota", r.stopped)
        self.assertEqual(r.channels[0].new_videos, 50)
        r = scout.scout(self.store, "w", search=False, transport=yt, now=NOW)
        self.assertIsNone(r.stopped)
        self.assertEqual(self.missing(new), [])
        self.assertEqual((r.channels[0].pages, r.channels[0].new_videos), (3, 50))
        yt.calls.clear()
        r = scout.scout(self.store, "w", search=False, transport=yt, now=NOW)
        self.assertEqual((r.channels[0].pages, r.channels[0].new_videos), (1, 0))


class ScoutQuotaTest(StoreCase):
    def test_a_run_that_cannot_fit_is_refused_before_any_call(self):
        self.watchlist_with_slowwalks()
        t = RecordedTransport(SLOW_ROUTES)
        used = quota.usage(self.store).buckets
        with mock.patch.dict("os.environ", {"CF_QUOTA_DEFAULT": "2"}):  # add_channel already used 1
            with self.assertRaises(quota.QuotaExceeded):
                scout.scout(self.store, "lisbon", transport=t, now=NOW)
        self.assertEqual(t.calls, [])
        self.assertEqual(quota.usage(self.store).buckets, used)

    def test_running_out_mid_run_stops_cleanly_and_the_next_run_resumes(self):
        self.watchlist_with_slowwalks()
        t = RecordedTransport(SLOW_ROUTES)
        with mock.patch.dict("os.environ", {"CF_QUOTA_DEFAULT": "4"}):  # 1 used + p1, videos, p2; videos p2 refused
            r = scout.scout(self.store, "lisbon", transport=t, now=NOW)
        self.assertIn("quota", r.stopped)
        self.assertEqual(r.channels[0].new_videos, 2)
        self.assertFalse(r.channels[0].backfilled)
        self.assertEqual(len(feed.feed(self.store, "lisbon", lookback_days=60, now=NOW)), 2)
        t = RecordedTransport(SLOW_ROUTES)
        r = scout.scout(self.store, "lisbon", transport=t, now=NOW)
        self.assertIsNone(r.stopped)
        self.assertEqual((r.channels[0].mode, r.channels[0].new_videos, r.channels[0].backfilled),
                         ("backfill", 1, True))
        self.assertEqual(t.methods(), {"playlistItems.list": 2, "videos.list": 1})


class ScoutErrorTest(StoreCase):
    DEAD, ALIVE = "UCaaaaaaaaaaaaaaaaaa0005", "UCaaaaaaaaaaaaaaaaaa0006"

    def setUp(self):
        super().setUp()
        wl.create(self.store, "w", format_id="walk_reel", queries=["broken", "lisbon walk"])
        add_member(self.store, "w", self.DEAD, "@dead")
        add_member(self.store, "w", self.ALIVE, "@alive")
        self.yt = yt = FakeYouTube()
        yt.uploads[self.ALIVE] = [video_item(f"alive{i:06d}", self.ALIVE, ago(days=i + 1), 30, 100) for i in range(3)]
        yt.extra_videos["lens1"] = video_item("lens1", LENS, ago(days=2), 45, 70_000)
        yt.searches["lisbon walk"] = [{"items": [{"id": {"kind": "youtube#video", "videoId": "lens1"},
                                                  "snippet": {"channelId": LENS, "title": "lens1",
                                                              "publishedAt": ago(days=2)}}]}]
        yt.channels[LENS] = channel_payload(LENS, "@lisbonlens")["items"][0]

    def transport(self, method, params):
        if method == "playlistItems.list" and params["playlistId"] == "UU" + self.DEAD[2:]:
            self.yt.calls.append((method, dict(params)))
            raise youtube.YouTubeError("playlistItems.list: HTTP 404: playlist not found (playlistNotFound)")
        if method == "search.list" and params["q"] == "broken":
            self.yt.calls.append((method, dict(params)))
            raise youtube.YouTubeError("search.list: HTTP 400: bad request (invalidSearchFilter)")
        return self.yt(method, params)

    def test_a_failing_channel_or_query_is_reported_and_the_rest_of_the_run_goes_on(self):
        r = scout.scout(self.store, "w", transport=self.transport, now=NOW)
        self.assertIsNone(r.stopped)
        dead, alive = r.channels
        self.assertIn("playlistNotFound", dead.error)
        self.assertEqual((dead.handle, dead.pages, dead.new_videos, dead.backfilled), ("@dead", 0, 0, False))
        self.assertEqual((alive.error, alive.new_videos, alive.backfilled), (None, 3, True))
        broken, ok = r.queries
        self.assertIn("invalidSearchFilter", broken.error)
        self.assertEqual((ok.query, ok.error, ok.results), ("lisbon walk", None, 1))
        self.assertEqual([c.handle for c in r.candidates], ["@lisbonlens"])

    def test_the_failed_calls_stay_charged(self):
        before = quota.usage(self.store).by_method
        scout.scout(self.store, "w", transport=self.transport, now=NOW)
        calls = {m.method: m.calls for m in quota.usage(self.store).by_method}
        prior = {m.method: m.calls for m in before}
        self.assertEqual(calls["playlistItems.list"] - prior.get("playlistItems.list", 0), 2)
        self.assertEqual(calls["search.list"], 2)


class ScoutSearchTest(StoreCase):
    def routes(self):
        return {**SLOW_ROUTES,
                ("search.list", None): "search_list_lisbon.json",
                ("videos.list", "Ab3dEf6hIj0,Lm4nOp5qRs6"): "videos_list_lisbonlens.json",
                ("channels.list", LENS): "channels_list_lisbonlens.json"}

    def test_queries_bring_references_and_candidate_channels_with_their_handles(self):
        self.watchlist_with_slowwalks(queries=["lisbon walk"])
        t = RecordedTransport(self.routes())
        r = scout.scout(self.store, "lisbon", transport=t, now=NOW, search_days=14)
        self.assertIsNone(r.stopped)
        [(method, params)] = [c for c in t.calls if c[0] == "search.list"]
        self.assertEqual((params["q"], params["publishedAfter"], params["relevanceLanguage"],
                          params["regionCode"], params["order"]),
                         ("lisbon walk", ago(days=14), "en", "US", "viewCount"))
        [q] = r.queries
        self.assertEqual((q.query, q.pages, q.results), ("lisbon walk", 1, 2))
        [cand] = r.candidates
        self.assertEqual((cand.handle, cand.subscriber_count, cand.hits), ("@lisbonlens", 48_100, 1))
        lens = {x.external_id: x for x in feed.feed(self.store, "lisbon", now=NOW)}["Lm4nOp5qRs6"]
        self.assertEqual((lens.handle, lens.views, lens.kind, lens.candidate), ("@lisbonlens", 2_400_511, "short", True))
        self.assertEqual(t.methods()["search.list"], 1)

    def test_search_can_be_skipped(self):
        self.watchlist_with_slowwalks(queries=["lisbon walk"])
        t = RecordedTransport(self.routes())
        r = scout.scout(self.store, "lisbon", transport=t, now=NOW, search=False)
        self.assertNotIn("search.list", t.methods())
        self.assertEqual(r.queries, [])

    def test_more_pages_follow_the_next_page_token(self):
        wl.create(self.store, "w", format_id="walk_reel", queries=["q"])
        yt = FakeYouTube()
        hit = video_item("v1", LENS, ago(days=1), 40, 10, channel_title="Lisbon Lens")
        page = {"items": [{"id": {"kind": "youtube#video", "videoId": "v1"},
                           "snippet": {"channelId": LENS, "title": "v1", "channelTitle": "Lisbon Lens",
                                       "publishedAt": ago(days=1)}}]}
        yt.searches["q"] = [{**page, "nextPageToken": "1"}, page]
        yt.extra_videos["v1"] = hit
        yt.channels[LENS] = channel_payload(LENS, "@lisbonlens")["items"][0]
        r = scout.scout(self.store, "w", transport=yt, now=NOW, search_pages=3)
        self.assertEqual((r.queries[0].pages, r.queries[0].results), (2, 1))


class SnapshotTest(StoreCase):
    def setUp(self):
        super().setUp()
        wl.create(self.store, "w", format_id="walk_reel", queries=["q"])
        self.ch = "UCaaaaaaaaaaaaaaaaaa0001"
        add_member(self.store, "w", self.ch, "@mixed")
        self.yt = yt = FakeYouTube()
        yt.uploads[self.ch] = [video_item(f"v{i:03d}", self.ch, ago(days=4 + i), 40 if i % 2 else 900, 100 + i)
                               for i in range(60)]
        hit = video_item("lens1", LENS, ago(days=1), 40, 7_000, channel_title="Lisbon Lens")
        yt.extra_videos["lens1"] = hit
        yt.searches["q"] = [{"items": [{"id": {"kind": "youtube#video", "videoId": "lens1"},
                                        "snippet": {"channelId": LENS, "title": "lens1", "publishedAt": ago(days=1),
                                                    "channelTitle": "Lisbon Lens"}}]}]
        yt.channels[LENS] = channel_payload(LENS, "@lisbonlens")["items"][0]
        scout.scout(self.store, "w", transport=yt, now=NOW)
        yt.calls.clear()

    def test_one_snapshot_per_reference_per_run_in_batches_of_fifty_search_hits_included(self):
        for v in self.yt.uploads[self.ch]:
            v["statistics"]["viewCount"] = str(int(v["statistics"]["viewCount"]) + 1000)
        later = NOW + timedelta(days=1)
        r = scout.snapshot(self.store, "w", transport=self.yt, now=later)
        self.assertEqual((r.videos, r.missing, r.stopped), (61, [], None))
        self.assertEqual(self.yt.methods(), {"videos.list": 2})
        self.assertTrue(all(len(params["id"].split(",")) <= 50 for _, params in self.yt.calls))
        hist = scout.snapshot_history(self.store, "v000")
        self.assertEqual([(h.taken_at, h.views) for h in hist], [(iso(NOW), 100), (iso(later), 1100)])
        self.assertEqual(len(scout.snapshot_history(self.store, "lens1")), 2)

    def test_videos_gone_from_youtube_are_reported_missing(self):
        del self.yt.uploads[self.ch][5]
        r = scout.snapshot(self.store, "w", transport=self.yt, now=NOW + timedelta(days=1))
        self.assertEqual((r.videos, r.missing), (60, ["v005"]))

    def test_a_snapshot_that_cannot_fit_is_refused_before_any_call(self):
        used = sum(b.used for b in quota.usage(self.store).buckets if b.bucket == "default")
        with mock.patch.dict("os.environ", {"CF_QUOTA_DEFAULT": str(used + 1)}):
            with self.assertRaises(quota.QuotaExceeded):
                scout.snapshot(self.store, "w", transport=self.yt, now=NOW + timedelta(days=1))
        self.assertEqual(self.yt.calls, [])


if __name__ == "__main__":
    unittest.main()
