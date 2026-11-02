"""cf.hdr: HLG math, SDR overlays at graphics white, the log-composite alpha (no ffmpeg, no Resolve)."""

import unittest

import numpy as np

from cf.hdr import (hlg_inverse_oetf, hlg_oetf, hlg_signal_to_nits, log_composite_alpha, nits_to_hlg_signal,
                    sdr_to_hlg)


class HlgMathTest(unittest.TestCase):
    def test_oetf_round_trip_and_anchor_points(self):
        e = np.linspace(0, 1, 101)
        np.testing.assert_allclose(hlg_inverse_oetf(hlg_oetf(e)), e, atol=1e-9)
        self.assertAlmostEqual(float(hlg_oetf(1 / 12)), 0.5, places=9)
        self.assertAlmostEqual(float(hlg_oetf(1.0)), 1.0, places=6)

    def test_reference_white_is_75_percent(self):
        # BT.2408: 203 nits = 75 % HLG on a 1000-nit display.
        self.assertAlmostEqual(float(nits_to_hlg_signal(203)), 0.75, delta=0.001)
        self.assertAlmostEqual(float(hlg_signal_to_nits(0.75)), 203, delta=0.5)
        self.assertAlmostEqual(float(hlg_signal_to_nits(1.0)), 1000, delta=0.01)


class SdrToHlgTest(unittest.TestCase):
    def test_white_black_and_grey(self):
        out = sdr_to_hlg(np.array([[1.0, 1, 1], [0, 0, 0], [0.5, 0.5, 0.5]]))
        np.testing.assert_allclose(out[0], [0.75, 0.75, 0.75], atol=0.001)
        np.testing.assert_allclose(out[1], [0, 0, 0], atol=1e-9)
        grey_nits = 203 * 0.5 ** 2.4
        self.assertAlmostEqual(float(hlg_signal_to_nits(out[2, 1])), grey_nits, delta=0.2)

    def test_white_level_parameter(self):
        out = sdr_to_hlg(np.array([1.0, 1, 1]), white_nits=1000)
        np.testing.assert_allclose(out, [1, 1, 1], atol=1e-6)

    def test_saturated_red_stays_in_range_and_red(self):
        r = sdr_to_hlg(np.array([1.0, 0, 0]))
        self.assertTrue(np.all((r >= 0) & (r <= 1)))
        self.assertGreater(r[0], r[1])
        self.assertGreater(r[1], 0)  # Rec.709 red has some green in Rec.2020


class LogCompositeAlphaTest(unittest.TestCase):
    def test_opaque_and_transparent_unchanged(self):
        a = log_composite_alpha(np.array([[1.0, 1, 1], [0, 0, 0], [0.3, 0.3, 0.3]]), np.array([1.0, 0.0, 1.0]))
        np.testing.assert_allclose(a, [1, 0, 1], atol=1e-9)

    def test_soft_black_backdrop_is_thinned(self):
        # A log composite darkens more than a gamma composite, so the alpha goes down.
        a = log_composite_alpha(np.array([[0.0, 0, 0]] * 3), np.array([0.1, 0.25, 0.45]))
        self.assertTrue(np.all(a < [0.1, 0.25, 0.45]))
        self.assertTrue(np.all(np.diff(a) > 0))
        self.assertAlmostEqual(float(a[1]), 0.116, delta=0.01)


class PublishVariantTest(unittest.TestCase):
    def test_variant_sources(self):
        import tempfile
        from pathlib import Path

        from cf.publish import sources

        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            for n in ("r.mp4", "r.normalized.mp4", "r.ambience.normalized.mp4", "r.hdr.mp4", "r.hdr.normalized.mp4"):
                (out / n).write_bytes(b"")
            self.assertEqual([p.name for p in sources(out, "r")[:2]], ["r.normalized.mp4", "r.ambience.normalized.mp4"])
            music, amb, own = sources(out, "r", "hdr")
            self.assertEqual((music.name, amb.name, own), ("r.hdr.normalized.mp4", "r.ambience.normalized.mp4", False))
            (out / "r.ambience.hdr.mp4").write_bytes(b"")
            self.assertEqual(sources(out, "r", "hdr")[1].name, "r.ambience.hdr.mp4")
            self.assertIsNone(sources(out, "r", "sdr-bright")[0])


if __name__ == "__main__":
    unittest.main()
