"""python -m cf.research scout / snapshot / feed: JSON and the Russian report line. Fake transport, no network."""

import contextlib
import io
import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest import mock

from cf.research import cli, feed, youtube
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import FakeYouTube, add_member, channel_payload, iso, video_item

CH = "UCaaaaaaaaaaaaaaaaaaaaaa"
LENS = "UCq1W2e3R4t5Y6u7I8o9P0aS"


def real_ago(days=0, hours=0):
    return iso(datetime.now(timezone.utc) - timedelta(days=days, hours=hours))


class ScoutCliTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = str(Path(self.tmp.name) / "f.db")
        with st.open_store(self.db) as s:
            wl.create(s, "lisbon", format_id="walk_reel", queries=["lisbon walk"])
            add_member(s, "lisbon", CH, "@alpha")
        self.yt = yt = FakeYouTube()
        yt.uploads[CH] = [video_item(f"old{i}", CH, real_ago(days=5 + i), 40, 1000) for i in range(6)] + []
        yt.uploads[CH].insert(0, video_item("hit", CH, real_ago(days=1), 40, 5000, title="Alfama | at dawn"))
        yt.extra_videos["lens1"] = video_item("lens1", LENS, real_ago(days=2), 45, 70_000)
        yt.searches["lisbon walk"] = [{"items": [{"id": {"kind": "youtube#video", "videoId": "lens1"},
                                                  "snippet": {"channelId": LENS, "title": "lens1",
                                                              "publishedAt": real_ago(days=2),
                                                              "channelTitle": "Lisbon Lens"}}]}]
        yt.channels[LENS] = channel_payload(LENS, "@lisbonlens")["items"][0]

    def tearDown(self):
        self.tmp.cleanup()

    def run_cli(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.object(youtube, "http_transport", self.yt), \
                mock.patch.dict(os.environ, {"YOUTUBE_API_KEY": "test-key"}), \
                contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*argv, "--db", self.db])
        return code, out.getvalue(), err.getvalue()

    def json_of(self, *argv):
        code, out, err = self.run_cli(*argv, "--json")
        self.assertEqual(code, 0, err)
        return json.loads(out)

    def test_scout_snapshot_feed(self):
        r = self.json_of("scout", "lisbon")
        self.assertIsNone(r["stopped"])
        self.assertEqual(r["channels"][0]["new_videos"], 7)
        self.assertEqual(r["candidates"][0]["handle"], "@lisbonlens")
        s = self.json_of("snapshot", "lisbon")
        self.assertEqual((s["videos"], s["missing"]), (8, []))
        rows = self.json_of("feed", "lisbon", "--days", "3")
        self.assertEqual([x["external_id"] for x in rows], ["hit", "lens1"])
        self.assertEqual(rows[0]["outlier"], 5.0)
        self.assertEqual((rows[0]["handle"], rows[0]["analyzed"], rows[0]["url"]),
                         ("@alpha", False, "https://www.youtube.com/watch?v=hit"))
        self.assertIsNone(rows[1]["outlier"])
        self.assertTrue(rows[1]["candidate"])

    def test_feed_filters_on_the_command_line(self):
        self.json_of("scout", "lisbon")
        ids = lambda *a: [x["external_id"] for x in self.json_of("feed", "lisbon", *a)]  # noqa: E731
        self.assertEqual(ids("--min-outlier", "2"), ["hit"])
        self.assertEqual(ids("--min-views", "6000"), ["lens1"])
        self.assertEqual(ids("--kind", "long"), [])
        self.assertEqual(ids("--max-duration", "42", "--days", "3"), ["hit"])
        self.assertEqual(len(ids("--limit", "3")), 3)

    def test_feed_report_lines_in_russian(self):
        self.json_of("scout", "lisbon")
        code, out, _ = self.run_cli("feed", "lisbon", "--days", "3")
        self.assertEqual(code, 0)
        lines = [ln for ln in out.splitlines() if ln[:2] in ("1.", "2.")]
        self.assertEqual(lines[0], f"1. **5,0x** · 5 тыс. просмотров · {real_ago(days=1)[:10]} · "
                                   "«Alfama | at dawn» · @alpha · https://www.youtube.com/watch?v=hit · без разбора")
        self.assertTrue(lines[1].startswith("2. **—** · 70 тыс. просмотров"))
        self.assertIn("кандидат", lines[1])

    def test_scout_human_output_and_quota_stop(self):
        code, out, _ = self.run_cli("scout", "lisbon")
        self.assertEqual(code, 0)
        self.assertIn("| @alpha |", out)
        self.assertIn("@lisbonlens", out)
        with mock.patch.dict(os.environ, {"CF_QUOTA_SEARCH": "0"}):
            code, _, err = self.run_cli("scout", "lisbon")
        self.assertEqual(code, 1)
        self.assertIn("quota", err)

    def test_unknown_watchlist(self):
        code, out, err = self.run_cli("feed", "nope", "--json")
        self.assertEqual((code, out), (1, ""))
        self.assertIn("nope", err)


class ReportLineTest(unittest.TestCase):
    def row(self, **kw):
        base = dict(external_id="x", date="2026-10-09", outlier=12.345, views=1_203_344, title="T",
                    handle="@h", url="https://www.youtube.com/watch?v=x", analyzed=True, kind="short",
                    duration_s=30.0, published_at="2026-10-09T00:00:00Z", channel_title="H")
        base.update(kw)
        return feed.FeedRow(**base)

    def test_numbers(self):
        self.assertEqual(feed.report_line(3, self.row()),
                         "3. **12,3x** · 1,2 млн просмотров · 2026-10-09 · «T» · @h · https://www.youtube.com/watch?v=x")
        self.assertIn("· 1 просмотр ·", feed.report_line(1, self.row(views=1)))
        self.assertIn("· 3 просмотра ·", feed.report_line(1, self.row(views=3)))
        self.assertIn("· 999 просмотров ·", feed.report_line(1, self.row(views=999)))
        self.assertIn("· 18,4 тыс. просмотров ·", feed.report_line(1, self.row(views=18_422)))
        self.assertIn("**—** · — просмотров", feed.report_line(1, self.row(outlier=None, views=None)))
        self.assertIn("· без хэндла ·", feed.report_line(1, self.row(handle=None, channel_title=None)))
        self.assertIn("· Lisbon Lens ·", feed.report_line(1, self.row(handle=None, channel_title="Lisbon Lens")))


if __name__ == "__main__":
    unittest.main()
