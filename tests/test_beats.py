"""cf.beats: grid sanity on a synthetic click track, energy, intro_end, sections, drop. No model run."""

import unittest

import numpy as np

from cf.beats import (click_track, energy_sections, find_drop, grid_sanity, intro_end, mean_energy,
                      parse_window, rms_curve)

SR = 8000


def synthetic_track(bpm=120.0, quiet_s=3.0, loud_from_s=None, seconds=40.0):
    """Clicks at ``bpm`` over a noise bed: quiet for ``quiet_s``, then full level
    (and louder still from ``loud_from_s``). Returns (signal, beats)."""
    rng = np.random.default_rng(0)
    n = int(seconds * SR)
    t = np.arange(n) / SR
    gain = np.where(t < quiet_s, 0.05, 0.5)
    if loud_from_s is not None:
        gain = np.where(t >= loud_from_s, 1.0, gain)
    sig = (rng.standard_normal(n) * 0.1 * gain).astype(np.float32)
    beats = list(np.arange(quiet_s, seconds, 60.0 / bpm))
    sig += click_track(beats, beats[::4], SR, seconds)[:n] * gain
    return sig, [round(b, 3) for b in beats]


class GridSanityTest(unittest.TestCase):
    def test_click_track_grid_is_regular(self):
        _, beats = synthetic_track(bpm=125.0)
        s = grid_sanity(beats)
        self.assertAlmostEqual(s["bpm"], 125.0, delta=0.5)
        self.assertLess(s["ibi_cv"], 0.03)
        self.assertTrue(s["ok"])

    def test_jittered_grid_fails_cv(self):
        rng = np.random.default_rng(1)
        beats = np.cumsum(0.5 + rng.normal(0, 0.05, 60))
        s = grid_sanity(list(beats))
        self.assertGreater(s["ibi_cv"], 0.03)
        self.assertFalse(s["ok"])

    def test_implausible_bpm_fails(self):
        s = grid_sanity([i * 0.25 for i in range(40)])  # 240 BPM
        self.assertEqual(s["bpm"], 240.0)
        self.assertFalse(s["bpm_ok"])

    def test_window_limits(self):
        beats = [i * 0.5 for i in range(100)]
        s = grid_sanity(beats, upto=10.0, after=2.0)
        self.assertEqual((s["from_s"], s["to_s"], s["beats"]), (2.0, 10.0, 17))
        self.assertFalse(grid_sanity([1.0, 2.0])["ok"])


class EnergyTest(unittest.TestCase):
    def test_rms_curve_is_normalized_per_half_second(self):
        sig, _ = synthetic_track(seconds=10.0)
        e = rms_curve(sig, SR)
        self.assertEqual(len(e), 20)
        self.assertAlmostEqual(float(e.max()), 1.0)
        self.assertLess(float(e[:6].max()), 0.35)   # the quiet first 3 s
        self.assertGreater(float(e[6:].min()), 0.35)

    def test_intro_end_is_first_downbeat_after_the_rise(self):
        sig, beats = synthetic_track(bpm=120.0, quiet_s=3.0)
        e = rms_curve(sig, SR)
        downbeats = [1.0, 3.0, 5.0, 7.0]  # a downbeat inside the quiet part must not count
        self.assertEqual(intro_end(e, downbeats), 3.0)
        self.assertEqual(intro_end(e, [1.0, 3.2, 5.2]), 3.2)
        self.assertIsNone(intro_end(np.zeros(10), downbeats))
        # Loud from the first window: the first downbeat (the quiet-start rule is a no-op).
        self.assertEqual(intro_end(np.ones(10), [1.62, 2.62]), 1.62)

    def test_sections_and_drop_on_the_downbeat_grid(self):
        sig, beats = synthetic_track(bpm=120.0, quiet_s=4.0, loud_from_s=20.0, seconds=36.0)
        e = rms_curve(sig, SR)
        downbeats = beats[::4]  # 4.0, 6.0, ... (bars of 2 s)
        secs = energy_sections(e, downbeats, 0.0, 36.0)
        self.assertEqual(secs[0]["label"], "intro")
        self.assertEqual(secs[-1]["label"], "high")
        self.assertEqual(secs[-1]["start"], 20.0)
        drop = find_drop(e, downbeats, secs, 0.0, 36.0)
        self.assertIn(drop["t"], (4.0, 20.0))
        self.assertGreater(drop["jump"], 0)
        self.assertGreater(mean_energy(e, 20.0, 22.0), mean_energy(e, 18.0, 20.0))

    def test_parse_window(self):
        self.assertEqual(parse_window("0:60", 270.0), (0.0, 60.0))
        self.assertEqual(parse_window(":30", 20.0), (0.0, 20.0))
        self.assertEqual(parse_window(None, 12.5), (0.0, 12.5))
        with self.assertRaises(ValueError):
            parse_window("50:40", 270.0)


if __name__ == "__main__":
    unittest.main()
