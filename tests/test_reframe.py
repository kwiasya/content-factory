"""Reframe math (cf.reframe), its Script validation and cf.build.plan_reframes. No Resolve."""

import json
import unittest
from pathlib import Path

import numpy as np

from cf.build import BuildError, black_band, find_window, plan_reframes, proxy_frame_stats
from cf.reframe import (Reframe, aspect_relation, base_scale, default_mode, default_reframe, plan_reframe,
                        zoom_to_hide_band)
from cf.script_schema import ScriptError, from_dict, validate

ROOT = Path(__file__).resolve().parents[1]
STYLE = json.loads((ROOT / "style.json").read_text())
CW, CH = 2160, 3840
MANIFEST = {
    "walk": "w",
    "clips": [
        {"file": "DJI.mp4", "fps": 29.97, "duration_s": 100.0, "width": 3840, "height": 2160,
         "display_width": 3840, "display_height": 2160},
        {"file": "IPH.MOV", "fps": 60.0, "duration_s": 30.0, "width": 1920, "height": 1080, "rotation": -180,
         "display_width": 1920, "display_height": 1080},
        {"file": "PORT.MOV", "fps": 30.0, "duration_s": 30.0, "width": 1920, "height": 1080, "rotation": -90,
         "display_width": 1080, "display_height": 1920},
        {"file": "SQ.mov", "fps": 30.0, "duration_s": 30.0, "width": 1080, "height": 1080,
         "display_width": 1080, "display_height": 1080},
    ],
}


def script(shots, ending="reveal_last"):
    return from_dict({
        "schema": "cf-script/1", "walk": "w", "concept": "c", "format": "pov", "target_length_s": 2.5 * len(shots),
        "hook": {"type": "pov", "text": "one two three four five", "clip": shots[0]["clip"]},
        "shots": shots, "ending": ending, "location_tag": "x",
    })


def shot(clip, a, b, **kw):
    return {"clip": clip, "in_s": a, "out_s": b, "role": kw.pop("role", "build"), **kw}


