"""Instagram as a second research source (ADR 0007): the V6 migration, ingest from recorded Graph API
payloads, channel refs, scout and snapshot over a fake Graph transport, the Outlier score per Platform,
the hourly quota planner, the token, the own account and the Author's picks. No network."""

import json
import os
import re
import sqlite3
import stat
import tempfile
import unittest
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from research_synth import NOW, add_member, add_videos, ago, iso, video_item

from cf.research import env, feed, fetch, ingest, instagram, notes, outlier, own, picks, quota, scout
from cf.research import store as st
from cf.research import watchlist as wl
from cf.research.fetch import FetchError

FIX = Path(__file__).parent / "fixtures" / "research"
UID = "17841400000000099"
IG_ENV = {"INSTAGRAM_USER_ID": UID}


def payload(name: str) -> dict:
    return json.loads((FIX / name).read_text())


def reel(code: str, when: str, views: int | None, likes: int = 10, caption: str | None = None,
         product: str = "REELS") -> dict:
    item = {"id": f"18{zlib.crc32(code.encode()):015d}", "media_product_type": product, "media_type": "VIDEO",
            "like_count": likes, "comments_count": 1, "timestamp": when.replace("Z", "+0000"),
            "permalink": f"https://www.instagram.com/{'reel' if product == 'REELS' else 'p'}/{code}/",
            "caption": caption if caption is not None else f"reel {code}\nmore"}
    if views is not None:
        item["view_count"] = views
    return item


class FakeGraph:
    """A Graph API stand-in. ``accounts[username]`` is ``{"id", "followers_count", "media": [newest first]}``;
    a missing username is a personal account. ``own_pages`` are own media pages; ``fail_nested`` makes
    the nested-insights page fail once per page; ``insights[media_id]`` answers ``/insights``."""

    def __init__(self):
        self.accounts: dict[str, dict] = {}
        self.own_account: dict | None = None
        self.own_pages: list[dict] = []
        self.fail_nested = False
        self.insights: dict[str, dict] = {}
        self.calls: list[tuple[str, dict]] = []

    def __call__(self, path: str, params: dict) -> dict:
        self.calls.append((path, dict(params)))
        f = params.get("fields") or ""
        m = re.search(r"business_discovery\.username\(([^)]+)\)", f)
        if m:
            acct = self.accounts.get(m.group(1))
            if acct is None:
                raise instagram.InstagramError("Invalid user id", 110, 2207013)
            bd = {k: v for k, v in acct.items() if k != "media"} | {"username": m.group(1)}
            mm = re.search(r"media(?:\.after\(([^)]+)\))?\.limit\((\d+)\)", f)
            if mm:
                start, size = int(mm.group(1) or 0), int(mm.group(2))
                items = acct.get("media", [])
                bd["media"] = {"data": items[start:start + size],
                               "paging": {"cursors": {"after": str(start + size)}}}
            return {"business_discovery": bd, "id": UID}
        if path.endswith("/insights"):
            return self.insights[path.split("/")[0]]
        if path.endswith("/media"):
            if self.fail_nested and "insights" in f:
                raise instagram.InstagramError("Invalid metric", 100)
            i = int(params.get("after") or 0)
            page = json.loads(json.dumps(self.own_pages[i]))
            if "insights" not in f:
                for item in page["data"]:
                    item.pop("insights", None)
            if i + 1 < len(self.own_pages):
                page["paging"] = {"cursors": {"after": str(i + 1)}, "next": "https://graph.facebook.com/next"}
            return page
        if path == UID:
            return self.own_account
        raise AssertionError(f"unexpected call {path} {params}")

    def methods(self) -> list[str]:
        return [p for p, _ in self.calls]


