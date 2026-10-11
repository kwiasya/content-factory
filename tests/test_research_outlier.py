"""Outlier score on synthetic snapshots: views ÷ median of the channel's last 30 videos of the same kind,
at least 3 days old, without the video itself; None under 5 baseline videos."""

import tempfile
import unittest
from pathlib import Path

from cf.research import outlier
from cf.research import store as st
from research_synth import NOW, add_videos, ago, iso, video_item

CH = "UCaaaaaaaaaaaaaaaaaaaaaa"
OTHER = "UCbbbbbbbbbbbbbbbbbbbbbb"
LONG, SHORT = 600, 45


class OutlierTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def score(self, vid):
        return outlier.score(self.store, vid, now=NOW)

    def test_normal_channel_divides_by_the_median_of_its_older_videos(self):
        add_videos(self.store, [video_item(f"old{i}", CH, ago(days=4 + i), LONG, v)
                                for i, v in enumerate([100, 200, 300, 400, 500, 600, 700])]
                   + [video_item("new", CH, ago(days=1), LONG, 1000)])
        self.assertAlmostEqual(self.score("new"), 1000 / 400)

    def test_the_video_itself_is_not_in_its_own_baseline(self):
        add_videos(self.store, [video_item(f"old{i}", CH, ago(days=4 + i), LONG, v)
                                for i, v in enumerate([100, 200, 300, 400, 500, 600])])
        self.assertAlmostEqual(self.score("old5"), 600 / 300)  # median of 100..500

    def test_fewer_than_five_baseline_videos_give_none(self):
        add_videos(self.store, [video_item(f"old{i}", CH, ago(days=4 + i), LONG, 100 * (i + 1))
                                for i in range(4)] + [video_item("new", CH, ago(days=1), LONG, 1000)])
        self.assertIsNone(self.score("new"))
        self.assertIsNone(self.score("old0"))

    def test_videos_younger_than_three_days_are_not_baseline(self):
        add_videos(self.store, [video_item(f"old{i}", CH, ago(days=4 + i), LONG, v)
                                for i, v in enumerate([100, 200, 300, 400, 500, 600])]
                   + [video_item("young", CH, ago(days=2, hours=23), LONG, 1_000_000),
                      video_item("edge", CH, ago(days=3), LONG, 350)])
        # baseline of old5: 100..500 and edge (exactly 3 days old) → median 325; young is left out
        self.assertAlmostEqual(self.score("old5"), 600 / 325)

    def test_short_and_long_of_one_channel_do_not_mix(self):
        add_videos(self.store,
                   [video_item(f"l{i}", CH, ago(days=4 + i), LONG, 1_000) for i in range(5)]
                   + [video_item(f"s{i}", CH, ago(days=4 + i), SHORT, 100_000) for i in range(5)]
                   + [video_item("snew", CH, ago(days=1), SHORT, 300_000),
                      video_item("lnew", CH, ago(days=1), LONG, 3_000)])
        self.assertAlmostEqual(self.score("snew"), 3.0)
        self.assertAlmostEqual(self.score("lnew"), 3.0)

    def test_other_channels_do_not_count(self):
        add_videos(self.store, [video_item(f"o{i}", OTHER, ago(days=4 + i), LONG, 10) for i in range(10)]
                   + [video_item(f"c{i}", CH, ago(days=4 + i), LONG, 100) for i in range(3)]
                   + [video_item("new", CH, ago(days=1), LONG, 1000)])
        self.assertIsNone(self.score("new"))

    def test_only_the_last_thirty_videos_make_the_baseline(self):
        recent = [100] * 15 + [300] * 15
        add_videos(self.store, [video_item(f"r{i}", CH, ago(days=4 + i), LONG, v) for i, v in enumerate(recent)]
                   + [video_item(f"a{i}", CH, ago(days=40 + i), LONG, 1_000_000) for i in range(20)]
                   + [video_item("new", CH, ago(days=1), LONG, 1000)])
        self.assertAlmostEqual(self.score("new"), 1000 / 200)

    def test_views_come_from_the_latest_snapshot(self):
        items = [video_item(f"old{i}", CH, ago(days=4 + i), LONG, 100) for i in range(5)] \
            + [video_item("new", CH, ago(days=1), LONG, 200)]
        add_videos(self.store, items, taken_at=ago(days=1))
        for it in items:
            it["statistics"]["viewCount"] = str(int(it["statistics"]["viewCount"]) * 2)
        add_videos(self.store, items, taken_at=iso(NOW))
        add_videos(self.store, [video_item("new", CH, ago(days=1), LONG, 1)], taken_at=ago(days=1, hours=1))
        self.assertAlmostEqual(self.score("new"), 400 / 200)

    def test_a_video_without_snapshots_or_unknown_has_no_score(self):
        add_videos(self.store, [video_item(f"old{i}", CH, ago(days=4 + i), LONG, 100) for i in range(5)]
                   + [video_item("hidden", CH, ago(days=1), LONG, None)])
        self.assertIsNone(self.score("hidden"))
        self.assertIsNone(self.score("missing"))


if __name__ == "__main__":
    unittest.main()