class ZoomPanMathTest(unittest.TestCase):
    def test_dji_4k_fit_height(self):
        p = plan_reframe(Reframe("center"), 3840, 2160, CW, CH)
        self.assertAlmostEqual(p.scale, 3840 / 2160, places=5)        # x1.78 upscale
        self.assertAlmostEqual(p.base_scale, 2160 / 3840)             # Resolve's fit width
        self.assertAlmostEqual(p.zoom_x, (16 / 9) ** 2, places=9)     # 3.1605
        self.assertEqual((p.window_w, p.window_h), (1215.0, 2160.0))  # 9:16 window of the source
        self.assertAlmostEqual(p.pan_range, (3840 * 3840 / 2160 - 2160) / 2, places=3)  # 2333.33
        self.assertEqual(p.pan, 0.0)
        self.assertEqual(p.window_x0, (3840 - 1215) / 2)

    def test_iphone_1080p_fit_height(self):
        p = plan_reframe(Reframe("center"), 1920, 1080, CW, CH)
        self.assertAlmostEqual(p.scale, 3840 / 1080, places=5)        # x3.56 upscale
        self.assertAlmostEqual(p.zoom_x, (16 / 9) ** 2, places=9)     # same ZoomX: same aspect
        self.assertEqual((p.window_w, p.window_h), (607.5, 1080.0))
        self.assertAlmostEqual(p.pan_range, 2333.3333, places=3)      # same canvas-px range

    def test_pan_x_maps_to_canvas_pixels_and_window(self):
        # Pan > 0 moves the image right (probe: Pan 500 shifted the still 500 px right),
        # so the left part of the source (x < 0) needs a positive Pan.
        p = plan_reframe(Reframe("pan", x=-0.6), 3840, 2160, CW, CH)
        self.assertAlmostEqual(p.pan, 1400.0, places=3)
        self.assertAlmostEqual(p.window_x0, 525.0, places=2)
        left = plan_reframe(Reframe("pan", x=-1), 3840, 2160, CW, CH)
        right = plan_reframe(Reframe("pan", x=1), 3840, 2160, CW, CH)
        self.assertAlmostEqual(left.window_x0, 0.0, places=2)
        self.assertAlmostEqual(right.window_x0 + right.window_w, 3840.0, places=2)
        self.assertAlmostEqual(left.pan, -right.pan)
        ip = plan_reframe(Reframe("pan", x=0.4), 1920, 1080, CW, CH)
        self.assertAlmostEqual(ip.pan, -933.3333, places=3)
        self.assertAlmostEqual(ip.window_x0, (1920 - 607.5) / 2 + 0.4 * (1920 - 607.5) / 2, places=2)

    def test_extra_zoom_narrows_the_window_and_widens_the_range(self):
        p = plan_reframe(Reframe("pan", x=1, zoom=1.5), 3840, 2160, CW, CH)
        self.assertAlmostEqual(p.zoom_x, (16 / 9) ** 2 * 1.5, places=9)
        self.assertEqual((p.window_w, p.window_h), (810.0, 1440.0))
        self.assertAlmostEqual(p.window_x0 + p.window_w, 3840.0, places=2)  # x=1 still ends at the edge

    def test_zoom_depends_on_the_timelines_input_scaling(self):
        self.assertAlmostEqual(plan_reframe(Reframe("center"), 3840, 2160, CW, CH, "scaleToCrop").zoom_x, 1.0)
        self.assertAlmostEqual(plan_reframe(Reframe("center"), 3840, 2160, CW, CH, "centerCrop").zoom_x,
                               3840 / 2160, places=6)
        with self.assertRaises(ValueError):
            base_scale(3840, 2160, CW, CH, "stretch")

    def test_x_end_is_recorded_not_animated(self):
        p = plan_reframe(Reframe("pan", x=-0.5, x_end=0.5), 3840, 2160, CW, CH)
        self.assertAlmostEqual(p.pan, 1166.6667, places=3)
        self.assertAlmostEqual(p.pan_end, -1166.6667, places=3)
        self.assertTrue(any("not animated" in n for n in p.notes))
        same = plan_reframe(Reframe("pan", x=0.4, x_end=0.4), 3840, 2160, CW, CH)
        self.assertFalse(any("not animated" in n for n in same.notes))

    def test_smart_writes_pan_zero(self):
        p = plan_reframe(Reframe("smart"), 3840, 2160, CW, CH)
        self.assertEqual((p.pan, p.x), (0.0, None))

    def test_only_sources_wider_than_the_canvas(self):
        for w, h in ((1080, 1920), (2160, 3840), (1080, 2400)):
            with self.assertRaises(ValueError):
                plan_reframe(Reframe("center"), w, h, CW, CH)


