"""cf.research.kinds: short/long threshold and ISO 8601 durations."""

import unittest

from cf.research.kinds import SHORT_MAX_S, parse_iso_duration, video_kind


class KindTest(unittest.TestCase):
    def test_threshold_is_inclusive(self):
        self.assertEqual(video_kind(SHORT_MAX_S), "short")
        self.assertEqual(video_kind(SHORT_MAX_S + 1), "long")
        self.assertEqual(video_kind(45), "short")

    def test_unknown_duration_has_no_kind(self):
        self.assertIsNone(video_kind(None))
        self.assertIsNone(video_kind(0))


class IsoDurationTest(unittest.TestCase):
    def test_parses_data_api_durations(self):
        cases = {"PT1M3S": 63, "PT45S": 45, "PT2H0M5S": 7205, "PT10M": 600, "P1DT1S": 86401, "PT0.5S": 0.5}
        for text, seconds in cases.items():
            with self.subTest(text=text):
                self.assertEqual(parse_iso_duration(text), seconds)

    def test_zero_and_junk_are_none(self):
        for text in ("P0D", "PT0S", "", None, "1:03", "P"):
            with self.subTest(text=text):
                self.assertIsNone(parse_iso_duration(text))


if __name__ == "__main__":
    unittest.main()
