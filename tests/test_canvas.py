"""cf.canvas: canvas from style.json, reference-space scale, render bitrate, Super Scale plan."""

import json
import unittest
from pathlib import Path

from cf.canvas import (Canvas, for_reel, from_style, overlay_positions, overlay_style, parse_size, preset_name,
                       reference_size, render_bitrate_kbps, resolve, safe_zone, scaled_safe_zone, upscale_plan)

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
        self.assertEqual((z["top"], z["bottom"], z["left"], z["right"]), (538, 1344, 260, 260))
        self.assertEqual(z["right_rail"], {"width": 460, "from_y": 2300})
        self.assertEqual(scaled_safe_zone(STYLE, from_style(STYLE, "1080x1920"))["top"], 269)

    def test_bitrate_per_canvas(self):
        self.assertEqual(render_bitrate_kbps(STYLE, from_style(STYLE)), 45000)
        self.assertEqual(render_bitrate_kbps(STYLE, from_style(STYLE, "1080x1920")), 22000)
        with self.assertRaises(ValueError):
            render_bitrate_kbps(STYLE, Canvas(1440, 2560, 30))


class CanvasPresetTest(unittest.TestCase):
    def test_default_is_the_portrait_preset(self):
        c = resolve(STYLE)
        self.assertEqual((c.preset, c.name, c.landscape), ("portrait", "2160x3840", False))
        self.assertEqual(resolve(STYLE, "portrait"), c)

    def test_landscape_by_name_and_by_size(self):
        c = resolve(STYLE, "landscape")
        self.assertEqual((c.width, c.height, c.fps, c.reference_width, c.scale), (3840, 2160, 30, 1920, 2.0))
        self.assertTrue(c.landscape)
        self.assertEqual(preset_name(c), "cf-instagram-3840x2160")
        self.assertEqual(resolve(STYLE, "3840x2160"), c)
        hd = resolve(STYLE, "1920x1080")
        self.assertEqual((hd.preset, hd.scale), ("landscape", 1.0))
        # A WxH of the portrait aspect keeps the portrait geometry (the comparison render).
        self.assertEqual((resolve(STYLE, "1080x1920").preset, resolve(STYLE, "1080x1920").scale), ("portrait", 1.0))

    def test_unknown_name_or_aspect_fails(self):
        for bad in ("square", "1080x1350", "1081x1920"):
            with self.assertRaises(ValueError):
                resolve(STYLE, bad)

    def test_precedence_cli_over_script_over_style(self):
        self.assertEqual(for_reel(STYLE).preset, "portrait")
        self.assertEqual(for_reel(STYLE, "landscape").preset, "landscape")
        self.assertEqual(for_reel(STYLE, "landscape", "1080x1920").name, "1080x1920")
        self.assertEqual(for_reel(STYLE, None, "landscape").name, "3840x2160")

    def test_safe_zone_and_positions_follow_the_preset(self):
        land = resolve(STYLE, "landscape")
        z = safe_zone(STYLE, land)
        self.assertEqual((z["top"], z["bottom"], z["left"], z["right"]), (54, 130, 96, 96))
        self.assertNotIn("right_rail", z)
        # ~5 % margins, 12 % bottom band for the YouTube controls.
        self.assertAlmostEqual(z["left"] / 1920, 0.05, places=3)
        self.assertAlmostEqual(z["top"] / 1080, 0.05, places=3)
        self.assertAlmostEqual(z["bottom"] / 1080, 0.12, places=2)
        px = scaled_safe_zone(STYLE, land)
        self.assertEqual((px["top"], px["bottom"], px["left"], px["right"]), (108, 260, 192, 192))
        self.assertEqual(safe_zone(STYLE, resolve(STYLE)), STYLE["safe_zone"])
        self.assertEqual(overlay_positions(STYLE, resolve(STYLE)), STYLE["overlay_positions"])
        pos = overlay_positions(STYLE, land)
        self.assertEqual(pos["hook"]["anchor"], "center")
        self.assertGreater(pos["hook"]["y"], 1080 / 2)  # lower half (lower third, centre-ish)
        self.assertEqual((pos["place"]["anchor"], pos["place"]["x"]), ("bottom-left", 120))
        # Every landscape position and slot sits inside the safe zone (bottom anchors incl. the slide-in).
        slide = STYLE["animation"]["in"]["distance_px"]
        for name, p in list(pos.items()) + [(k, v) for k, v in land.slots.items() if k != "lower-left-loose"]:
            if name.startswith("_"):
                continue
            self.assertGreaterEqual(p["y"], z["top"], name)
            self.assertGreaterEqual(p.get("x", z["left"]), z["left"], name)
            if p["anchor"].startswith("bottom"):
                self.assertLessEqual(p["y"] + slide, 1080 - z["bottom"], name)

    def test_landscape_bitrate(self):
        self.assertEqual(render_bitrate_kbps(STYLE, resolve(STYLE, "landscape")), 45000)


class OverlayScaleTest(unittest.TestCase):
    def test_overlay_style_swaps_in_the_preset_geometry(self):
        o = overlay_style(STYLE, resolve(STYLE, "landscape"))
        self.assertEqual(o["canvas"], {"width": 3840, "height": 2160, "fps": 30, "reference_width": 1920,
                                       "preset": "landscape"})
        self.assertEqual(o["role_placement"], "overlay_positions")
        self.assertIn("lower-left", o["slots"])
        self.assertEqual(o["safe_zone"]["bottom"], 130)
        p = overlay_style(STYLE, resolve(STYLE))
        self.assertNotIn("role_placement", p)
        self.assertNotIn("slots", p)
        self.assertEqual(p["safe_zone"], STYLE["safe_zone"])

    def test_same_design_scale_on_both_4k_canvases(self):
        """designScale = width / reference_width: 2 on 2160x3840 and on 3840x2160, so a tiktok-hype
        hook is the same pixel size on both, i.e. the same fraction of the frame's short side."""
        port, land = resolve(STYLE), resolve(STYLE, "landscape")
        self.assertEqual(port.scale, land.scale)
        self.assertEqual(port.px(56), land.px(56))
        self.assertEqual(port.px(56) / min(port.width, port.height), land.px(56) / min(land.width, land.height))
        self.assertEqual(reference_size(land), (1920, 1080))
        self.assertEqual(reference_size(port), (1080, 1920))


class UpscalePlanTest(unittest.TestCase):
    def test_low_res_clips_get_2x_enhanced_on_4k(self):
        plan = {u.clip: u for u in upscale_plan(CLIPS, from_style(STYLE), ENHANCED)}
        hd = plan["HD.MOV"]
        self.assertEqual((hd.super_scale, hd.enhanced, hd.sharpness, hd.noise_reduction), (2, True, 0.5, 0.25))
        self.assertEqual(hd.set_args(), (2, 0.5, 0.25))  # the 4-argument form after the property name
        self.assertEqual(plan["UHD.MOV"].set_args(), (1,))
        self.assertEqual(plan["RAW.MOV"].super_scale, 2)
        self.assertEqual(plan["NOSIZE.MOV"].super_scale, 1)

    def test_4k_sources_are_not_upscaled_on_the_landscape_canvas(self):
        land = from_style(STYLE, "landscape")
        dji = {"DJI.MP4": {"display_width": 3840, "display_height": 2160}, "HD.MOV": {"display_height": 1080}}
        plan = {u.clip: u for u in upscale_plan(dji, land, STYLE)}
        self.assertEqual(plan["DJI.MP4"].set_args(), (1,))
        self.assertEqual(plan["HD.MOV"].super_scale, 2)  # a 1080p landscape clip would still get 2x

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