class SmartBandTest(unittest.TestCase):
    def test_zoom_to_hide_band_matches_the_probe(self):
        # Probe 2026-10-11 (DJI 4K, one shot): black 455 px at zoom 1.0, 235 at 1.15, 15 at 1.3.
        self.assertEqual(zoom_to_hide_band(455, 3840, 1.0), 1.35)
        self.assertEqual(zoom_to_hide_band(235, 3840, 1.15), 1.35)
        self.assertEqual(zoom_to_hide_band(0, 3840, 1.2), 1.2)
        self.assertIsNone(zoom_to_hide_band(1920, 3840, 1.0))

    def test_black_band_counts_edge_rows_and_columns(self):
        a = np.full((100, 60, 3), 90, np.uint8)
        a[:7] = 0
        a[-20:] = 1
        a[:, :3] = 0
        a[50, 30] = 0  # a black pixel inside is not a band
        self.assertEqual(black_band(a), {"top": 7, "bottom": 20, "left": 3, "right": 0})

    def test_find_window_locates_a_pan_window_on_the_proxy(self):
        import cv2

        rng = np.random.default_rng(1)
        src = cv2.resize(rng.integers(0, 255, (54, 96, 3), dtype=np.uint8), (1920, 1080),
                         interpolation=cv2.INTER_CUBIC)
        proxy = cv2.resize(src, (960, 540), interpolation=cv2.INTER_AREA)
        cw, ch = 540, 960  # a small 9:16 canvas keeps the test fast
        for x in (-0.6, 0.0, 0.4):
            p = plan_reframe(Reframe("pan", x=x), 1920, 1080, cw, ch)
            x0 = round(p.window_x0)
            still = cv2.resize(src[:, x0:x0 + round(p.window_w)], (cw, ch), interpolation=cv2.INTER_CUBIC)
            win = find_window(still[..., ::-1].copy(), proxy, p, 1920, 1080)
            self.assertLessEqual(abs(win["x0_src"] - p.window_x0), win["tolerance_src"], (x, win))
            self.assertAlmostEqual(win["x"], x, delta=0.02)
            self.assertGreater(win["score"], 0.9)

    def test_proxy_stats_of_the_window_band(self):
        f = np.zeros((10, 100, 3), np.uint8)
        f[:, 40:60] = 200
        st = proxy_frame_stats(None, 1.0, f, (0.4, 0.2))
        self.assertEqual((st["width"], st["crop_px"], st["mean_luma"]), (20, [40, 60], 200.0))


class DefaultsTest(unittest.TestCase):
    def test_landscape_on_portrait_is_follow_portrait_is_none(self):
        self.assertEqual(default_reframe(3840, 2160, CW, CH), Reframe("follow"))
        self.assertEqual(default_reframe(1920, 1080, CW, CH, "smart"), Reframe("smart"))
        self.assertEqual(default_mode(STYLE), "follow")
        self.assertEqual(default_mode({}), "follow")
        self.assertIsNone(default_reframe(1080, 1920, CW, CH))
        self.assertIsNone(default_reframe(None, None, CW, CH))
        self.assertIsNone(default_reframe(3840, 2160, 1920, 1080))  # landscape canvas
        self.assertEqual(aspect_relation(1080, 1080, CW, CH), "wider")  # a square clip is wider than 9:16
        self.assertEqual(aspect_relation(1088, 1920, 1080, 1920), "same")

    def test_plan_reframes_defaults_and_explicit(self):
        sc = script([shot("DJI.mp4", 1, 3.5), shot("PORT.MOV", 1, 3.5), shot("IPH.MOV", 1, 3.5,
                     reframe={"mode": "pan", "x": 0.4})])
        with self.assertRaises(BuildError):  # follow without a person analysis
            plan_reframes(sc, MANIFEST, CW, CH)
        plans = plan_reframes(sc, MANIFEST, CW, CH, follow_x={"s01": -0.5})
        self.assertEqual((plans["s01"].mode, plans["s01"].x), ("follow", -0.5))
        self.assertAlmostEqual(plans["s01"].pan, 1166.6667, places=3)
        self.assertTrue(plans["s01"].default)
        self.assertEqual(plan_reframes(sc, MANIFEST, CW, CH, default_mode="smart")["s01"].mode, "smart")
        self.assertIsNone(plans["s02"])
        self.assertEqual((plans["s03"].mode, plans["s03"].default), ("pan", False))
        self.assertAlmostEqual(plans["s03"].pan, -933.3333, places=3)

    def test_plan_reframes_refuses_reframe_on_a_portrait_clip(self):
        sc = script([shot("PORT.MOV", 1, 3.5, reframe={"mode": "center"})])
        with self.assertRaises(BuildError):
            plan_reframes(sc, MANIFEST, CW, CH)


