"""cf.look: DaVinci Intermediate curve, .cube format, identity spec, saturation. No Resolve."""

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np

from cf.look import (DI_LIN_CUT, DI_LOG_CUT, DWG_TO_709, REC709_TO_DWG, LookSpec, apply_dwg_di, apply_look,
                     apply_lut, apply_rec709_display, build_lut, di_decode, di_encode, lattice, load_spec,
                     read_cube, write_cube)

REPO = Path(__file__).resolve().parents[1]


def lab_chroma(rgb_lin_709: np.ndarray) -> np.ndarray:
    """CIE Lab chroma of linear Rec.709 values (D65)."""
    m = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = rgb_lin_709 @ m.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.hypot(a, b)


class DaVinciIntermediate(unittest.TestCase):
    def test_round_trip(self):
        x = np.linspace(0.0, 1.0, 10001)
        self.assertLess(np.abs(di_encode(di_decode(x)) - x).max(), 1e-12)
        lin = np.geomspace(1e-5, 100.0, 2001)
        self.assertLess(np.abs(di_decode(di_encode(lin)) / lin - 1).max(), 1e-12)

    def test_known_points(self):
        # Mid grey 0.18 sits at DI 0.336; one stop is 0.07329 code values on the log segment once
        # the +0.0075 offset is negligible (the HLG CDL offset -0.0749 = -1.02 stop in docs/resolve-rules.md relies on it).
        self.assertAlmostEqual(float(di_encode(0.18)), 0.33604, places=4)
        self.assertAlmostEqual(float(di_encode(8.0) - di_encode(4.0)), 0.07329, places=3)
        self.assertAlmostEqual(float(di_decode(0.0)), 0.0)
        self.assertAlmostEqual(float(di_decode(1.0)), 100.0, places=3)

    def test_cut_is_continuous(self):
        self.assertAlmostEqual(float(di_decode(DI_LOG_CUT)), DI_LIN_CUT, places=7)
        self.assertAlmostEqual(float(di_encode(DI_LIN_CUT)), DI_LOG_CUT, places=6)

    def test_gamut_matrices(self):
        np.testing.assert_allclose(DWG_TO_709 @ np.ones(3), np.ones(3), atol=1e-9)  # same D65 white
        np.testing.assert_allclose(DWG_TO_709 @ REC709_TO_DWG, np.eye(3), atol=1e-12)


class CubeFile(unittest.TestCase):
    def test_format_and_round_trip(self):
        lut = build_lut(load_spec(REPO / "looks" / "cinema-warm.json"), 17)
        with TemporaryDirectory() as tmp:
            f = write_cube(Path(tmp) / "x.cube", lut, "test", ["a comment"])
            lines = f.read_text().splitlines()
            self.assertIn('TITLE "test"', lines)
            self.assertIn("LUT_3D_SIZE 17", lines)
            self.assertIn("DOMAIN_MIN 0.0 0.0 0.0", lines)
            self.assertIn("DOMAIN_MAX 1.0 1.0 1.0", lines)
            data = [ln for ln in lines if ln[:1].isdigit()]
            self.assertEqual(len(data), 17 ** 3)
            self.assertTrue(all(len(ln.split()) == 3 for ln in data))
            back = read_cube(f)
        np.testing.assert_allclose(back, lut, atol=1e-6)
        self.assertGreaterEqual(back.min(), 0.0)
        self.assertLessEqual(back.max(), 1.0)

    def test_red_runs_fastest(self):
        g = lattice(3).reshape(-1, 3)
        np.testing.assert_allclose(g[1], [0.5, 0.0, 0.0])
        np.testing.assert_allclose(g[3], [0.0, 0.5, 0.0])
        np.testing.assert_allclose(g[9], [0.0, 0.0, 0.5])


class Identity(unittest.TestCase):
    def test_identity_spec_gives_identity_lut(self):
        lut = build_lut(LookSpec(), 33)
        self.assertLess(np.abs(lut - lattice(33)).max(), 1 / 1023 / 100)

    def test_identity_through_trilinear_lookup(self):
        rng = np.random.default_rng(1)
        px = rng.random((5000, 3))
        out = apply_lut(px, build_lut(LookSpec(), 33))
        self.assertLess(np.abs(out - px).max(), 1 / 1023)

    def test_identity_preview(self):
        px = np.random.default_rng(2).random((1000, 3))
        self.assertLess(np.abs(apply_rec709_display(px, LookSpec()) - px).max(), 1e-9)

    def test_unknown_key_rejected(self):
        with self.assertRaises(ValueError):
            LookSpec.from_dict({"name": "x", "contrast": {"amout": 1.2}})


