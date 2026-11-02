"""Pornhub as a third research Platform (ADR 0015): the Webmasters API adapter, yt-dlp listing,
ingest, channel refs, scout and snapshot over fake transports, picks, fetch without video, cards,
the feed and the traits report. Synthetic fixtures only; no network."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import timedelta
from pathlib import Path
from unittest import mock

import cv2
import numpy as np
from research_synth import NOW, analysis, iso

from cf.research import card, cli, feed, fetch, ingest, picks, pornhub, quota, scout, traits
from cf.research import store as st
from cf.research import watchlist as wl

FIX = Path(__file__).parent / "fixtures" / "research"
VK = "6a1b2c3d4e5f0"


def payload(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def ph_video(vk: str, when: str, views: int, *, duration: str = "12:00", rating: float = 80.0, ratings: int = 100,
             title: str | None = None, tags: tuple[str, ...] = (), categories: tuple[str, ...] = ()) -> dict:
    """One synthetic ``video_by_id`` video object; ``when`` is ISO UTC."""
    return {"video_id": vk, "title": title or f"upload {vk}", "duration": duration, "views": views,
            "rating": rating, "ratings": ratings, "publish_date": when.replace("T", " ").rstrip("Z"),
            "url": f"https://www.pornhub.com/view_video.php?viewkey={vk}", "segment": "straight",
            "default_thumb": f"https://ei.example.test/{vk}/thumb.jpg",
            "thumbs": [{"src": f"https://ei.example.test/{vk}/{i}.jpg"} for i in range(1, 17)],
            "tags": [{"tag_name": t} for t in tags], "categories": [{"category": c} for c in categories],
            "pornstars": []}


class FakePH:
    """Webmasters API and yt-dlp listing stand-in: ``videos[viewkey]`` answers ``video_by_id`` (a missing key
    answers code 2002), ``uploads[channel]`` lists viewkeys newest first. Calls are recorded."""

    def __init__(self):
        self.videos: dict[str, dict] = {}
        self.uploads: dict[str, list[str]] = {}
        self.calls: list[tuple] = []
        self.fail: Exception | None = None
        self.broken: set[str] = set()
        self.flaky: set[str] = set()

    def transport(self, path: str, params: dict) -> dict:
        self.calls.append(("video_by_id", params["id"]))
        if self.fail is not None:
            raise self.fail
        if params["id"] in self.flaky:
            raise pornhub.PornhubError("HTTP Error 503: Service Unavailable", 503)
        v = self.videos.get(params["id"])
        return {"video": v} if v is not None else payload("ph_not_found.json")

    def lister(self, url: str, limit: int) -> list[str]:
        self.calls.append(("list", url, limit))
        ch = url.split("pornhub.com/", 1)[1].rsplit("/videos", 1)[0]
        if ch in self.broken:
            raise pornhub.PornhubError(f"yt-dlp {url}: HTTP Error 404: Not Found")
        return list(self.uploads.get(ch, []))[:limit]

    def count(self, kind: str) -> int:
        return sum(1 for c in self.calls if c[0] == kind)


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = st.open_store(Path(self.tmp.name) / "f.db", create=True)
        self.addCleanup(self.store.close)
        self.ph = FakePH()


class AdapterTest(Case):
    def test_platforms_include_pornhub(self):
        self.assertIn("pornhub", st.PLATFORMS)
        self.assertEqual(st.SCHEMA_VERSION, 10)

    def test_video_by_id_returns_the_video_and_charges_the_hourly_bucket(self):
        got = pornhub.video_by_id(self.store, VK, transport=lambda p, q: payload("ph_video_by_id.json"))
        self.assertEqual(got["video_id"], VK)
        self.assertEqual(quota.cost("ph.video_by_id"), ("pornhub", 1))
        used = {b.bucket: b for b in quota.usage(self.store).buckets}
        self.assertEqual(used["pornhub"].used, 1)
        self.assertEqual(used["pornhub"].window, "hour")
        self.assertEqual(used["pornhub"].limit, 600)

    def test_missing_video_is_a_pornhub_error_with_its_code(self):
        with self.assertRaises(pornhub.PornhubError) as ctx:
            pornhub.video_by_id(self.store, VK, transport=lambda p, q: payload("ph_not_found.json"))
        self.assertEqual(ctx.exception.code, "2002")
        self.assertTrue(pornhub.missing(ctx.exception))

    def test_http_429_pauses_the_bucket(self):
        def refuse(path, params):
            raise pornhub.PornhubError("HTTP 429: too many requests", 429)
        with self.assertRaises(quota.QuotaExceeded):
            pornhub.video_by_id(self.store, VK, transport=refuse)
        self.assertIsNotNone(quota.pressure(self.store, "pornhub").paused_until)
        with self.assertRaises(quota.QuotaExceeded):
            pornhub.video_by_id(self.store, VK, transport=lambda p, q: payload("ph_video_by_id.json"))

    def test_http_403_from_the_api_pauses_the_bucket_like_429(self):
        def refuse(path, params):
            raise pornhub.PornhubError("Pornhub API: HTTP 403", 403)
        with self.assertRaises(pornhub.RateLimited):
            pornhub.video_by_id(self.store, VK, transport=refuse)
        self.assertIsNotNone(quota.pressure(self.store, "pornhub").paused_until)

    def test_listing_429_is_read_from_the_status_only(self):
        from yt_dlp.utils import DownloadError
        cases = [("ERROR: [PornHub] users/abc4290: HTTP Error 404: Not Found", None),
                 ("ERROR: [PornHub] users/abc: HTTP Error 429: Too Many Requests", 429)]
        for text, code in cases:
            with self.subTest(text=text), mock.patch("yt_dlp.YoutubeDL.YoutubeDL.extract_info", side_effect=DownloadError(text)):
                with self.assertRaises(pornhub.PornhubError) as ctx:
                    pornhub.ytdlp_lister("https://www.pornhub.com/users/abc4290/videos", 40)
                self.assertEqual(ctx.exception.code, code)

    def test_a_broken_extractor_is_a_pornhub_error(self):
        with mock.patch("yt_dlp.YoutubeDL.YoutubeDL.extract_info", side_effect=KeyError("entries")):
            with self.assertRaises(pornhub.PornhubError):
                pornhub.ytdlp_lister("https://www.pornhub.com/model/sample-maker/videos", 40)

    def test_quota_limit_override(self):
        with mock.patch.dict(os.environ, {"CF_QUOTA_PORNHUB": "2"}):
            self.assertEqual(quota.limits()["pornhub"], 2)

    def test_list_uploads_charges_pages_and_keeps_order(self):
        self.ph.uploads["model/sample-maker"] = [f"6a00000000{i:03x}" for i in range(90, 0, -1)]
        got = pornhub.list_uploads(self.store, "model/sample-maker", limit=60, lister=self.ph.lister)
        self.assertEqual(len(got), 60)
        self.assertEqual(got[0], "6a0000000005a")
        self.assertEqual(self.ph.calls[0], ("list", "https://www.pornhub.com/model/sample-maker/videos", 60))
        hourly = {m.method: m.calls for m in quota.usage(self.store).hourly_by_method}
        self.assertEqual(hourly["ph.list_page"], 2)

    def test_viewkeys_from_a_flat_yt_dlp_listing(self):
        keys = pornhub.viewkeys(payload("ph_flat_list.json"))
        self.assertEqual(keys, ["6a00000000005", "6a00000000004", "6a00000000003", "6a00000000002",
                                "6a00000000001"])

    def test_channel_exists(self):
        self.ph.uploads["channels/sample-studio"] = ["6a00000000001"]
        self.assertEqual(pornhub.channel_exists(self.store, "channels/sample-studio", lister=self.ph.lister),
                         "sample-studio")
        self.assertIsNone(pornhub.channel_exists(self.store, "model/nobody-here", lister=self.ph.lister))

    def test_no_secret_is_read(self):
        with mock.patch("cf.research.env.value", side_effect=AssertionError("secret read")):
            pornhub.video_by_id(self.store, VK, transport=lambda p, q: payload("ph_video_by_id.json"))


class IngestTest(Case):
    def test_duration(self):
        self.assertEqual(ingest.ph_duration("32:40"), 1960.0)
        self.assertEqual(ingest.ph_duration("1:02:03"), 3723.0)
        self.assertEqual(ingest.ph_duration("0:59"), 59.0)
        for junk in (None, "", "abc", "12", "1:2:3:4", "5:70"):
            self.assertIsNone(ingest.ph_duration(junk), junk)

    def test_row_and_snapshot(self):
        v = payload("ph_video_by_id.json")["video"]
        row = ingest.ph_video_row(v)
        self.assertEqual(row["platform"], "pornhub")
        self.assertEqual(row["external_id"], VK)
        self.assertEqual(row["url"], "https://www.pornhub.com/view_video.php?viewkey=6a1b2c3d4e5f0")
        self.assertEqual(row["published_at"], "2026-09-21T19:00:05Z")
        self.assertEqual(row["duration_s"], 1960.0)
        self.assertEqual(row["kind"], "long")
        self.assertEqual(json.loads(row["tags"]), ["pov", "evening", "old town"])
        raw = json.loads(row["raw"])
        self.assertEqual(raw["categories"], ["amateur", "hd-porn"])
        self.assertEqual(raw["rating"], 89.5618)
        self.assertEqual(raw["ratings"], 52375)
        self.assertEqual(raw["api_publish_date"], "2026-09-21 19:00:05")
        self.assertEqual(len(raw["thumbs"]), 16)
        self.assertEqual(ingest.ph_snapshot_row(v), {"views": 1608000, "likes": 46908, "comments": None})

    def test_channel_and_videos_upsert_with_snapshot(self):
        cid = ingest.ingest_ph_channel(self.store, "model", "Sample-Maker")
        again = ingest.ingest_ph_channel(self.store, "model", "sample-maker", "Sample Maker")
        self.assertEqual(cid, again)
        ch = self.store.one("SELECT * FROM channel WHERE id = ?", (cid,))
        self.assertEqual((ch["platform"], ch["external_id"], ch["handle"], ch["title"]),
                         ("pornhub", "model/sample-maker", "sample-maker", "Sample Maker"))
        v = payload("ph_video_by_id.json")["video"]
        ids = ingest.ingest_ph_videos(self.store, cid, [v], fetched_at="2026-10-01T00:00:00Z",
                                      taken_at="2026-10-01T00:00:00Z")
        v2 = {**v, "views": 1700000, "rating": 90.0, "ratings": 60000}
        self.assertEqual(ingest.ingest_ph_videos(self.store, None, [v2], fetched_at="2026-10-02T00:00:00Z",
                                                 taken_at="2026-10-02T00:00:00Z"), ids)
        row = self.store.one("SELECT channel_id, raw FROM video WHERE id = ?", (ids[0],))
        self.assertEqual(row["channel_id"], cid)
        self.assertEqual(json.loads(row["raw"])["rating"], 90.0)
        snaps = self.store.query("SELECT views, likes, comments FROM snapshot WHERE video_id = ? ORDER BY taken_at",
                                 (ids[0],))
        self.assertEqual(snaps, [{"views": 1608000, "likes": 46908, "comments": None},
                                 {"views": 1700000, "likes": 54000, "comments": None}])


class WatchlistTest(Case):
    def setUp(self):
        super().setUp()
        wl.create(self.store, "ph-walks", format_id="walk-reel")
        self.ph.uploads["model/sample-maker"] = ["6a00000000001"]

    def test_add_channel_by_link(self):
        ch = wl.add_channel(self.store, "ph-walks", "https://www.pornhub.com/model/Sample-Maker/videos",
                            ph_lister=self.ph.lister)
        self.assertEqual((ch.platform, ch.external_id, ch.handle), ("pornhub", "model/sample-maker", "sample-maker"))
        self.assertEqual(wl.get(self.store, "ph-walks").platforms, {"pornhub": 1})
        again = wl.add_channel(self.store, "ph-walks", "ph:model/sample-maker", ph_lister=self.ph.lister)
        self.assertEqual(again.external_id, "model/sample-maker")
        self.assertEqual(self.ph.count("list"), 1)
        self.assertEqual(wl.remove_channel(self.store, "ph-walks", "ph:model/sample-maker").external_id,
                         "model/sample-maker")

    def test_unknown_slug_writes_nothing(self):
        with self.assertRaises(wl.WatchlistError) as ctx:
            wl.add_channel(self.store, "ph-walks", "ph:model/nobody-here", ph_lister=self.ph.lister)
        self.assertNotIn("\n", str(ctx.exception))
        self.assertIn("nobody-here", str(ctx.exception))
        self.assertEqual(self.store.query("SELECT * FROM channel"), [])
        self.assertEqual(self.store.query("SELECT * FROM watchlist_channel"), [])

    def test_video_link_points_to_add_reference(self):
        with self.assertRaises(wl.WatchlistError) as ctx:
            wl.add_channel(self.store, "ph-walks", f"https://www.pornhub.com/view_video.php?viewkey={VK}",
                           ph_lister=self.ph.lister)
        self.assertIn("watchlist add-reference", str(ctx.exception))
        self.assertEqual(self.ph.calls, [])


def keys(n: int, start: int = 1) -> list[str]:
    """``n`` synthetic viewkeys, newest first (the highest number first)."""
    return [f"6a{i:011x}" for i in range(start + n - 1, start - 1, -1)]


class ScoutBase(Case):
    def setUp(self):
        super().setUp()
        env = mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": ""})
        env.start()
        self.addCleanup(env.stop)
        wl.create(self.store, "ph-walks", format_id="walk-reel")
        self.ph.uploads["model/sample-maker"] = keys(100)
        for i, vk in enumerate(keys(100)):
            self.ph.videos[vk] = ph_video(vk, iso(NOW - timedelta(days=4 + i)), 1000 + i)
        wl.add_channel(self.store, "ph-walks", "ph:model/sample-maker", ph_lister=self.ph.lister)
        self.ph.calls.clear()

    def run_scout(self, now=NOW):
        return scout.scout(self.store, "ph-walks", ph_transport=self.ph.transport, ph_lister=self.ph.lister, now=now)


class ScoutTest(ScoutBase):
    def test_first_run_backfills_and_snapshots_each_video(self):
        res = self.run_scout()
        self.assertIsNone(res.stopped)
        self.assertIsNone(res.skipped)
        [ch] = res.channels
        self.assertEqual((ch.platform, ch.mode, ch.new_videos, ch.longs, ch.backfilled),
                         ("pornhub", "backfill", 60, 60, True))
        self.assertEqual(self.ph.count("video_by_id"), 60)
        self.assertEqual(res.calls, {"ph.list_page": 2, "ph.video_by_id": 60})
        n = self.store.one("SELECT COUNT(*) AS n FROM snapshot s JOIN video v ON v.id = s.video_id "
                           "WHERE v.platform = 'pornhub' AND s.comments IS NULL AND s.likes = 80")["n"]
        self.assertEqual(n, 60)
        c = self.store.one("SELECT backfilled_at, uploads_through FROM channel WHERE platform = 'pornhub'")
        self.assertEqual(c["uploads_through"], iso(NOW - timedelta(days=4)))
        self.assertIsNotNone(c["backfilled_at"])

    def test_second_run_reads_only_new_viewkeys(self):
        self.run_scout()
        new = keys(3, start=101)
        for i, vk in enumerate(new):
            self.ph.videos[vk] = ph_video(vk, iso(NOW - timedelta(hours=10 + i)), 5000)
        self.ph.uploads["model/sample-maker"] = new + self.ph.uploads["model/sample-maker"]
        self.ph.calls.clear()
        res = self.run_scout(NOW + timedelta(days=1))
        [ch] = res.channels
        self.assertEqual((ch.mode, ch.new_videos), ("new", 3))
        self.assertEqual([c[1] for c in self.ph.calls if c[0] == "video_by_id"], new[::-1])
        self.assertEqual([c[2] for c in self.ph.calls if c[0] == "list"], [40])
        through = self.store.one("SELECT uploads_through FROM channel WHERE platform = 'pornhub'")["uploads_through"]
        self.assertEqual(through, iso(NOW - timedelta(hours=10)))

    def test_later_run_extends_the_list_while_everything_is_new(self):
        self.run_scout()
        new = keys(50, start=201)
        for vk in new:
            self.ph.videos[vk] = ph_video(vk, iso(NOW), 10)
        self.ph.uploads["model/sample-maker"] = new + self.ph.uploads["model/sample-maker"]
        self.ph.calls.clear()
        res = self.run_scout(NOW + timedelta(days=1))
        self.assertEqual([c[2] for c in self.ph.calls if c[0] == "list"], [40, 80])
        self.assertEqual(res.channels[0].new_videos, 50)

    def test_a_missing_video_is_skipped_and_an_error_ends_only_its_channel(self):
        del self.ph.videos[keys(100)[0]]
        wl.add_channel(self.store, "ph-walks", "ph:channels/sample-studio",
                       ph_lister=lambda url, limit: ["6a00000000fff"])
        self.ph.broken.add("channels/sample-studio")
        self.ph.calls.clear()
        res = self.run_scout()
        by = {c.external_id: c for c in res.channels}
        self.assertEqual(by["model/sample-maker"].new_videos, 59)
        self.assertIsNone(by["model/sample-maker"].error)
        self.assertIn("404", by["channels/sample-studio"].error or "")

    def test_runs_without_a_youtube_key_and_skips_the_youtube_part(self):
        wl.add_query(self.store, "ph-walks", "evening walk")
        res = self.run_scout()
        self.assertIn("YouTube part skipped", res.skipped)
        self.assertEqual(res.channels[0].new_videos, 60)

    def add_new(self, n: int = 50) -> list[str]:
        new = keys(n, start=201)
        for vk in new:
            self.ph.videos[vk] = ph_video(vk, iso(NOW), 10)
        self.ph.uploads["model/sample-maker"] = new + self.ph.uploads["model/sample-maker"]
        self.ph.calls.clear()
        return new

    def known(self, vks: list[str]) -> list[str]:
        have = {r["external_id"] for r in self.store.query("SELECT external_id FROM video WHERE platform = 'pornhub'")}
        return [vk for vk in vks if vk in have]

    def through(self) -> str:
        return self.store.one("SELECT uploads_through FROM channel WHERE platform = 'pornhub'")["uploads_through"]

    def test_a_catch_up_cut_by_the_quota_is_completed_by_the_next_run(self):
        self.run_scout()
        mark = self.through()
        new = self.add_new()
        with mock.patch.dict(os.environ, {"CF_QUOTA_PORNHUB": str(63 + 3 + 20)}):
            res = self.run_scout(NOW + timedelta(days=1))
        self.assertIn("quota", res.stopped)
        self.assertEqual(len(self.known(new)), 20)
        self.assertEqual(self.through(), mark)
        self.ph.calls.clear()
        res = self.run_scout(NOW + timedelta(days=1, hours=2))
        self.assertEqual(self.known(new), new)
        self.assertEqual(res.channels[0].new_videos, 30)
        self.assertEqual(self.ph.count("video_by_id"), 30)
        self.assertEqual(self.through(), iso(NOW))

    def test_a_transient_error_midway_is_completed_by_the_next_run(self):
        self.run_scout()
        new = self.add_new()
        self.ph.flaky.add(new[20])
        res = self.run_scout(NOW + timedelta(days=1))
        self.assertIn("503", res.channels[0].error or "")
        self.ph.flaky.clear()
        self.run_scout(NOW + timedelta(days=1, hours=2))
        self.assertEqual(self.known(new), new)

    def test_fetching_the_newest_upload_first_does_not_end_the_listing(self):
        self.run_scout()
        new = self.add_new()
        picks.add_reference(self.store, "ph-walks", f"ph:{new[0]}", ph_transport=self.ph.transport)
        self.run_scout(NOW + timedelta(days=1))
        self.assertEqual(self.known(new), new)

    def test_a_video_picked_before_its_channel_is_scouted_gets_the_channel(self):
        vk = keys(100)[10]
        picks.add_reference(self.store, "ph-walks", f"ph:{vk}", ph_transport=self.ph.transport)
        self.ph.calls.clear()
        self.run_scout()
        self.assertNotIn(vk, [c[1] for c in self.ph.calls if c[0] == "video_by_id"])
        row = self.store.one("SELECT c.external_id FROM video v JOIN channel c ON c.id = v.channel_id "
                             "WHERE v.external_id = ?", (vk,))
        self.assertEqual(row["external_id"], "model/sample-maker")

    def test_a_first_run_after_a_pick_still_backfills_60(self):
        picks.add_reference(self.store, "ph-walks", f"ph:{keys(100)[10]}", ph_transport=self.ph.transport)
        self.run_scout()
        self.assertEqual(self.known(keys(100)), keys(100)[:60])
        self.assertEqual(self.through(), iso(NOW - timedelta(days=4)))

    def test_a_video_listed_below_a_read_one_but_published_later_is_read(self):
        self.run_scout()
        first, late = keys(2, start=301)
        self.ph.videos[first] = ph_video(first, iso(NOW - timedelta(hours=1)), 10)
        self.ph.uploads["model/sample-maker"] = [first] + self.ph.uploads["model/sample-maker"]
        self.run_scout()
        self.ph.videos[late] = ph_video(late, iso(NOW + timedelta(hours=12)), 10)
        self.ph.uploads["model/sample-maker"].insert(1, late)
        self.run_scout(NOW + timedelta(days=1))
        self.assertEqual(self.known([late]), [late])

    def test_more_than_the_listing_cap_reads_the_newest_200(self):
        self.run_scout()
        new = keys(250, start=201)
        for i, vk in enumerate(new):
            self.ph.videos[vk] = ph_video(vk, iso(NOW + timedelta(hours=250 - i)), 10)
        self.ph.uploads["model/sample-maker"] = new + self.ph.uploads["model/sample-maker"]
        self.run_scout(NOW + timedelta(days=12))
        self.assertEqual(self.known(new), new[:200])
        self.assertEqual(self.through(), iso(NOW + timedelta(hours=250)))

    def test_a_rate_limit_refusal_counts_its_charged_call(self):
        self.run_scout()
        self.add_new(3)

        def refuse(path, params):
            raise pornhub.PornhubError("HTTP Error 429: Too Many Requests", 429)
        res = scout.scout(self.store, "ph-walks", ph_transport=refuse, ph_lister=self.ph.lister,
                          now=NOW + timedelta(days=1))
        self.assertIn("rate limit", res.stopped)
        self.assertEqual(res.calls, {"ph.list_page": 1, "ph.video_by_id": 1})

    def test_a_403_midway_stops_the_run_and_the_next_one_completes_it(self):
        self.ph.uploads["channels/sample-studio"] = keys(5, start=401)
        for vk in keys(5, start=401):
            self.ph.videos[vk] = ph_video(vk, iso(NOW - timedelta(days=5)), 100)
        wl.add_channel(self.store, "ph-walks", "ph:channels/sample-studio", ph_lister=self.ph.lister)
        self.ph.calls.clear()
        self.ph.fail = pornhub.PornhubError("Pornhub API: HTTP 403", 403)
        res = self.run_scout()
        self.assertIn("rate limit", res.stopped)
        self.assertEqual(self.ph.count("video_by_id"), 1)
        self.ph.fail = None
        self.store.conn.execute("DELETE FROM rate_pressure WHERE bucket = 'pornhub'")
        self.store.conn.commit()
        self.run_scout(NOW + timedelta(hours=2))
        self.assertEqual(len(self.known(keys(100))), 60)
        self.assertEqual(self.known(keys(5, start=401)), keys(5, start=401))

    def test_quota_stop_keeps_what_was_read(self):
        with mock.patch.dict(os.environ, {"CF_QUOTA_PORNHUB": "13"}):
            res = self.run_scout()
        self.assertIn("quota", res.stopped)
        self.assertEqual(res.channels[0].new_videos, 10)
        self.assertIsNone(self.store.one("SELECT backfilled_at FROM channel WHERE platform = 'pornhub'")
                          ["backfilled_at"])



class SnapshotTest(ScoutBase):
    def test_rereads_recent_references_picks_and_own_videos(self):
        self.run_scout()
        self.store.conn.execute("INSERT INTO watchlist_pick (watchlist_id, video_id, added_at) SELECT w.id, v.id, ? "
                                "FROM watchlist w, video v WHERE w.name = 'ph-walks' AND v.external_id = ?",
                                (iso(NOW), keys(100)[59]))
        self.store.conn.commit()
        del self.ph.videos[keys(100)[0]]
        self.ph.calls.clear()
        later = NOW + timedelta(days=1)
        res = scout.snapshot(self.store, "ph-walks", ph_transport=self.ph.transport, now=later)
        read = [c[1] for c in self.ph.calls]
        self.assertEqual(sorted(read), sorted(keys(100)[:26] + [keys(100)[59]]))
        self.assertEqual(res.missing, [keys(100)[0]])
        self.assertEqual(res.videos, len(read) - 1)
        self.assertEqual(res.calls, {"ph.video_by_id": len(read)})
        self.assertIsNone(res.skipped)

    def test_a_short_quota_reads_what_fits_and_stops(self):
        self.run_scout()
        with mock.patch.dict(os.environ, {"CF_QUOTA_PORNHUB": str(63 + 5)}):
            res = scout.snapshot(self.store, "ph-walks", ph_transport=self.ph.transport, now=NOW + timedelta(hours=2))
        self.assertIn("quota", res.stopped)
        self.assertEqual(res.calls, {"ph.video_by_id": 5})

    def test_videos_the_scout_read_this_hour_are_not_reread(self):
        self.run_scout()
        self.ph.calls.clear()
        res = scout.snapshot(self.store, "ph-walks", ph_transport=self.ph.transport, now=NOW + timedelta(minutes=30))
        self.assertEqual(self.ph.count("video_by_id"), 0)
        self.assertEqual(res.videos, 26)
        self.assertEqual(res.calls, {})

    def test_own_videos_are_reread_whatever_their_age(self):
        self.run_scout()
        self.store.conn.execute("UPDATE video SET own = 1 WHERE external_id = ?", (keys(100)[55],))
        self.store.conn.commit()
        self.ph.calls.clear()
        scout.snapshot(self.store, "ph-walks", ph_transport=self.ph.transport, now=NOW + timedelta(days=1))
        self.assertIn(keys(100)[55], [c[1] for c in self.ph.calls])



class PicksTest(ScoutBase):
    def test_pick_of_a_scouted_video_keeps_its_owner(self):
        self.run_scout()
        vk = keys(100)[3]
        self.ph.videos[vk] = {**self.ph.videos[vk], "views": 99999}
        got = picks.add_reference(self.store, "ph-walks", f"https://www.pornhub.com/view_video.php?viewkey={vk}&t=3",
                                  note="nice framing", ph_transport=self.ph.transport)
        self.assertEqual((got.shortcode, got.status, got.owner), (vk, "store", "sample-maker"))
        self.assertEqual(got.url, f"https://www.pornhub.com/view_video.php?viewkey={vk}")
        self.assertIsNotNone(got.note)
        views = self.store.one("SELECT s.views FROM snapshot s WHERE s.video_id = ? ORDER BY taken_at DESC LIMIT 1",
                               (got.video,))["views"]
        self.assertEqual(views, 99999)
        self.assertEqual([p["external_id"] for p in picks.picks(self.store, "ph-walks")], [vk])

    def test_pick_of_an_unknown_video_has_no_owner(self):
        self.ph.videos[VK] = payload("ph_video_by_id.json")["video"]
        got = picks.add_reference(self.store, "ph-walks", f"ph:{VK}", ph_transport=self.ph.transport)
        self.assertEqual((got.status, got.owner), ("unresolved", None))
        self.assertIn("scout", got.detail)
        row = self.store.one("SELECT channel_id, platform, title FROM video WHERE id = ?", (got.video,))
        self.assertEqual((row["channel_id"], row["platform"]), (None, "pornhub"))

    def test_pick_of_a_missing_video_is_refused(self):
        with self.assertRaises(wl.WatchlistError) as ctx:
            picks.add_reference(self.store, "ph-walks", f"ph:{VK}", ph_transport=self.ph.transport)
        self.assertIn(VK, str(ctx.exception))
        self.assertEqual(self.store.query("SELECT * FROM watchlist_pick"), [])




class FeedTest(ScoutBase):
    def test_pornhub_rows_carry_platform_rating_and_an_outlier_score(self):
        hit = keys(100)[0]
        self.ph.videos[hit] = {**self.ph.videos[hit], "views": 10_000, "rating": 91.5}
        self.run_scout()
        rows = feed.feed(self.store, "ph-walks", lookback_days=20, platform="pornhub", now=NOW)
        self.assertEqual(rows[0].external_id, hit)
        self.assertEqual((rows[0].platform, rows[0].rating), ("pornhub", 91.5))
        self.assertAlmostEqual(rows[0].outlier, 10_000 / 1015.5)
        self.assertEqual(rows[0].to_dict()["rating"], 91.5)
        line = feed.report_line(1, rows[0])
        self.assertIn("Pornhub", line)
        self.assertIn("sample-maker", line)
        self.assertEqual(feed.feed(self.store, "ph-walks", platform="youtube", now=NOW), [])


class FakeImages:
    """Image downloader stand-in: a small solid JPEG per URL, every URL recorded."""

    def __init__(self):
        self.urls: list[str] = []

    def __call__(self, url: str) -> bytes:
        self.urls.append(url)
        shade = (len(self.urls) * 13) % 255
        ok, buf = cv2.imencode(".jpg", np.full((240, 320, 3), shade, np.uint8))
        return buf.tobytes()


class FetchTest(Case):
    def setUp(self):
        super().setUp()
        self.root = Path(self.tmp.name) / "shared"
        self.root.mkdir()
        self.ph.videos[VK] = payload("ph_video_by_id.json")["video"]
        self.images = FakeImages()

    def run_fetch(self, **kw):
        return fetch.fetch_pornhub(self.store, VK, root=self.root, transport=self.ph.transport,
                                   downloader=self.images, **kw)

    def test_writes_info_thumb_frames_and_a_measured_card_without_video(self):
        got = self.run_fetch()
        d = self.root / "references" / "_adhoc" / VK
        self.assertEqual(got["dir"], str(d))
        self.assertEqual(json.loads((d / "info.json").read_text())["video_id"], VK)
        self.assertTrue((d / "thumb.jpg").is_file())
        self.assertEqual(sorted(p.name for p in (d / "frames").iterdir()), [f"{i:02d}.jpg" for i in range(1, 17)])
        self.assertEqual(cv2.imread(str(d / "frames.jpg")).shape, (960, 1280, 3))
        self.assertEqual(len(self.images.urls), 17)
        self.assertTrue(all(u.startswith("https://ei.example.test/") for u in self.images.urls))
        self.assertEqual(sorted(p.name for p in d.iterdir()), ["card.json", "frames", "frames.jpg", "info.json",
                                                              "thumb.jpg"])
        m = got["card"]["measured"]
        self.assertEqual((m["platform"], m["duration_s"], m["kind"]), ("pornhub", 1960.0, "long"))
        pk = m["packaging"]
        self.assertEqual(pk["title"], "POV: A Quiet Evening Walk Through The Old Town (4K) 2")
        self.assertEqual((pk["title_chars"], pk["title_words"]), (53, 11))
        self.assertEqual((pk["digits"], pk["brackets"], pk["pov"], pk["emoji"]), (2, True, True, 0))
        self.assertEqual(pk["caps_share"], 0.32)
        self.assertEqual((pk["tags"], pk["categories"], pk["pornstars"], pk["segment"]),
                         (["pov", "evening", "old town"], ["amateur", "hd-porn"], [], "straight"))
        self.assertEqual((pk["thumb"], pk["frames"]), ("thumb.jpg", "frames.jpg"))
        pub = m["published"]
        self.assertEqual((pub["at"], pub["weekday"], pub["hour_utc"]), ("2026-09-21T19:00:05Z", "Mon", 19))
        self.assertEqual(m["counts"]["views"], 1608000)
        self.assertEqual((m["counts"]["likes"], m["counts"]["votes"], m["counts"]["rating"]), (46908, 52375, 89.5618))
        self.assertIn("no video", m["notes"]["media"])
        self.assertIsNone(m["spoken_hook"])
        row = self.store.one("SELECT has_media, has_transcript FROM video WHERE external_id = ?", (VK,))
        self.assertEqual((row["has_media"], row["has_transcript"]), (0, 0))

    def test_local_hour_follows_the_given_zone(self):
        from zoneinfo import ZoneInfo
        m = self.run_fetch(tz=ZoneInfo("Europe/Lisbon"))["card"]["measured"]
        self.assertEqual((m["published"]["hour_local"], m["published"]["weekday_local"]), (20, "Mon"))

    def test_a_second_fetch_keeps_the_images_and_refreshes_the_counts(self):
        self.run_fetch()
        self.ph.videos[VK] = {**self.ph.videos[VK], "views": 1700000}
        got = self.run_fetch()
        self.assertEqual(len(self.images.urls), 17)
        self.assertEqual(got["card"]["measured"]["counts"]["views"], 1700000)
        self.run_fetch(force=True)
        self.assertEqual(len(self.images.urls), 34)

    def test_a_missing_video_is_a_fetch_error(self):
        del self.ph.videos[VK]
        with self.assertRaises(fetch.FetchError):
            self.run_fetch()

    def test_without_the_share_the_mount_hint_comes_first(self):
        with mock.patch.dict(os.environ, {"CF_SHARED_ROOT": str(Path(self.tmp.name) / "not-mounted")}):
            with self.assertRaises(st.StoreError) as ctx:
                fetch.fetch_pornhub(self.store, VK, transport=self.ph.transport, downloader=self.images)
        self.assertIn("not-mounted", str(ctx.exception))
        self.assertEqual(self.ph.calls, [])

    def test_fetch_routes_pornhub_refs(self):
        for ref in (f"https://www.pornhub.com/view_video.php?viewkey={VK}", f"ph:{VK}", VK):
            with mock.patch.object(fetch, "fetch_pornhub", return_value={"ok": ref}) as fp:
                self.assertEqual(fetch.fetch(self.store, ref, root=self.root), {"ok": ref})
            self.assertEqual(fp.call_args.args[1], VK)

    def test_an_all_digit_viewkey_resolves_as_a_viewkey(self):
        digits = "1234567890123"
        self.ph.videos[digits] = {**self.ph.videos[VK], "video_id": digits}
        got = fetch.fetch_pornhub(self.store, digits, root=self.root, transport=self.ph.transport,
                                  downloader=self.images)
        self.assertEqual(card.video(self.store, digits)["id"], got["video"])
        self.assertEqual(card.video(self.store, str(got["video"]))["id"], got["video"])

    def test_card_analysis_with_a_null_spoken_hook_saves(self):
        got = self.run_fetch()
        a = analysis(hook__spoken_hook=None)
        saved = card.save_analysis(self.store, f"https://www.pornhub.com/view_video.php?viewkey={VK}", a,
                                   root=self.root)
        self.assertIsNone(saved["analysis"]["hook"]["spoken_hook"])
        self.assertEqual(card.video(self.store, f"ph:{VK}")["id"], got["video"])
        self.assertEqual(card.video(self.store, VK)["id"], got["video"])
        on_disk = json.loads((Path(got["dir"]) / "card.json").read_text())
        self.assertEqual(on_disk["schema"], "cf-reference-card/1")



class TraitsTest(Case):
    def setUp(self):
        super().setUp()
        wl.create(self.store, "ph-walks", format_id="walk-reel")
        cid = ingest.ingest_ph_channel(self.store, "model", "sample-maker")
        self.store.conn.execute("INSERT INTO watchlist_channel (watchlist_id, channel_id, added_at) "
                                "SELECT id, ?, ? FROM watchlist WHERE name = 'ph-walks'", (cid, iso(NOW)))
        self.store.conn.commit()
        hits = [ph_video("6a000000000a1", "2026-10-05T19:00:00Z", 5000, duration="25:00", rating=95.0,
                         title="POV night walk 2", tags=("pov", "night"), categories=("amateur",)),
                ph_video("6a000000000a2", "2026-09-28T19:00:00Z", 5000, duration="22:00", rating=95.0,
                         title="POV night walk 3", tags=("pov", "night"), categories=("amateur",))]
        days = ["2026-10-07", "2026-09-30", "2026-09-23", "2026-09-16", "2026-09-09", "2026-09-02", "2026-08-26",
                "2026-08-19"]
        base = [ph_video(f"6a000000000b{i}", f"{d}T10:00:00Z", 1000, duration="8:00" if i < 4 else "15:00",
                         title="day walk", tags=("day", "pov") if i < 2 else ("day",),
                         categories=("amateur",) if i < 4 else ()) for i, d in enumerate(days)]
        ingest.ingest_ph_videos(self.store, cid, hits + base, taken_at=iso(NOW))

    def report(self, **kw):
        from zoneinfo import ZoneInfo
        return traits.traits(self.store, "ph-walks", platform="pornhub", tz=ZoneInfo("Europe/Lisbon"), now=NOW, **kw)

    def test_compares_outliers_with_all_scored_references(self):
        r = self.report()
        self.assertEqual((r.references, r.outliers), (10, 2))
        dur = {b.key: (b.all, b.outliers, b.share_all, b.share_outliers, b.lift) for b in r.duration}
        self.assertEqual(dur, {"<5": (0, 0, 0.0, 0.0, None), "5-10": (4, 0, 0.4, 0.0, 0.0),
                               "10-20": (4, 0, 0.4, 0.0, 0.0), "20+": (2, 2, 0.2, 1.0, 5.0)})
        self.assertEqual([(t.key, t.all, t.outliers, t.lift) for t in r.tags], [("pov", 4, 2, 2.5), ("day", 8, 0, 0.0)])
        self.assertEqual([(t.key, t.all, t.outliers, t.lift) for t in r.categories], [("amateur", 6, 2, 1.667)])
        title = {t.key: (t.all, t.outliers) for t in r.title}
        self.assertEqual((title["pov"], title["digits"], title["brackets"]), ((2, 2), (2, 2), (0, 0)))
        self.assertEqual({w.key: (w.all, w.outliers) for w in r.weekday_utc}, {"Mon": (2, 2), "Wed": (8, 0)})
        self.assertEqual({h.key: (h.all, h.outliers) for h in r.hour_utc}, {"19": (2, 2), "10": (8, 0)})
        self.assertEqual({h.key: (h.all, h.outliers) for h in r.hour_local}, {"20": (2, 2), "11": (8, 0)})
        self.assertEqual(r.rating, {"all": 80.0, "outliers": 95.0})
        self.assertEqual(r.title_length, {"chars": {"all": 8.0, "outliers": 16.0}, "words": {"all": 2.0, "outliers": 4.0}})

    def test_is_deterministic_and_serialisable(self):
        self.assertEqual(json.dumps(self.report().to_dict()), json.dumps(self.report().to_dict()))

    def test_threshold_and_window(self):
        self.assertEqual(self.report(min_outlier=6.0).outliers, 0)
        self.assertEqual(self.report(days=10).references, 2)


    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", str(Path(self.tmp.name) / "f.db")])
        return code, out.getvalue(), err.getvalue()

    def test_cli_traits_and_feed(self):
        self.store.close()
        code, out, err = self.run_cli("traits", "ph-walks", "--platform", "pornhub", "--days", "120", "--json")
        self.assertEqual(code, 0, err)
        got = json.loads(out)
        self.assertEqual((got["references"], got["outliers"]), (10, 2))
        code, out, err = self.run_cli("traits", "ph-walks", "--min-outlier", "3")
        self.assertEqual(code, 0, err)
        self.assertIn("pov", out)
        self.assertIn("20+", out)
        code, out, err = self.run_cli("feed", "ph-walks", "--platform", "pornhub", "--days", "120")
        self.assertEqual(code, 0, err)
        self.assertIn("Pornhub", out)
        self.assertIn("рейтинг 95", out)

    def test_cli_reports_a_pornhub_error_in_one_line(self):
        self.store.close()
        with mock.patch.object(pornhub, "video_by_id", side_effect=pornhub.PornhubError("Pornhub API: HTTP 503", 503)):
            code, out, err = self.run_cli("watchlist", "add-reference", "ph-walks", f"ph:{VK}")
        self.assertEqual(code, 1)
        self.assertEqual(err.strip().count("\n"), 0)
        self.assertIn("HTTP 503", err)


if __name__ == "__main__":
    unittest.main()