class Case(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = st.open_store(Path(self.tmp.name) / "f.db")
        self.addCleanup(self.store.close)
        patcher = mock.patch.dict(os.environ, IG_ENV)
        patcher.start()
        self.addCleanup(patcher.stop)
        wl.create(self.store, "me-walks", format_id="walk-reel", author_channel="kwi_asya")
        self.g = FakeGraph()

    def account(self, name: str, media: list[dict], followers: int = 1000, aid: str | None = None) -> None:
        self.g.accounts[name] = {"id": aid or f"1784{zlib.crc32(name.encode()):011d}", "name": name.title(),
                                 "followers_count": followers, "media_count": len(media), "media": media}

    def add_ig(self, name: str) -> wl.ReferenceChannel:
        return wl.add_channel(self.store, "me-walks", f"ig:{name}", ig_transport=self.g)


# --- the migration ---------------------------------------------------------------------

class MigrationV6Test(unittest.TestCase):
    def test_a_v5_store_gets_the_instagram_tables_and_its_rows_stay_youtube(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "v5.db"
            conn = sqlite3.connect(path)
            for v, script in enumerate(st.MIGRATIONS[:5]):
                conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
            conn.execute("INSERT INTO channel (external_id, handle) VALUES ('UCaaaaaaaaaaaaaaaaaaaaaa', '@alpha')")
            conn.execute("INSERT INTO video (external_id, channel_id, kind) VALUES ('dQw4w9WgXcQ', 1, 'short')")
            conn.commit()
            conn.close()
            with st.open_store(path, seed=False) as s:
                self.assertEqual(s.schema_version(), 6)
                self.assertEqual(s.one("SELECT platform FROM channel")["platform"], "youtube")
                self.assertEqual(s.one("SELECT platform, marks FROM video"), {"platform": "youtube", "marks": "[]"})
                self.assertLessEqual({"insight", "watchlist_pick", "rate", "rate_pressure"}, set(s.tables()))


# --- ingest -------------------------------------------------------------------------------

class IngestTest(Case):
    def test_business_discovery_payload_becomes_an_account_and_its_reels(self):
        bd = payload("ig_business_discovery_p1.json")["business_discovery"]
        cid = ingest.ingest_ig_account(self.store, bd)
        ids = ingest.ingest_ig_media(self.store, cid, bd["media"]["data"], taken_at="2026-10-11T12:00:00Z")
        self.assertEqual(len(ids), 2)  # the carousel is not a reel
        ch = self.store.one("SELECT platform, external_id, handle, subscriber_count, video_count FROM channel")
        self.assertEqual(ch, {"platform": "instagram", "external_id": "17841400000000001", "handle": "@berlinstrolls",
                              "subscriber_count": 48210, "video_count": 312})
        r = feed.reference(self.store, "DeBerlin003")
        self.assertEqual((r.platform, r.kind, r.title, r.url, r.views, r.likes, r.comments, r.published_at),
                         ("instagram", "short", "When he says 'just one more street' 😂",
                          "https://www.instagram.com/reel/DeBerlin003/", 210400, 4120, 88, "2026-10-10T16:15:44Z"))
        quiet = feed.reference(self.store, "DeBerlin001")
        self.assertEqual((quiet.title, quiet.views, quiet.likes), ("Morning at the Spree", None, 310))
        self.assertEqual(json.loads(self.store.one("SELECT tags FROM video WHERE external_id = 'DeBerlin003'")["tags"]),
                         ["berlin", "walk"])
        self.assertIsNone(feed.reference(self.store, "DeBerlin002"))

    def test_links_give_their_shortcode_without_tracking_parameters(self):
        for url, code in (("https://www.instagram.com/reel/DdZbBzwu4bO/?igsh=MWx0&stkn=1", "DdZbBzwu4bO"),
                          ("instagram.com/p/DcOXXfGEYSZ/?img_index=5", "DcOXXfGEYSZ"),
                          ("https://www.instagram.com/someone/reel/DeUex6UKm5s/", "DeUex6UKm5s"),
                          ("https://www.instagram.com/lyuba_bich", None), ("https://youtu.be/dQw4w9WgXcQ", None)):
            self.assertEqual(ingest.instagram_shortcode(url), code, url)

    def test_insight_values_read_nested_and_edge_payloads(self):
        item = payload("ig_own_media.json")["data"][0]
        self.assertEqual(ingest.insight_values(item)["ig_reels_avg_watch_time"], 6329)
        self.assertEqual(ingest.insight_values({"data": item["insights"]["data"]})["shares"], 63)


# --- channel refs ---------------------------------------------------------------------------

class ChannelRefTest(Case):
    def test_instagram_accounts_parse_from_prefix_and_links(self):
        for text in ("ig:Lyuba_Bich", "instagram:lyuba_bich", "https://www.instagram.com/lyuba_bich?igsh=x",
                     "instagram.com/lyuba_bich/reels/"):
            self.assertEqual(wl.parse_channel_ref(text), wl.ChannelRef("handle", "@lyuba_bich", "instagram"), text)
        self.assertEqual(wl.parse_channel_ref("@slowwalks").platform, "youtube")
        with self.assertRaisesRegex(wl.WatchlistError, "add-reference"):
            wl.parse_channel_ref("https://www.instagram.com/reel/DdZbBzwu4bO/")

    def test_add_channel_resolves_through_business_discovery_once(self):
        self.account("berlinstrolls", [], followers=48210)
        c = self.add_ig("berlinstrolls")
        self.assertEqual((c.platform, c.handle, c.subscriber_count), ("instagram", "@berlinstrolls", 48210))
        self.add_ig("berlinstrolls")
        self.assertEqual(len(self.g.calls), 1)  # the second add reuses the stored account
        self.assertNotIn("media.limit", self.g.calls[0][1]["fields"])  # no media yet: scout reads those
        self.assertEqual([x.handle for x in wl.channels(self.store, "me-walks")], ["@berlinstrolls"])
        self.assertEqual(quota.usage(self.store).hourly_by_method[0].method, "ig.business_discovery")

    def test_a_personal_account_is_reported_not_crashed(self):
        with self.assertRaisesRegex(wl.WatchlistError, "personal or private"):
            self.add_ig("someprivategirl")


# --- scout and snapshot ---------------------------------------------------------------------

class ScoutTest(Case):
    def seed(self, n: int = 60):
        media = [reel(f"Code{i:04d}x", ago(days=i), 1000 + i, caption=f"Reel number {i}\nline 2") for i in range(n)]
        media.insert(3, reel("PostOnly01", ago(days=3), None, product="FEED"))
        self.account("berlinstrolls", media)
        self.add_ig("berlinstrolls")
        return media

    def test_first_scout_backfills_reels_then_reads_only_new_ones(self):
        self.seed()
        with mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": ""}):
            r = scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        c = r.channels[0]
        self.assertEqual((c.platform, c.mode, c.pages, c.new_videos, c.shorts, c.backfilled), ("instagram", "backfill",
                                                                                              2, 60, 60, True))
        self.assertIsNone(r.skipped)
        self.assertEqual(r.calls, {"ig.business_discovery": 2})
        self.g.accounts["berlinstrolls"]["media"].insert(0, reel("FreshReel1", ago(hours=2), 9000))
        r = scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        self.assertEqual((r.channels[0].mode, r.channels[0].pages, r.channels[0].new_videos), ("new", 1, 1))

    def test_feed_shows_instagram_rows_with_platform_permalink_and_caption_line(self):
        self.seed(10)
        scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        rows = feed.feed(self.store, "me-walks", now=NOW, platform="instagram")
        top = [r for r in rows if r.external_id == "Code0005x"][0]
        self.assertEqual((top.platform, top.url, top.title, top.handle),
                         ("instagram", "https://www.instagram.com/reel/Code0005x/", "Reel number 5", "@berlinstrolls"))
        self.assertIn("Instagram", feed.report_line(1, top))
        self.assertEqual(feed.feed(self.store, "me-walks", now=NOW, platform="youtube"), [])

    def test_snapshot_rereads_recent_pages_within_the_hourly_bucket(self):
        self.seed(10)
        scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        self.g.accounts["berlinstrolls"]["media"][0]["view_count"] = 5555
        later = NOW + timedelta(hours=1)
        r = scout.snapshot(self.store, "me-walks", ig_transport=self.g, now=later)
        self.assertEqual((r.videos, r.calls, r.errors), (10, {"ig.business_discovery": 1}, []))
        hist = scout.snapshot_history(self.store, "Code0000x", "instagram")
        self.assertEqual([h.views for h in hist], [1000, 5555])

    def test_a_watchlist_with_youtube_channels_but_no_key_still_scouts_instagram(self):
        self.seed(5)
        add_member(self.store, "me-walks", "UCaaaaaaaaaaaaaaaaaaaaaa", "@alpha")
        with mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": ""}):
            r = scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        self.assertIn("YOUTUBE_API_KEY", r.skipped)
        self.assertEqual([c.platform for c in r.channels], ["instagram"])

    def test_a_renamed_account_is_an_error_of_its_channel_only(self):
        self.seed(5)
        del self.g.accounts["berlinstrolls"]
        r = scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        self.assertIn("Invalid user id", r.channels[0].error)
        self.assertTrue(r.failed())

    def test_the_token_warning_shows_under_seven_days(self):
        self.seed(5)
        soon = {"data": {"is_valid": True, "type": "USER", "expires_at": int((NOW + timedelta(days=3)).timestamp())}}
        with mock.patch.dict(os.environ, {"INSTAGRAM_ACCESS_TOKEN": "t"}):
            r = scout.scout(self.store, "me-walks", ig_transport=self.g, token_transport=lambda p, q: soon, now=NOW)
        self.assertEqual(r.token["days_left"], 3)
        self.assertIn("token-refresh", r.token_warning)


# --- Outlier score per Platform ---------------------------------------------------------------

class OutlierTest(Case):
    def test_instagram_reels_score_against_their_own_account_and_fall_back_to_likes(self):
        media = [reel(f"Base{i:05d}", ago(days=10 + i), 1000, likes=100) for i in range(6)]
        media = [reel("BigReel01", ago(days=4), 5000, likes=50), reel("NoViews01", ago(days=5), None, likes=400)] + media
        self.account("berlinstrolls", media)
        self.add_ig("berlinstrolls")
        scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        add_member(self.store, "me-walks", "UCaaaaaaaaaaaaaaaaaaaaaa", "@alpha")
        add_videos(self.store, [video_item(f"yt{i:09d}", "UCaaaaaaaaaaaaaaaaaaaaaa", ago(days=10 + i), 40, 10)
                                for i in range(6)] + [video_item("ytBig000001", "UCaaaaaaaaaaaaaaaaaaaaaa",
                                                                 ago(days=4), 40, 30)])
        rows = {r.external_id: r for r in feed.feed(self.store, "me-walks", now=NOW, limit=None)}
        self.assertAlmostEqual(rows["BigReel01"].outlier, 5.0)  # vs 1 000 median views of its account
        self.assertEqual(rows["BigReel01"].outlier_basis, "views")
        self.assertAlmostEqual(rows["NoViews01"].outlier, 4.0)  # 400 likes vs a 100-like median
        self.assertEqual(rows["NoViews01"].outlier_basis, "likes")
        self.assertIn("по лайкам", feed.report_line(1, rows["NoViews01"]))
        self.assertAlmostEqual(rows["ytBig000001"].outlier, 3.0)  # YouTube against YouTube only
        self.assertAlmostEqual(outlier.score(self.store, "BigReel01", platform="instagram", now=NOW), 5.0)

    def test_youtube_keeps_no_score_without_views(self):
        add_member(self.store, "me-walks", "UCaaaaaaaaaaaaaaaaaaaaaa", "@alpha")
        add_videos(self.store, [video_item(f"yt{i:09d}", "UCaaaaaaaaaaaaaaaaaaaaaa", ago(days=10 + i), 40, 10)
                                for i in range(6)] + [video_item("ytHidden001", "UCaaaaaaaaaaaaaaaaaaaaaa",
                                                                 ago(days=4), 40, None)])
        self.assertIsNone(outlier.score(self.store, "ytHidden001", now=NOW))


# --- the hourly quota planner -------------------------------------------------------------------

class HourlyQuotaTest(Case):
    T = datetime(2026, 10, 12, 14, 30, tzinfo=timezone.utc)

    def test_the_bucket_counts_a_rolling_hour_and_refuses_before_calling(self):
        for _ in range(100):
            quota.charge(self.store, "ig.business_discovery", now=self.T)
        with self.assertRaisesRegex(quota.QuotaExceeded, "last 60 minutes"):
            quota.charge(self.store, "ig.media", now=self.T + timedelta(minutes=59))
        with self.assertRaises(quota.QuotaExceeded):
            quota.check(self.store, {"ig.business_discovery": 1}, now=self.T)
        quota.charge(self.store, "ig.media", now=self.T + timedelta(minutes=60))  # the first calls left the window
        u = quota.usage(self.store, now=self.T + timedelta(minutes=60))
        ig = [b for b in u.buckets if b.bucket == "instagram"][0]
        self.assertEqual((ig.window, ig.used, ig.remaining), ("hour", 1, 99))
        self.assertEqual({b.bucket: b.used for b in u.buckets if b.window == "day"}, {"default": 0, "search": 0})

    def test_a_plan_mixes_daily_and_hourly_buckets(self):
        with mock.patch.dict(os.environ, {"CF_QUOTA_INSTAGRAM": "3"}):
            quota.check(self.store, {"videos.list": 2, "ig.business_discovery": 3}, now=self.T)
            with self.assertRaisesRegex(quota.QuotaExceeded, "4 calls of the instagram bucket"):
                quota.check(self.store, {"videos.list": 2, "ig.business_discovery": 4}, now=self.T)

    def test_meta_reporting_ninety_percent_pauses_the_bucket(self):
        quota.record_pressure(self.store, "instagram", 92, 0, now=self.T)
        with self.assertRaisesRegex(quota.QuotaExceeded, "Meta reported 92%"):
            quota.check(self.store, {"ig.media": 1}, now=self.T + timedelta(minutes=5))
        quota.check(self.store, {"ig.media": 1}, now=self.T + timedelta(minutes=16))
        quota.record_pressure(self.store, "instagram", 95, 40, now=self.T)
        with self.assertRaises(quota.QuotaExceeded):
            quota.check(self.store, {"ig.media": 1}, now=self.T + timedelta(minutes=30))

    def test_a_lower_share_soon_after_a_higher_one_does_not_replace_it(self):
        quota.record_pressure(self.store, "instagram", 51, 0, now=self.T)
        quota.record_pressure(self.store, "instagram", 1, 0, now=self.T + timedelta(minutes=2))
        self.assertEqual(quota.pressure(self.store, "instagram", now=self.T).pct, 51)
        quota.record_pressure(self.store, "instagram", 1, 0, now=self.T + timedelta(minutes=20))
        self.assertEqual(quota.pressure(self.store, "instagram", now=self.T).pct, 1)

    def test_usage_headers_give_the_highest_share_and_the_wait(self):
        h = {"X-App-Usage": '{"call_count":14,"total_cputime":3,"total_time":20}',
             "x-business-use-case-usage": '{"1":[{"type":"instagram","call_count":41,"total_cputime":2,'
                                          '"total_time":5,"estimated_time_to_regain_access":7}]}'}
        self.assertEqual(instagram.usage_from_headers(h), {"pct": 41, "regain_minutes": 7})
        self.assertEqual(instagram.usage_from_headers({"X-App-Usage": "junk"}), {"pct": 0, "regain_minutes": 0})

    def test_a_call_records_the_reported_usage_and_a_rate_limit_error_pauses(self):
        def busy(path, params):
            return {"business_discovery": {"id": "1", "username": "x"}, "_usage": {"pct": 93, "regain_minutes": 0}}
        instagram.business_discovery(self.store, UID, "x", transport=busy)
        with self.assertRaisesRegex(quota.QuotaExceeded, "Meta reported 93%"):
            instagram.business_discovery(self.store, UID, "x", transport=busy)

        def limited(path, params):
            raise instagram.InstagramError("Application request limit reached", 4)
        with self.store.transaction() as c:
            c.execute("DELETE FROM rate_pressure")
        with self.assertRaisesRegex(quota.QuotaExceeded, "rate limit"):
            instagram.account(self.store, UID, transport=limited)
        self.assertEqual(quota.pressure(self.store, "instagram").pct, 100)


# --- the token ------------------------------------------------------------------------------------

class TokenTest(unittest.TestCase):
    def test_debug_token_payload_gives_expiry_and_days_left(self):
        st_ = instagram.token_status_from(payload("ig_debug_token.json"),
                                          now=datetime(2026, 10, 12, 20, 0, tzinfo=timezone.utc))
        self.assertEqual((st_.valid, st_.type, st_.expires_at[:10], st_.days_left), (True, "USER", "2026-12-11", 59))
        self.assertIn("instagram_manage_insights", st_.scopes)

    def test_an_expired_token_is_invalid_and_a_permanent_one_has_no_expiry(self):
        p = {"data": {"is_valid": True, "expires_at": 1_700_000_000}}
        self.assertEqual((instagram.token_status_from(p).valid, instagram.token_status_from(p).days_left), (False, 0))
        p = {"data": {"is_valid": True, "expires_at": 0}}
        self.assertEqual((instagram.token_status_from(p).expires_at, instagram.token_status_from(p).days_left),
                         (None, None))

    def test_refresh_rewrites_only_the_token_line_with_mode_600(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / ".env"
            path.write_text("# keys\nINSTAGRAM_APP_ID=1\nINSTAGRAM_ACCESS_TOKEN=old\nYOUTUBE_API_KEY=k\n")
            with mock.patch.dict(os.environ, {"CF_ENV_FILE": str(path), "INSTAGRAM_ACCESS_TOKEN": "old",
                                              "INSTAGRAM_APP_ID": "1", "INSTAGRAM_APP_SECRET": "s"}):
                got = instagram.exchange_token(transport=lambda p, q: {"access_token": "new", "expires_in": 5184000})
                env.set_value(env.IG_TOKEN_VAR, got["access_token"])
                self.assertEqual(os.environ["INSTAGRAM_ACCESS_TOKEN"], "new")
            self.assertEqual(path.read_text(), "# keys\nINSTAGRAM_APP_ID=1\nINSTAGRAM_ACCESS_TOKEN=new\nYOUTUBE_API_KEY=k\n")
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)


# --- the own account ---------------------------------------------------------------------------------

class OwnTest(Case):
    def setUp(self):
        super().setUp()
        self.g.own_account = {"id": UID, "username": "kwi_asya", "name": "Asya", "followers_count": 1742,
                              "media_count": 264}
        first = payload("ig_own_media.json")
        second = {"data": [reel("DeOwnReel01", "2026-10-01T10:00:00Z", None, likes=20, caption="Close up, me\n")]}
        second["data"][0]["insights"] = {"data": [{"name": "views", "values": [{"value": 400}]},
                                                  {"name": "reach", "values": [{"value": 300}]},
                                                  {"name": "shares", "values": [{"value": 2}]}]}
        self.g.own_pages = [first, second]

    def test_sync_stores_reels_with_insights_and_the_report_ranks_them(self):
        r = own.sync(self.store, transport=self.g, now=NOW)
        self.assertEqual((r.handle, r.followers, r.pages, r.reels, r.with_insights), ("kwi_asya", 1742, 2, 2, 2))
        self.assertEqual(r.calls, {"ig.account": 1, "ig.media": 2})
        rep = own.report(self.store)
        self.assertEqual([(x.rank, x.external_id, x.views, x.reach, x.shares, x.saved) for x in rep.reels],
                         [(1, "DeOwnReel02", 2043, 1571, 63, 14), (2, "DeOwnReel01", 400, 300, 2, None)])
        self.assertEqual(rep.reels[0].title, "Therapy? I have a field 🌾")
        self.assertEqual(rep.reels[0].avg_watch_s, 6.3)
        self.assertEqual(rep.median_views, 1221.5)
        self.assertAlmostEqual(rep.reels[0].vs_median, 5.11)

    def test_marks_split_the_report_for_the_hypothesis(self):
        own.sync(self.store, transport=self.g, now=NOW)
        own.mark(self.store, "https://www.instagram.com/reel/DeOwnReel02/?igsh=x", "closeup_emotion")
        g = own.report(self.store).marks[0]
        self.assertEqual((g.mark, g.reels, g.others, g.median_views, g.others_median_views),
                         ("closeup_emotion", 1, 1, 2043, 400))
        self.assertEqual(own.mark(self.store, "DeOwnReel02", "closeup_emotion", remove=True), [])
        with self.assertRaises(own.OwnError):
            own.mark(self.store, "DeOwnReel02", "Close Up")

    def test_a_page_whose_nested_insights_fail_is_read_again_and_asked_one_by_one(self):
        self.g.fail_nested = True
        self.g.own_pages = [payload("ig_own_media.json")]
        mid = self.g.own_pages[0]["data"][0]["id"]
        self.g.insights[mid] = {"data": self.g.own_pages[0]["data"][0]["insights"]["data"]}
        r = own.sync(self.store, transport=self.g, now=NOW)
        self.assertEqual((r.reels, r.with_insights), (1, 1))
        self.assertEqual(r.calls, {"ig.account": 1, "ig.media": 2, "ig.insights": 1})
        self.assertEqual(own.report(self.store).reels[0].reach, 1571)

    def test_pre_business_reels_stop_insights_and_take_views_from_business_discovery(self):
        old = [reel(f"OldOwn{i:04d}", f"2024-0{i + 1}-01T10:00:00Z", None, likes=30) for i in range(3)]
        page = payload("ig_own_media.json")
        page["data"] += old
        self.g.own_pages = [page]
        self.g.fail_nested = True
        mid = page["data"][0]["id"]
        self.g.insights[mid] = {"data": page["data"][0]["insights"]["data"]}

        def refuse(path, params, inner=self.g):
            if path.endswith("/insights") and path.split("/")[0] != mid:
                raise instagram.InstagramError("Media posted before business account conversion", 100, 2108006)
            return inner(path, params)
        self.account("kwi_asya", [reel(f"OldOwn{i:04d}", "2024-01-01T10:00:00Z", 700 + i) for i in range(3)], aid=UID)
        r = own.sync(self.store, transport=refuse, now=NOW)
        self.assertEqual((r.reels, r.with_insights, r.views_from_discovery), (4, 1, 3))
        self.assertEqual(r.calls, {"ig.account": 1, "ig.media": 2, "ig.insights": 2, "ig.business_discovery": 1})
        self.assertIn("before the account became a business account", r.errors[-1])
        views = {x.external_id: (x.views, x.reach) for x in own.report(self.store).reels}
        self.assertEqual(views["OldOwn0002"], (702, None))
        self.assertEqual(views["DeOwnReel02"], (2043, 1571))

    def test_report_without_a_sync_says_what_to_run(self):
        with self.assertRaisesRegex(own.OwnError, "own sync"):
            own.report(self.store)


# --- the Author's picks ---------------------------------------------------------------------------------

class PicksTest(Case):
    def resolver(self, answers: dict):
        slept: list[float] = []

        def extract(url):
            got = answers.get(ingest.instagram_shortcode(url))
            if isinstance(got, Exception) or got is None:
                raise got or FetchError("yt-dlp: Instagram sent an empty media response")
            return got
        r = picks.YtDlpResolver(extract, delay_s=3, sleep=slept.append, clock=lambda: 0.0)
        return r, slept

    def test_ytdlp_names_the_owner_and_business_discovery_brings_the_reel_and_baseline(self):
        media = [reel("OwnerReel1", ago(days=4), 9000)] + [reel(f"Ob{i:07d}", ago(days=10 + i), 1000) for i in range(6)]
        self.account("cutiepookiecookie", media)
        res, _ = self.resolver({"OwnerReel1": {"channel": "cutiepookiecookie"}})
        p = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/reel/OwnerReel1/?igsh=abc",
                                note="фулл контент и надписи пиздить можно", resolver=res, ig_transport=self.g)
        self.assertEqual((p.status, p.owner, p.url), ("ytdlp", "@cutiepookiecookie",
                                                       "https://www.instagram.com/reel/OwnerReel1/"))
        self.assertEqual(notes.list(self.store, kind="card", key="OwnerReel1")[0].text,
                         "фулл контент и надписи пиздить можно")
        row = [r for r in feed.feed(self.store, "me-walks", now=NOW) if r.external_id == "OwnerReel1"][0]
        self.assertEqual((row.pick, row.candidate, row.views), (True, False, 9000))
        self.assertAlmostEqual(row.outlier, 9.0)
        again = picks.add_reference(self.store, "me-walks", "instagram.com/reel/OwnerReel1/",
                                    note="фулл контент и надписи пиздить можно", resolver=res, ig_transport=self.g)
        self.assertEqual((again.status, again.note), ("store", p.note))
        self.assertEqual(len(notes.list(self.store, kind="card", key="OwnerReel1")), 1)

    def test_a_reel_older_than_the_owners_page_keeps_ytdlp_counts(self):
        self.account("odarka_komarova", [reel("Newer00001", ago(days=1), 50)])
        res, _ = self.resolver({"OldReel001": {"channel": "odarka_komarova", "like_count": 777, "view_count": None,
                                               "description": "Street vibes\n#berlin", "timestamp": 1760000000}})
        p = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/reel/OldReel001/",
                                resolver=res, ig_transport=self.g)
        self.assertEqual((p.status, p.owner, p.title), ("ytdlp", "@odarka_komarova", "Street vibes"))
        self.assertIn("not in the owner", p.detail)
        self.assertEqual(feed.reference(self.store, "OldReel001").likes, 777)

    def test_an_older_reel_is_found_by_paging_the_owner_deeper(self):
        media = [reel(f"New{i:07d}", ago(days=1 + i / 100), 10) for i in range(50)]
        media += [reel(f"Mid{i:07d}", ago(days=3 + i / 100), 10) for i in range(50)]
        media += [reel("Deep000001", ago(days=8), 4321)] + [reel(f"Old{i:07d}", ago(days=9 + i), 10) for i in range(20)]
        self.account("lyuba_bich", media)
        stamp = int((NOW - timedelta(days=8)).timestamp())
        res, _ = self.resolver({"Deep000001": {"channel": "lyuba_bich", "timestamp": stamp}})
        p = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/reel/Deep000001/",
                                resolver=res, ig_transport=self.g)
        self.assertEqual((p.status, p.detail), ("ytdlp", None))
        self.assertEqual(feed.reference(self.store, "Deep000001").views, 4321)
        afters = [(re.search(r"media\.after\(([^)]+)\)", q["fields"]) or [None, None])[1] for _, q in self.g.calls]
        self.assertEqual(afters, [None, "50", "100"])  # the first page is not read twice

    def test_refusals_stop_ytdlp_and_unmatched_links_stay_unresolved_with_their_note(self):
        res, slept = self.resolver({})
        a = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/reel/Unknown001/",
                                note="машина", resolver=res)
        b = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/p/Unknown002/", resolver=res)
        c = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/reel/Unknown003/", resolver=res)
        self.assertEqual([x.status for x in (a, b, c)], ["unresolved"] * 3)
        self.assertEqual(res.calls, 2)  # the third link was not sent to Instagram
        self.assertIn("refused 2 times", c.detail)
        self.assertEqual(slept, [3])
        rows = {r.external_id: r for r in feed.feed(self.store, "me-walks", now=NOW)}
        self.assertEqual((rows["Unknown001"].handle, rows["Unknown001"].pick), (None, True))
        self.assertIn("владелец неизвестен", feed.report_line(1, rows["Unknown001"]))
        self.assertEqual(rows["Unknown002"].url, "https://www.instagram.com/p/Unknown002/")

    def test_a_shortcode_the_scout_already_read_needs_no_ytdlp(self):
        self.account("berlinstrolls", [reel("Scouted001", ago(days=2), 100)])
        self.add_ig("berlinstrolls")
        scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)
        res, _ = self.resolver({})
        p = picks.add_reference(self.store, "me-walks", "https://www.instagram.com/reel/Scouted001/", resolver=res)
        self.assertEqual((p.status, p.owner, res.calls), ("store", "@berlinstrolls", 0))