class Grade(unittest.TestCase):
    def patch(self):
        return np.array([0.30, 0.18, 0.10])  # a warm, mid-saturation colour near mid grey

    def test_saturation_gain_increases_chroma(self):
        p = self.patch()
        out = apply_look(p, LookSpec.from_dict({"saturation": {"amount": 1.3}}))
        self.assertGreater(lab_chroma(out), lab_chroma(p) * 1.15)
        self.assertAlmostEqual(float(out @ [0.2126, 0.7152, 0.0722]), float(p @ [0.2126, 0.7152, 0.0722]), places=5)

    def test_skin_protection_reduces_the_boost(self):
        skin = np.array([0.42, 0.24, 0.17])  # HSV hue about 20 degrees
        free = apply_look(skin, LookSpec.from_dict({"saturation": {"amount": 1.3}}))
        kept = apply_look(skin, LookSpec.from_dict({"saturation": {"amount": 1.3, "skin": {"protect": 0.8}}}))
        self.assertLess(lab_chroma(kept), lab_chroma(free))
        self.assertGreater(lab_chroma(kept), lab_chroma(skin))

    def test_contrast_keeps_pivot_and_is_monotonic(self):
        spec = LookSpec.from_dict({"contrast": {"amount": 1.4}})
        grey = apply_look(np.full(3, 0.18), spec)
        np.testing.assert_allclose(grey, 0.18, atol=1e-12)
        ramp = np.geomspace(1e-4, 50, 500)
        y = apply_look(np.stack([ramp] * 3, -1), spec)[:, 0]
        self.assertTrue(np.all(np.diff(y) > 0))
        self.assertGreater(y[0], 0.0)  # deep shadows are not crushed to zero

    def test_split_tone_warms_highlights_and_cools_shadows(self):
        spec = LookSpec.from_dict({"split_tone": {"highlights": {"hue": 35, "strength": 0.2},
                                                  "shadows": {"hue": 190, "strength": 0.2}}})
        hi = apply_look(np.full(3, 1.5), spec)
        lo = apply_look(np.full(3, 0.01), spec)
        self.assertGreater(hi[0], hi[2])
        self.assertGreater(lo[2], lo[0])

    def test_shoulder_off_by_default(self):
        hi = np.array([[4.0, 1.0, 0.5], [0.02, 0.03, 0.05]])
        np.testing.assert_allclose(apply_look(hi, LookSpec()), hi, atol=1e-12)
        spec = LookSpec.from_dict({"shoulder": {"knee": 1.0, "compress": 0.0}})
        np.testing.assert_allclose(apply_look(hi, spec), hi, atol=1e-12)

    def test_shoulder_compresses_above_the_knee_only(self):
        spec = LookSpec.from_dict({"shoulder": {"knee": 1.0, "compress": 0.5, "width": 1.0, "max_weight": 0.0}})
        ramp = np.geomspace(1e-4, 200, 800)
        y = apply_look(np.stack([ramp] * 3, -1), spec)[:, 0]
        below = ramp <= 0.18 * 2 ** 1.0
        np.testing.assert_allclose(y[below], ramp[below], rtol=1e-12)
        self.assertTrue(np.all(np.diff(y) > 0))  # monotonic
        self.assertTrue(np.all(y[~below] < ramp[~below]))
        # far above the knee the log2 slope tends to 1 - compress
        hi = np.log2(y[-50:])
        slope = np.diff(hi) / np.diff(np.log2(ramp[-50:]))
        self.assertAlmostEqual(float(slope.mean()), 0.5, delta=0.02)

    def test_shoulder_keeps_ratios_and_pulls_back_saturated_channels(self):
        red = np.array([2.0, 0.05, 0.1])  # a bright, saturated projection red: low luma, hot R
        by_luma = apply_look(red, LookSpec.from_dict({"shoulder": {"knee": 2.0, "compress": 0.6,
                                                                   "max_weight": 0.0}}))
        by_max = apply_look(red, LookSpec.from_dict({"shoulder": {"knee": 2.0, "compress": 0.6,
                                                                  "max_weight": 1.0}}))
        np.testing.assert_allclose(by_luma, red, rtol=1e-9)  # luma is under the knee: untouched
        self.assertLess(by_max[0], red[0] * 0.9)
        np.testing.assert_allclose(by_max / by_max[0], red / red[0], rtol=1e-9)  # hue and saturation kept

    def test_shipped_looks_build(self):
        for f in sorted((REPO / "looks").glob("*.json")):
            spec = load_spec(f)
            self.assertTrue(spec.description)
            lut = build_lut(spec, 9)
            self.assertTrue(np.isfinite(lut).all())
            # mid grey stays near mid grey in DI (within half a stop)
            g = apply_dwg_di(np.full(3, float(di_encode(0.18))), spec)
            self.assertLess(abs(float(di_decode(g).mean()) / 0.18 - 1), 0.5, f.name)
            self.assertEqual(json.loads(f.read_text())["name"], f.stem)


if __name__ == "__main__":
    unittest.main()
