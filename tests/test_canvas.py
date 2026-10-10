"""cf.canvas: canvas from style.json, reference-space scale, render bitrate, Super Scale plan."""

import json
import unittest
from pathlib import Path

from cf.canvas import (Canvas, from_style, parse_size, preset_name, render_bitrate_kbps, scaled_safe_zone,
                       upscale_plan)

STYLE = json.loads((Path(__file__).resolve().parents[1] / "style.json").read_text())
ENHANCED = dict(STYLE, upscale={"mode": "2x-enhanced", "sharpness": 0.5, "noise_reduction": 0.25})
CLIPS = {
    "HD.MOV": {"display_width": 1080, "display_height": 1920},
    "UHD.MOV": {"display_width": 2160, "display_height": 3840},
    "RAW.MOV": {"width": 1080, "height": 1920},  # no display_* keys: falls back to width/height
    "NOSIZE.MOV": {},
}


class CanvasTest(unittest.TestCase):
    def test_style_default_is_4k_vertical(self):
        c = from_style(STYLE)
        self.assertEqual((c.width, c.height, c.fps, c.reference_width), (2160, 3840, 30, 1080))
        self.assertEqual(c.scale, 2.0)
        self.assertEqual(preset_name(c), "cf-instagram-2160x3840")

    def test_override_keeps_fps(self):
        c = from_style(STYLE, "1080x1920")
        self.assertEqual((c.width, c.height, c.fps, c.scale), (1080, 1920, 30, 1.0))
        self.assertEqual(preset_name(c), "cf-instagram-1080x1920")

    def test_parse_size(self):
        self.assertEqual(parse_size("2160x3840"), (2160, 3840))
        self.assertEqual(parse_size(" 1080 X 1920 "), (1080, 1920))
        for bad in ("1080", "1080x", "1081x1920", "0x1920", "axb"):
            with self.assertRaises(ValueError):
                parse_size(bad)

    def test_safe_zone_scales_from_reference(self):
        z = scaled_safe_zone(STYLE, from_style(STYLE))
        self.assertEqual((z["top"], z["bottom"], z["left"], z["right"]), (538, 1344, 130, 130))
        self.assertEqual(z["right_rail"], {"width": 460, "from_y": 2300})
        self.assertEqual(scaled_safe_zone(STYLE, from_style(STYLE, "1080x1920"))["top"], 269)

    def test_bitrate_per_canvas(self):
        self.assertEqual(render_bitrate_kbps(STYLE, from_style(STYLE)), 45000)
        self.assertEqual(render_bitrate_kbps(STYLE, from_style(STYLE, "1080x1920")), 22000)
        with self.assertRaises(ValueError):
            render_bitrate_kbps(STYLE, Canvas(1440, 2560, 30))


class UpscalePlanTest(unittest.TestCase):
    def test_low_res_clips_get_2x_enhanced_on_4k(self):
        plan = {u.clip: u for u in upscale_plan(CLIPS, from_style(STYLE), ENHANCED)}
        hd = plan["HD.MOV"]
        self.assertEqual((hd.super_scale, hd.enhanced, hd.sharpness, hd.noise_reduction), (2, True, 0.5, 0.25))
        self.assertEqual(hd.set_args(), (2, 0.5, 0.25))  # the 4-argument form after the property name
        self.assertEqual(plan["UHD.MOV"].set_args(), (1,))
        self.assertEqual(plan["RAW.MOV"].super_scale, 2)
        self.assertEqual(plan["NOSIZE.MOV"].super_scale, 1)

    def test_nothing_upscaled_on_1080_canvas_or_when_disabled(self):
        self.assertTrue(all(u.super_scale == 1 for u in upscale_plan(CLIPS, from_style(STYLE, "1080x1920"), STYLE)))
        self.assertTrue(all(u.set_args() == (1,) for u in upscale_plan(CLIPS, from_style(STYLE), STYLE,
                                                                       enabled=False)))

    def test_plain_2x_mode_and_validation(self):
        self.assertEqual(STYLE["upscale"]["mode"], "2x")  # style.json default since 2026-10-11 (render time)
        hd = {u.clip: u for u in upscale_plan(CLIPS, from_style(STYLE), STYLE)}["HD.MOV"]
        self.assertEqual((hd.set_args(), hd.enhanced, hd.sharpness), ((2,), False, None))
        with self.assertRaises(ValueError):
            upscale_plan(CLIPS, from_style(STYLE), dict(STYLE, upscale={"mode": "4x"}))
        with self.assertRaises(ValueError):
            upscale_plan(CLIPS, from_style(STYLE), dict(STYLE, upscale={"sharpness": 1.5}))


if __name__ == "__main__":
    unittest.main()
