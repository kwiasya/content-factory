"""The feed of a Watchlist on synthetic snapshots: filters, order, rows, the not-analyzed mark."""

import tempfile
import unittest
from pathlib import Path

from cf.research import feed
from cf.research import store as st
from cf.research import watchlist as wl
from research_synth import NOW, add_member, add_videos, ago, video_item

A = "UCaaaaaaaaaaaaaaaaaaaaaa"
B = "UCbbbbbbbbbbbbbbbbbbbbbb"
C = "UCcccccccccccccccccccccc"
D = "UCdddddddddddddddddddddd"


class FeedTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        s = self.store = st.open_store(Path(self.tmp.name) / "f.db", create=True)
        wl.create(s, "lisbon", format_id="walk_reel")
        wl.create(s, "other", format_id="travel_long")
        add_member(s, "lisbon", A, "@alpha")
        add_member(s, "lisbon", B, "@beta")
        add_member(s, "lisbon", D, "@delta")
        add_member(s, "other", C, "@gamma")
        add_videos(s, [video_item(f"aL{i}", A, ago(days=10 + i), 600, 100) for i in range(6)]
                   + [video_item("ancient", A, ago(days=60), 600, 100_000),
                      video_item("hitL", A, ago(days=2), 600, 500, title="Alfama at dawn"),
                      video_item("midL", A, ago(days=1), 900, 300)]
                   + [video_item(f"aS{i}", A, ago(days=10 + i), 40, 1000) for i in range(5)]
                   + [video_item("hitS", A, ago(days=1), 30, 2000),
                      video_item("longS", A, ago(days=1), 150, 4000)]
                   + [video_item("b1", B, ago(days=2), 900, 50_000),
                      video_item("b2", B, ago(days=1), 40, 9_000)]
                   + [video_item(f"dL{i}", D, ago(days=10 + i), 600, 50) for i in range(5)]
                   + [video_item("d1", D, ago(days=1), 600, 100),
                      video_item("c1", C, ago(days=1), 600, 10_000_000)])
        hit = s.one("SELECT id FROM video WHERE external_id = 'hitL'")["id"]
        s.conn.execute("INSERT INTO card (video_id, schema, analysis, written_at) "
                       "VALUES (?, 'cf-reference-card/1', '{}', ?)", (hit, ago(hours=1)))
        mid = s.one("SELECT id FROM video WHERE external_id = 'midL'")["id"]  # fetched, measured, not analyzed
        s.conn.execute("INSERT INTO card (video_id, schema, written_at) VALUES (?, 'cf-reference-card/1', ?)",
                       (mid, ago(hours=1)))
        s.conn.commit()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def ids(self, **kw):
        return [r.external_id for r in feed.feed(self.store, "lisbon", now=NOW, **kw)]

    def test_order_is_outlier_then_views_with_unscored_last(self):
        self.assertEqual(self.ids(lookback_days=3), ["hitL", "longS", "midL", "hitS", "d1", "b1", "b2"])

    def test_rows_carry_date_outlier_views_title_handle_link_and_analysis_flag(self):
        first, second = feed.feed(self.store, "lisbon", lookback_days=3, now=NOW)[:2]
        self.assertEqual((first.date, first.views, first.title, first.handle, first.url, first.analyzed),
                         (ago(days=2)[:10], 500, "Alfama at dawn", "@alpha",
                          "https://www.youtube.com/watch?v=hitL", True))
        self.assertAlmostEqual(first.outlier, 5.0)
        self.assertFalse(second.analyzed)

    def test_a_measured_card_without_analysis_still_needs_analysis(self):
        rows = {r.external_id: r for r in feed.feed(self.store, "lisbon", lookback_days=3, now=NOW)}
        self.assertFalse(rows["midL"].analyzed)
        report = feed.report("lisbon", list(rows.values()), lookback_days=3)
        self.assertIn("без разбора 6.", report.splitlines()[0])
        mid_line = next(ln for ln in report.splitlines() if "watch?v=midL" in ln)
        self.assertTrue(mid_line.endswith("· без разбора"), mid_line)
        hit_line = next(ln for ln in report.splitlines() if "watch?v=hitL" in ln)
        self.assertNotIn("без разбора", hit_line)

    def test_lookback_window(self):
        got = self.ids()
        self.assertIn("aL0", got)
        self.assertNotIn("ancient", got)
        self.assertEqual(self.ids(lookback_days=1.5), ["longS", "midL", "hitS", "d1", "b2"])

    def test_min_outlier_drops_unscored_and_lower(self):
        self.assertEqual(self.ids(lookback_days=3, min_outlier=3), ["hitL", "longS", "midL"])

    def test_min_views(self):
        self.assertEqual(self.ids(lookback_days=3, min_views=2000), ["longS", "hitS", "b1", "b2"])

    def test_kind(self):
        self.assertEqual(self.ids(lookback_days=3, kind="short"), ["longS", "hitS", "b2"])
        self.assertEqual(self.ids(lookback_days=3, kind="long"), ["hitL", "midL", "d1", "b1"])

    def test_max_duration(self):
        self.assertEqual(self.ids(lookback_days=3, max_duration_s=60), ["hitS", "b2"])

    def test_limit(self):
        self.assertEqual(self.ids(lookback_days=3, limit=2), ["hitL", "longS"])

    def test_channels_outside_the_watchlist_stay_out(self):
        self.assertNotIn("c1", self.ids())
        self.assertEqual([r.external_id for r in feed.feed(self.store, "other", now=NOW)], ["c1"])

    def test_unknown_watchlist_is_an_error(self):
        with self.assertRaises(wl.WatchlistError):
            feed.feed(self.store, "nope", now=NOW)


if __name__ == "__main__":
    unittest.main()