# --- fetch -------------------------------------------------------------------------------------------------

class FetchTest(Case):
    def test_a_refused_download_leaves_a_caption_only_card(self):
        self.account("berlinstrolls", [reel("CapOnly001", ago(days=2), 1234, caption="Just a caption\n#x")])
        self.add_ig("berlinstrolls")
        scout.scout(self.store, "me-walks", ig_transport=self.g, now=NOW)

        def refuse(url, d, vid):
            raise FetchError("yt-dlp: login required")
        fail = lambda *a, **k: (_ for _ in ()).throw(AssertionError("must not run"))  # noqa: E731
        a = fetch.Adapters(extract=fail, download=refuse, transcribe=fail, proxy=fail, shotlog=fail, ocr=fail)
        r = fetch.fetch(self.store, "https://www.instagram.com/reel/CapOnly001/?igsh=1", watchlist="me-walks",
                        adapters=a, root=Path(self.tmp.name))
        m = r["card"]["measured"]
        self.assertEqual((r["video_id"], m["platform"], m["kind"], m["caption"], m["counts"]["views"]),
                         ("CapOnly001", "instagram", "short", "Just a caption\n#x", 1234))
        self.assertIn("caption-only", m["notes"]["media"])
        self.assertTrue(r["steps"]["transcript"].startswith("skipped"))
        self.assertTrue((Path(self.tmp.name) / "references" / "me-walks" / "CapOnly001" / "card.json").exists())

    def test_an_unknown_reel_says_how_to_get_it_in(self):
        with self.assertRaisesRegex(FetchError, "add-reference"):
            fetch.fetch(self.store, "https://www.instagram.com/reel/NotHere001/")