class ValidatorTest(unittest.TestCase):
    def problems(self, reframe, clip="DJI.mp4"):
        return validate(script([shot(clip, 1, 3.5, reframe=reframe)]), MANIFEST, STYLE)

    def test_valid_reframes(self):
        for r in ({"mode": "smart"}, {"mode": "center"}, {"mode": "pan", "x": -0.6},
                  {"mode": "pan", "x": 0.4, "x_end": -1}, {"mode": "smart", "zoom": 1.2}, None):
            self.assertEqual(self.problems(r), [], r)
        self.assertEqual(self.problems({"mode": "pan", "x": 1}, clip="IPH.MOV"), [])

    def test_pan_requires_x_and_x_is_pan_only(self):
        self.assertTrue(any("requires 'x'" in p for p in self.problems({"mode": "pan"})))
        self.assertTrue(any("only for mode 'pan'" in p for p in self.problems({"mode": "center", "x": 0.2})))
        self.assertTrue(any("only for mode 'pan'" in p for p in self.problems({"mode": "smart", "x_end": 0.2})))

    def test_ranges_and_enum(self):
        self.assertTrue(any("-1..1" in p for p in self.problems({"mode": "pan", "x": -1.2})))
        self.assertTrue(any("-1..1" in p for p in self.problems({"mode": "pan", "x": 0, "x_end": 2})))
        self.assertTrue(any(">= 1" in p for p in self.problems({"mode": "center", "zoom": 0.8})))
        self.assertTrue(any("not in" in p for p in self.problems({"mode": "track"})))
        self.assertTrue(any("not set by hand" in p for p in self.problems({"mode": "follow", "x": 0.2})))
        self.assertEqual(self.problems({"mode": "follow", "zoom": 1.2}), [])

    def test_only_when_the_aspect_differs(self):
        self.assertTrue(any("aspect" in p for p in self.problems({"mode": "center"}, clip="PORT.MOV")))
        self.assertEqual(self.problems({"mode": "smart"}, clip="SQ.mov"), [])  # 1:1 is wider than 9:16
        # Without a manifest only the field rules run.
        sc = script([shot("PORT.MOV", 1, 3.5, reframe={"mode": "center"})])
        self.assertEqual([p for p in validate(sc, None, STYLE) if "reframe" in p], [])

    def test_structure(self):
        for bad in ("smart", {"mode": 1}, {"mode": "pan", "x": "left"}, {"mode": "pan", "x": 0, "y": 0},
                    {"mode": "pan", "x": True}):
            with self.assertRaises(ScriptError, msg=bad):
                script([shot("DJI.mp4", 1, 3.5, reframe=bad)])
        r = script([shot("DJI.mp4", 1, 3.5, reframe={"mode": "pan", "x": -1})]).shots[0].reframe
        self.assertEqual(r, Reframe("pan", x=-1.0, x_end=None, zoom=1.0))

    def test_seamless_loop_window_must_not_jump(self):
        def loop(first_rf, last_rf):
            first = shot("DJI.mp4", 10, 12.5, role="hook", **({"reframe": first_rf} if first_rf else {}))
            last = shot("DJI.mp4", 8, 10, role="loop", **({"reframe": last_rf} if last_rf else {}))
            return [p for p in validate(script([first, shot("IPH.MOV", 1, 3.5), last], "loop_seamless"),
                                        MANIFEST, STYLE) if "seam" in p]
        self.assertEqual(loop(None, None), [])                                  # both default follow
        self.assertEqual(loop({"mode": "follow"}, None), [])                    # explicit = default
        self.assertTrue(loop({"mode": "smart"}, None))                          # smart vs default follow
        self.assertEqual(loop({"mode": "pan", "x": 0.2}, {"mode": "pan", "x": -0.4, "x_end": 0.2}), [])
        self.assertTrue(loop({"mode": "pan", "x": 0.2}, {"mode": "pan", "x": -0.4}))
        self.assertTrue(loop({"mode": "center"}, None))
        self.assertTrue(loop({"mode": "center", "zoom": 1.2}, {"mode": "center"}))


if __name__ == "__main__":
    unittest.main()
