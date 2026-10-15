"""Data API quota: every call charges its bucket; a call that would cross a daily limit is refused first.

Buckets (determine_quota_cost, 2026): search.list has its own bucket of 100 calls a day
at 1 unit each; every other method shares 10 000 units a day.
"""

import os
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from cf.research import quota
from cf.research import store as st

# 2026-10-11 20:00 UTC is 13:00 in California, the quota day 2026-10-11.
NOON_PT = datetime(2026, 10, 11, 20, 0, tzinfo=timezone.utc)
# 2026-10-12 06:00 UTC is still 23:00 on 2026-10-11 in California.
LATE_PT = datetime(2026, 10, 12, 6, 0, tzinfo=timezone.utc)
# 2026-10-12 08:00 UTC is 01:00 on 2026-10-12 in California: a fresh quota day.
NEXT_PT = datetime(2026, 10, 12, 8, 0, tzinfo=timezone.utc)


class QuotaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = st.open_store(Path(self.tmp.name) / "f.db")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def bucket(self, name, now=NOON_PT):
        return {b.bucket: b for b in quota.usage(self.store, now=now).buckets}[name]

    def test_unit_costs_and_buckets(self):
        self.assertEqual(quota.cost("search.list"), ("search", 1))
        for m in ("channels.list", "playlistItems.list", "videos.list"):
            self.assertEqual(quota.cost(m), ("default", 1))
        self.assertEqual(quota.limits(), {"default": 10_000, "search": 100, "instagram": 100})

    def test_usage_adds_up_per_bucket_and_method(self):
        quota.charge(self.store, "channels.list", now=NOON_PT)
        quota.charge(self.store, "channels.list", now=NOON_PT)
        quota.charge(self.store, "search.list", now=NOON_PT)
        u = quota.usage(self.store, now=NOON_PT)
        self.assertEqual(u.day, "2026-10-11")
        self.assertEqual({(b.bucket, b.used, b.remaining) for b in u.buckets},
                         {("default", 2, 9_998), ("search", 1, 99), ("instagram", 0, 100)})
        self.assertEqual({m.method: (m.calls, m.units) for m in u.by_method},
                         {"channels.list": (2, 2), "search.list": (1, 1)})

    def test_the_day_follows_pacific_midnight(self):
        quota.charge(self.store, "videos.list", now=NOON_PT)
        self.assertEqual(self.bucket("default", now=LATE_PT).used, 1)
        self.assertEqual(self.bucket("default", now=NEXT_PT).used, 0)

    def test_the_101st_search_is_refused_and_not_counted(self):
        for _ in range(100):
            quota.charge(self.store, "search.list", now=NOON_PT)
        with self.assertRaises(quota.QuotaExceeded) as cm:
            quota.charge(self.store, "search.list", now=NOON_PT)
        msg = str(cm.exception)
        self.assertIn("search.list", msg)
        self.assertIn("100 of 100", msg)
        self.assertIn("Pacific", msg)
        self.assertEqual(self.bucket("search").used, 100)
        quota.charge(self.store, "channels.list", now=NOON_PT)  # the other bucket is untouched
        self.assertEqual(self.bucket("default").used, 1)

    def test_default_bucket_refuses_past_10000(self):
        quota.charge(self.store, "videos.list", calls=9_999, now=NOON_PT)
        quota.charge(self.store, "videos.list", now=NOON_PT)  # exactly 10 000 is allowed
        with self.assertRaises(quota.QuotaExceeded) as cm:
            quota.charge(self.store, "channels.list", now=NOON_PT)
        self.assertIn("10 000 of 10 000", str(cm.exception))
        self.assertEqual(self.bucket("default").remaining, 0)

    def test_a_run_can_check_its_whole_plan_up_front(self):
        quota.charge(self.store, "search.list", calls=60, now=NOON_PT)
        quota.check(self.store, {"search.list": 40, "videos.list": 500}, now=NOON_PT)
        with self.assertRaises(quota.QuotaExceeded) as cm:
            quota.check(self.store, {"search.list": 41, "videos.list": 500}, now=NOON_PT)
        self.assertIn("this run", str(cm.exception))
        self.assertEqual(self.bucket("search").used, 60)

    def test_limits_can_be_raised_for_a_project_with_more_quota(self):
        with mock.patch.dict(os.environ, {"CF_QUOTA_SEARCH": "500"}):
            quota.charge(self.store, "search.list", calls=300, now=NOON_PT)
            self.assertEqual(self.bucket("search").remaining, 200)


if __name__ == "__main__":
    unittest.main()
