"""cf.build --grade-drx helpers: per-shot DRX lookup and build-option comparison. No Resolve."""

import tempfile
import unittest
from pathlib import Path

from cf.build import BuildError, grade_build_differences, grade_drx_files


class GradeDrxFiles(unittest.TestCase):
    def test_export_stills_names_and_plain_names(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            for n in ("s01_1.1.1.drx", "s01_1.1.1.jpg", "s02.drx", "s10_1.10.1.drx"):
                (d / n).write_text("x")
            got = grade_drx_files(d, ["s01", "s02", "s10"])
            self.assertEqual({k: v.name for k, v in got.items()},
                             {"s01": "s01_1.1.1.drx", "s02": "s02.drx", "s10": "s10_1.10.1.drx"})

    def test_missing_or_ambiguous_shot_fails(self):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / "s01_1.1.1.drx").write_text("x")
            (d / "s01_1.1.2.drx").write_text("x")
            with self.assertRaises(BuildError) as e:
                grade_drx_files(d, ["s01", "s02"])
            self.assertIn("s01: 2 DRX files", str(e.exception))
            self.assertIn("s02: 0 DRX files", str(e.exception))


class GradeBuildDifferences(unittest.TestCase):
    def test_reports_only_differing_known_keys(self):
        meta = {"build": {"deliver": "sdr", "hlg_normalize": "none", "look": "none", "other": 1}}
        self.assertEqual(grade_build_differences(meta, {"deliver": "sdr", "hlg_normalize": "none", "look": "none"}), [])
        diffs = grade_build_differences(meta, {"deliver": "sdr", "hlg_normalize": "cdl", "look": "none"})
        self.assertEqual(len(diffs), 1)
        self.assertIn("hlg_normalize", diffs[0])

    def test_no_build_block(self):
        self.assertEqual(grade_build_differences({}, {"deliver": "sdr"}), [])


if __name__ == "__main__":
    unittest.main()
