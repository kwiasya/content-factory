"""Meme cut (cf.memecut): placement maths, Script validation (pacing, key words, text size, safe zone), the match
rule, the plan, and a small end-to-end compose."""

import json
import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from cf import memecut as mc
from cf import render_check as rc
from cf.canvas import Canvas

W, H = 2160, 3840
HAVE_FFMPEG = bool(shutil.which("ffmpeg") and shutil.which("ffprobe"))


def profile() -> dict:
    return json.loads(mc.PROFILE_PATH.read_text(encoding="utf-8"))


def script() -> dict:
    """The approved "Потсдам — effortless" cut (2026-10-19) as a cf-memecut/1 Script: 7.0 s, no finale."""
    return {
        "schema": "cf-memecut/1",
        "title": "Потсдам — effortless",
        "reference": "TikTok @malyshka894 \"looked vs felt\"",
        "situation": "сборы",
        "setup": {"footage": "potsdam-2026-10-04", "clip": "IMG_1621.mov", "in_s": 19.6, "dur_s": 2.5,
                  "text": "everyone: your outfits\nalways look so {effortless}",
                  "anchor": {"anchor": "top-center", "y": 470, "align": "center"}},
        "punch": {"text": "me {1 hour before} leaving:"},
        "inserts": [
            {"ref": "@meme/frantic-try-on-boutique", "in_s": 0.4, "dur_s": 1.0,
             "shows": "two women frantically holding dresses up against themselves"},
            {"ref": "@meme/throwing-clothes-out-of-closet", "in_s": 0.3, "dur_s": 1.0,
             "trim": {"top": 10, "bottom": 110}, "shows": "a woman flinging clothes out of the closet"},
            {"ref": "@meme/closet-clothes-flying", "in_s": 0.6, "dur_s": 1.0, "trim": {"top": 20, "bottom": 100},
             "shows": "a girl in a walk-in closet throwing clothes everywhere"},
            {"ref": "@meme/confused-travolta", "in_s": 0.4, "dur_s": 1.5,
             "shows": "Travolta standing lost with a coat: still nothing to wear"},
        ],
        "ending": "last_meme",
        "caption": "my closet still hasn't recovered from this look 💅",
        "hashtags": ["#potsdam", "#outfit", "#getreadywithme", "#relatable", "#girlhumor"],
        "location_tag": "Schloss Cecilienhof, Potsdam",
    }


def old_script() -> dict:
    """The published "Свидание — мой мозг" cut (2026-10-15): a Script from before v2, with a finale."""
    return {
        "schema": "cf-memecut/1",
        "title": "Свидание — мой мозг",
        "situation": "свидание",
        "setup": {"walk": "garden-2026-08-30", "clip": "IMG_8645.MOV", "in_s": 19.75, "dur_s": 2.467,
                  "text": "🔵: you're so calm\nbefore a first date"},
        "punch": {"text": "my brain:"},
        "inserts": [
            {"ref": "@meme/kermit-panic", "in_s": 0.3, "dur_s": 0.9, "shows": "kermit biting his nails"},
            {"ref": "@meme/monkey-laptop", "in_s": 1.05, "dur_s": 0.9, "shows": "a baboon typing"},
            {"ref": "@meme/cillian-murphy-stare", "in_s": 4.4, "dur_s": 0.9, "shows": "a blank stare"},
            {"ref": "@meme/man-throwing-papers", "in_s": 0.25, "dur_s": 0.9, "shows": "papers flying",
             "trim": {"right": 140, "top": 60, "bottom": 80}},
            {"ref": "@meme/spongebob-burning-office", "in_s": 2.0, "dur_s": 0.9, "shows": "an office on fire",
             "trim": {"top": 8, "bottom": 8}},
        ],
        "finale": {"ref": "@meme/stock-explosion-mushroom-cloud", "in_s": 7.8, "dur_s": 1.2},
        "ending": "reveal_last",
        "caption": "the date was fine btw 🙂",
        "hashtags": ["#berlin", "#dating", "#relatable", "#berlinlife", "#memes"],
        "location_tag": "Berlin",
    }


def problems(s: dict) -> list[str]:
    return mc.validate(s, profile()).problems


def warnings(s: dict) -> list[str]:
    return mc.validate(s, profile()).warnings


class PlacementTest(unittest.TestCase):
    def assert_no_stretch(self, p: mc.Placement, canvas=(W, H)) -> None:
        cw, ch = p.crop.w, p.crop.h

        def within_a_pixel(r, aspect):
            # the box's aspect differs from the wanted one by less than one pixel of its shorter side
            self.assertLessEqual(abs(r.w / r.h - aspect) / aspect, 1.0 / min(r.w, r.h))

        if p.fit == "blur-fill":
            within_a_pixel(p.fg, cw / ch)  # the foreground keeps the trimmed source's aspect
        within_a_pixel(p.window, canvas[0] / canvas[1])  # fill picture / blur background: the canvas aspect
        # and lies inside the trimmed source
        self.assertGreaterEqual(p.window.x, 0)
        self.assertGreaterEqual(p.window.y, 0)
        self.assertLessEqual(p.window.x + p.window.w, cw)
        self.assertLessEqual(p.window.y + p.window.h, ch)

    def test_low_res_landscape_meme_sits_at_full_width_centred_over_blur(self):
        p = mc.place(480, 270, W, H)
        self.assertEqual(p.fit, "blur-fill")
        self.assertEqual((p.fg.x, p.fg.w, p.fg.h), (0, 2160, 1215))
        self.assertEqual(p.fg.y, (H - 1215) // 2)
        self.assertEqual(p.crop, mc.Rect(0, 0, 480, 270))
        self.assertAlmostEqual(p.upscale, 4.5)
        self.assert_no_stretch(p)

    def test_blur_background_is_a_zoomed_centred_canvas_window(self):
        p = mc.place(480, 270, W, H, bg_zoom=1.2)
        # cover window of 480x270 at 9:16 is 152x270; zoomed 1.2 it is 127x225 (rounded), centred
        self.assertEqual((p.window.w, p.window.h), (127, 225))
        self.assertEqual((p.window.x, p.window.y), ((480 - 127) // 2, (270 - 225) // 2))
        self.assert_no_stretch(p)

    def test_4k_stock_shot_fills_the_frame_with_a_centred_crop(self):
        p = mc.place(3840, 2160, W, H)
        self.assertEqual(p.fit, "fill")
        self.assertIsNone(p.fg)
        self.assertEqual((p.window.w, p.window.h), (1215, 2160))
        self.assertIn(p.window.x, (1312, 1313))
        self.assertAlmostEqual(p.upscale, 3840 / 2160, places=3)
        self.assert_no_stretch(p)

    def test_auto_fit_needs_a_short_side_as_large_as_the_canvas(self):
        self.assertEqual(mc.choose_fit(480, 270, W, H), "blur-fill")
        self.assertEqual(mc.choose_fit(1080, 1080, W, H), "blur-fill")
        self.assertEqual(mc.choose_fit(1080, 1920, W, H), "blur-fill")
        self.assertEqual(mc.choose_fit(3840, 2160, W, H), "fill")
        self.assertEqual(mc.choose_fit(2160, 3840, W, H), "fill")

    def test_explicit_fit_wins_over_auto(self):
        self.assertEqual(mc.place(480, 270, W, H, fit="fill").fit, "fill")
        self.assertEqual(mc.place(3840, 2160, W, H, fit="blur-fill").fit, "blur-fill")

    def test_trim_removes_an_edge_watermark_from_foreground_and_background(self):
        # this-is-fine: the [adult swim] bug sits in the right 15 % (72 px of 480)
        p = mc.place(480, 270, W, H, trim={"right": 72})
        self.assertEqual(p.crop, mc.Rect(0, 0, 408, 270))
        self.assertEqual((p.fg.w, p.fg.h), (2160, round(2160 * 270 / 408)))
        # the background window is cut from the trimmed picture, so the bug is in neither
        self.assertLessEqual(p.crop.x + p.window.x + p.window.w, 480 - 72)
        self.assert_no_stretch(p)
        f = mc.place(480, 270, W, H, fit="fill", trim={"right": 72})
        self.assertLessEqual(f.crop.x + f.window.x + f.window.w, 480 - 72)
        self.assert_no_stretch(f)

    def test_trim_all_edges(self):
        p = mc.place(1080, 1080, W, H, trim={"right": 140, "top": 60, "bottom": 80})
        self.assertEqual(p.crop, mc.Rect(0, 60, 940, 940))
        self.assert_no_stretch(p)

    def test_a_source_taller_than_the_canvas_fits_by_height(self):
        p = mc.place(500, 1200, W, H)
        self.assertEqual(p.fit, "blur-fill")
        self.assertEqual((p.fg.h, p.fg.w), (3840, 1600))
        self.assertEqual(p.fg.x, (W - 1600) // 2)
        self.assert_no_stretch(p)

    def test_never_stretch_over_many_sizes(self):
        sizes = [(240, 196), (440, 300), (450, 450), (472, 480), (852, 462), (1920, 1080), (1080, 1920),
                 (3840, 2160), (4096, 2160), (720, 1280), (300, 1000), (1001, 333)]
        for (w, h) in sizes:
            for fit in ("blur-fill", "fill"):
                for trim in (None, {"left": 7}, {"bottom": 11, "right": 3}):
                    for canvas in ((W, H), (1080, 1920), (216, 384)):
                        with self.subTest(size=(w, h), fit=fit, trim=trim, canvas=canvas):
                            self.assert_no_stretch(mc.place(w, h, *canvas, fit=fit, trim=trim), canvas)

    def test_bad_trims_are_refused(self):
        for trim in ({"left": -1}, {"right": 480}, {"left": 300, "right": 200}, {"top": 1.5}, {"middle": 3},
                     {"top": True}, "right"):
            with self.subTest(trim=trim), self.assertRaises(ValueError):
                mc.place(480, 270, W, H, trim=trim)

    def test_unknown_fit_is_refused(self):
        with self.assertRaises(ValueError):
            mc.place(480, 270, W, H, fit="stretch")


class ValidateTest(unittest.TestCase):
    def test_the_approved_cut_is_valid_and_quiet(self):
        self.assertEqual(problems(script()), [])
        self.assertEqual(warnings(script()), [])

    def test_durations_are_counted_in_frames(self):
        r = mc.validate(script(), profile())
        self.assertEqual(r.frames["setup"], 75)
        self.assertEqual(r.frames["inserts"], [30, 30, 30, 45])
        self.assertNotIn("finale", r.frames)
        self.assertEqual(r.frames["total"], 210)  # 7.0 s

    def test_insert_duration_outside_the_range(self):
        for dur in (0.7, 1.3):
            s = script()
            s["inserts"][1]["dur_s"] = dur
            with self.subTest(dur=dur):
                self.assertTrue(any("inserts[1]" in p and "dur_s" in p for p in problems(s)), problems(s))

    def test_the_last_insert_holds_one_to_one_and_a_half_seconds(self):
        for dur, ok in ((0.9, False), (1.0, True), (1.5, True), (1.6, False)):
            s = script()
            s["inserts"][-1]["dur_s"] = dur
            s["setup"]["dur_s"] = 3.0  # keep the total in range
            with self.subTest(dur=dur):
                got = [p for p in problems(s) if "inserts[3]" in p]
                self.assertEqual(not got, ok, got)

    def test_insert_count(self):
        for n, ok in ((2, False), (3, True), (6, True), (7, False)):
            s = script()
            s["inserts"] = [dict(s["inserts"][0]) for _ in range(n - 1)] + [dict(s["inserts"][-1])]
            with self.subTest(n=n):
                got = [p for p in problems(s) if p.startswith("inserts:")]
                self.assertEqual(not got, ok, got)

    def test_each_insert_says_what_it_shows(self):
        s = script()
        del s["inserts"][1]["shows"]
        self.assertTrue(any("inserts[1]" in p and "shows" in p for p in problems(s)))

    def test_no_finale_is_the_default_and_an_old_finale_still_validates_with_a_warning(self):
        old = old_script()
        self.assertEqual(problems(old), [])
        self.assertTrue(any("finale" in w and "deprecated" in w for w in warnings(old)), warnings(old))
        r = mc.validate(old, profile())
        # with a finale the last insert is an ordinary one (0.9 s is fine)
        self.assertEqual(r.frames["inserts"], [27] * 5)
        self.assertEqual(r.frames["finale"], 36)
        self.assertEqual(r.frames["total"], 245)
        old["finale"]["dur_s"] = 2.0
        self.assertTrue(any("finale" in p and "dur_s" in p for p in problems(old)))

    def test_setup_length(self):
        for dur in (2.0, 3.4):
            s = script()
            s["setup"]["dur_s"] = dur
            with self.subTest(dur=dur):
                self.assertTrue(any("setup" in p and "dur_s" in p for p in problems(s)))

    def test_total_length(self):
        s = script()  # 3.0 + 5 x 1.2 + 1.5 = 10.5 s
        s["setup"]["dur_s"] = 3.0
        s["inserts"] = [dict(s["inserts"][0], dur_s=1.2) for _ in range(5)] + [s["inserts"][-1]]
        self.assertTrue(any("total" in p for p in problems(s)), problems(s))
        s = script()  # 2.3 + 2 x 0.8 + 1.0 = 4.9 s
        s["setup"]["dur_s"] = 2.3
        s["inserts"] = [dict(s["inserts"][0], dur_s=0.8) for _ in range(2)] + [dict(s["inserts"][-1], dur_s=1.0)]
        got = problems(s)
        self.assertTrue(any("total" in p and "inserts" in p for p in got), got)

    def test_text_is_english_lowercase_and_short(self):
        cases = [("setup", "You're So {Calm}"), ("punch", "мой {мозг}:"),
                 ("punch", "this is how my poor {brain} actually felt:")]
        for part, text in cases:
            s = script()
            s[part]["text"] = text
            with self.subTest(text=text):
                self.assertTrue(any(part in p and "text" in p for p in problems(s)), problems(s))

    def test_at_most_one_emoji_on_screen(self):
        s = script()
        s["setup"]["text"] = "everyone: your outfits always look so {effortless} ✨"
        self.assertEqual(problems(s), [])
        s["punch"]["text"] = "me {1 hour before} leaving: 😭"
        self.assertTrue(any("emoji" in p for p in problems(s)), problems(s))

    def test_no_cta_no_alt_text_and_short_caption(self):
        for key, value in (("cta", "send this to a friend"), ("alt_text", "a girl in an alley")):
            s = script()
            s[key] = value
            with self.subTest(key=key):
                self.assertTrue(any(key in p for p in problems(s)))
        s = script()
        s["hashtags"].append("#six")
        self.assertTrue(any("hashtags" in p for p in problems(s)))
        s = script()
        s["caption"] = "line one\nline two"
        self.assertTrue(any("caption" in p for p in problems(s)))
        s = script()
        s["location_tag"] = ""
        self.assertTrue(any("location_tag" in p for p in problems(s)))

    def test_ending_is_last_meme_and_reveal_last_is_its_old_name(self):
        for ending, ok in (("last_meme", True), ("reveal_last", True), ("loop_seamless", False)):
            s = script()
            s["ending"] = ending
            with self.subTest(ending=ending):
                self.assertEqual(not [p for p in problems(s) if "ending" in p], ok)
        s = script()
        del s["ending"]
        self.assertEqual(problems(s), [])

    def test_a_reference_is_named(self):
        s = script()
        del s["reference"]
        self.assertTrue(any("reference" in w for w in warnings(s)))
        s["concept"] = "adapted from TikTok @malyshka894"
        self.assertFalse(any("reference" in w for w in warnings(s)))
        s["reference"] = ""
        self.assertTrue(any("reference" in p for p in problems(s)))

    def test_the_setup_names_its_footage_and_the_legacy_walk_still_reads(self):
        s = script()
        s["setup"]["walk"] = s["setup"].pop("footage")
        self.assertEqual(problems(s), [])
        self.assertEqual(mc.setup_footage(s["setup"]), "potsdam-2026-10-04")
        s["setup"]["footage"] = "garden-2026-08-30"
        self.assertTrue(any("footage and walk differ" in p for p in problems(s)))
        del s["setup"]["footage"], s["setup"]["walk"]
        self.assertTrue(any(p.startswith("setup.footage: required") for p in problems(s)))

    def test_the_setup_clip_is_read_from_the_footage_under_the_local_root(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / "potsdam-2026-10-04").mkdir()
            clip = root / "potsdam-2026-10-04" / "raw" / "IMG_1621.mov"
            (root / "potsdam-2026-10-04" / "clip_manifest.json").write_text(json.dumps(
                {"footage": "potsdam-2026-10-04", "clips": [{"file": "IMG_1621.mov", "path": str(clip)}]}))
            for key in ("footage", "walk"):
                with self.subTest(key=key):
                    self.assertEqual(mc.setup_source(root, {key: "potsdam-2026-10-04", "clip": "IMG_1621.mov"}), clip)
            with self.assertRaisesRegex(mc.MemecutError, "ingest-footage"):
                mc.setup_source(root, {"footage": "missing", "clip": "IMG_1621.mov"})

    def test_fit_and_trim_are_checked(self):
        s = script()
        s["inserts"][0]["fit"] = "stretch"
        s["inserts"][1]["trim"] = {"left": -4}
        got = problems(s)
        self.assertTrue(any("inserts[0]" in p and "fit" in p for p in got))
        self.assertTrue(any("inserts[1]" in p and "trim" in p for p in got))


class KeyWordTest(unittest.TestCase):
    def test_marks_strip_to_plain_text(self):
        self.assertEqual(mc.plain("look so {effortless}"), "look so effortless")
        self.assertEqual(mc.plain("me {1 hour\nbefore|yellow} leaving:"), "me 1 hour\nbefore leaving:")

    def test_a_bare_mark_takes_the_lines_default_colour(self):
        self.assertEqual(mc.key_text("look so {effortless}", "pink"), "look so {effortless|pink}")
        self.assertEqual(mc.key_text("me {1 hour|cyan} before", "yellow"), "me {1 hour|cyan} before")

    def test_one_key_word_in_the_whole_text(self):
        s = script()
        s["setup"]["text"] = "everyone: your {outfits} always look so {effortless}"
        self.assertTrue(any("setup" in p and "key words" in p for p in problems(s)), problems(s))
        s["setup"]["text"] = "everyone: your {outfits}\nalways look so {effortless}"   # one per line is still two
        self.assertTrue(any("setup" in p and "key words" in p for p in problems(s)), problems(s))
        s["setup"]["text"] = "everyone: your outfits\nalways look so {effortless}"
        self.assertEqual(problems(s), [])

    def test_a_line_without_a_key_word_is_a_warning(self):
        s = script()
        s["punch"]["text"] = "me 1 hour before leaving:"
        self.assertEqual(problems(s), [])
        self.assertTrue(any("punch" in w and "key word" in w for w in warnings(s)), warnings(s))

    def test_the_colour_is_a_palette_name(self):
        s = script()
        s["setup"]["text"] = "everyone: your outfits always look so {effortless|#FF4FA3}"
        self.assertTrue(any("colour" in p for p in problems(s)), problems(s))
        s["setup"]["text"] = "everyone: your outfits always look so {effortless|lime}"
        self.assertEqual(problems(s), [])

    def test_a_stray_brace_is_a_problem(self):
        s = script()
        s["setup"]["text"] = "everyone: your outfits always look so {effortless"
        self.assertTrue(any("brace" in p for p in problems(s)), problems(s))

    def test_the_palette(self):
        self.assertEqual(profile()["colors"]["key_words"], {"pink": "#FF4FA3", "yellow": "#FFD60A",
                                                            "cyan": "#3DDCFF", "lime": "#7CFF4F",
                                                            "orange": "#FF8A3D"})


class TextSizeAndSafeZoneTest(unittest.TestCase):
    def test_text_is_60_to_72_px(self):
        sizes = profile()["text"]["size"]
        self.assertEqual((sizes["setup"], sizes["punch"], sizes["min"], sizes["max"]), (64, 64, 60, 72))
        for size, ok in ((56, False), (59, False), (60, True), (64, True), (72, True), (73, False), (88, False)):
            s = script()
            s["punch"]["size"] = size
            with self.subTest(size=size):
                self.assertEqual(not any("punch.size" in p for p in problems(s)), ok, problems(s))
                self.assertEqual(warnings(s), [])

    def test_the_setup_sits_at_24_to_35_percent_of_the_height(self):
        for y, warn in ((420, True), (461, False), (600, False), (672, False), (700, True)):
            s = script()
            s["setup"]["anchor"] = {"anchor": "top-center", "y": y, "align": "center"}
            with self.subTest(y=y):
                self.assertEqual(problems(s), [])
                self.assertEqual(any("setup.anchor" in w for w in warnings(s)), warn, warnings(s))

    def test_the_stroke_variant_is_picked_per_text(self):
        s = script()
        s["setup"]["style"] = "stroke"
        self.assertEqual(problems(s), [])
        pr = profile()
        self.assertEqual(mc.text_preset(s["setup"], pr), "tiktok-caption-stroke")
        self.assertEqual(mc.text_preset(s["punch"], pr), "tiktok-caption")
        s["punch"]["style"] = "outline"
        self.assertTrue(any("punch.style" in p for p in problems(s)), problems(s))

    def test_text_stays_inside_the_safe_zone(self):
        for anchor in ({"anchor": "top-center", "y": 170, "align": "center"},
                       {"anchor": "top-left", "x": 140, "y": 1100},
                       {"anchor": "top-left", "x": 20, "y": 300},
                       {"anchor": "top-left", "x": 70, "y": 300},    # Meta's 6 %: cut on a tall phone
                       {"anchor": "top-left", "x": 129, "y": 300},
                       {"anchor": "top-right", "x": 960, "y": 300}):
            s = script()
            s["setup"]["anchor"] = anchor
            with self.subTest(anchor=anchor):
                self.assertTrue(any("setup.anchor" in p for p in problems(s)), problems(s))

    def test_the_sides_are_130_px_for_the_tall_phone_crop(self):
        # Instagram fills a 19.5:9 screen (her screenshot: 920x2000) by height: (1 - (920/2000)/(9/16))/2 of
        # the width goes off each side, ~98 px at 1080; plus a 32 px margin
        crop = (1 - (920 / 2000) / (9 / 16)) / 2 * 1080
        self.assertAlmostEqual(crop, 98.4, places=1)
        z = profile()["safe_zone"]
        self.assertEqual((z["left"], z["right"]), (130, 130))
        self.assertGreaterEqual(z["left"], crop + 30)
        self.assertEqual(z["right_rail"], {"width": 230, "from_y": 1150})
        for anchor in ({"anchor": "top-left", "x": 130, "y": 300}, {"anchor": "top-right", "x": 950, "y": 300}):
            s = script()
            s["setup"]["anchor"] = anchor
            self.assertEqual(problems(s), [], anchor)

    def test_drawn_text_nearer_than_130_px_to_a_side_fails_the_build_check(self):
        cv, pr = Canvas(W, H, 30), profile()
        self.assertEqual(mc.side_problems("setup", (280, 600, 1899, 900), pr, cv), [])  # 140..950 reference
        self.assertEqual(mc.side_problems("setup", None, pr, cv), [])
        left = mc.side_problems("setup", (196, 600, 1500, 900), pr, cv)       # 98 px: the posted list's edge
        self.assertEqual(len(left), 1)
        self.assertIn("98 px from the left edge", left[0])
        right = mc.side_problems("punch", (300, 600, 1960, 900), pr, cv)      # right edge at 980.5
        self.assertEqual(len(right), 1)
        self.assertIn("from the right edge", right[0])
        self.assertEqual(len(mc.side_problems("punch", (100, 0, 2100, 9), pr, cv)), 2)
        self.assertEqual(mc.side_problems("setup", (130, 600, 949, 900), pr, Canvas(1080, 1920, 30)), [])

    def test_the_default_anchors_are_inside_the_safe_zone(self):
        pr = profile()
        for key in ("setup_anchor", "punch_anchor"):
            a = pr["text"][key]
            self.assertEqual((a["anchor"].endswith("center"), a["align"]), (True, "center"), key)
            top = a["y"] - (2 * 64 * 1.2 if a["anchor"].startswith("bottom") else 0)
            self.assertGreaterEqual(top, pr["safe_zone"]["top"], key)
        # centred and at most 820 wide: 130 px clear of both sides of the 1080 frame
        self.assertEqual(pr["typography"]["max_width"], 820)
        self.assertEqual((1080 - pr["typography"]["max_width"]) / 2, pr["safe_zone"]["left"])
        s = script()
        del s["setup"]["anchor"]
        self.assertEqual(problems(s), [])


class Tagged:
    def __init__(self, ref, tags):
        self.ref, self._tags = ref, tags

    def all_tags(self):
        return list(self._tags)


class MatchRuleTest(unittest.TestCase):
    def lookup(self, tags_by_ref):
        return lambda ref: Tagged(ref, tags_by_ref[ref]) if ref in tags_by_ref else None

    def test_every_insert_shows_the_situation_the_last_one_too(self):
        s = script()
        tags = {i["ref"]: ["сборы", "одежда"] for i in s["inserts"]}
        self.assertEqual(mc.check_match(s, self.lookup(tags)), [])
        tags[s["inserts"][-1]["ref"]] = ["взрыв", "пожар"]  # a stock disaster as the closing beat
        got = mc.check_match(s, self.lookup(tags))
        self.assertEqual(len(got), 1, got)
        self.assertIn("inserts[3]", got[0])
        self.assertIn("сборы", got[0])

    def test_an_old_finale_only_has_to_be_in_the_library(self):
        s = old_script()
        tags = {i["ref"]: ["свидание", "нервы"] for i in s["inserts"]}
        tags[s["inserts"][1]["ref"]] = ["работа", "ноутбук"]  # Kostya's critique: work chaos under a date
        tags[s["finale"]["ref"]] = ["взрыв"]
        got = mc.check_match(s, self.lookup(tags))
        self.assertEqual(len(got), 1, got)
        self.assertIn("@meme/monkey-laptop", got[0])

    def test_unknown_ref(self):
        got = mc.check_match(old_script(), self.lookup({}))
        self.assertTrue(all("not in the Library" in p for p in got))
        self.assertEqual(len(got), 6)  # five inserts and the finale


DIMS = {"@meme/frantic-try-on-boutique": (480, 270, 5.0), "@meme/throwing-clothes-out-of-closet": (640, 480, 4.0),
        "@meme/closet-clothes-flying": (720, 540, 5.0), "@meme/confused-travolta": (498, 280, 3.0),
        "@meme/kermit-panic": (480, 264, 2.13), "@meme/monkey-laptop": (852, 462, 10.5),
        "@meme/cillian-murphy-stare": (480, 268, 5.5), "@meme/man-throwing-papers": (1080, 1080, 1.43),
        "@meme/spongebob-burning-office": (480, 360, 7.6),
        "@meme/stock-explosion-mushroom-cloud": (3840, 2160, 16.27)}


class PlanTest(unittest.TestCase):
    def sources(self, **over):
        src = {"setup": mc.Source(Path("/m/IMG_1621.mov"), 2160, 3840, 47.8)}
        for ref, (w, h, d) in DIMS.items():
            src[ref] = mc.Source(Path(f"/m/{ref[6:]}.mp4"), w, h, d)
        src.update(over)
        return src

    def test_plan_places_every_segment_and_ends_on_the_last_insert(self):
        plan = mc.build_plan(script(), profile(), Canvas(W, H, 30), self.sources())
        self.assertEqual(plan.problems, [])
        self.assertEqual([s.id for s in plan.segments], ["setup", "m1", "m2", "m3", "m4"])
        self.assertEqual([s.frames for s in plan.segments], [75, 30, 30, 30, 45])
        self.assertEqual([s.placement.fit for s in plan.segments],
                         ["fill", "blur-fill", "blur-fill", "blur-fill", "blur-fill"])
        self.assertEqual(plan.segments[2].placement.crop, mc.Rect(0, 10, 640, 360))
        self.assertEqual(plan.total_frames, 210)

    def test_the_texts_carry_size_anchor_and_key_word_colour(self):
        plan = mc.build_plan(script(), profile(), Canvas(W, H, 30), self.sources())
        setup, punch = plan.texts["setup"], plan.texts["punch"]
        self.assertEqual(setup["text"], "everyone: your outfits\nalways look so {effortless|pink}")
        self.assertEqual(punch["text"], "me {1 hour before|yellow} leaving:")
        self.assertEqual((setup["size"], punch["size"]), (64, 64))
        self.assertEqual((setup["frames"], punch["frames"]), (75, 135))
        spec = mc.overlay_spec(setup, 30, profile())
        self.assertEqual(spec["preset"], "tiktok-caption")
        self.assertEqual(spec["size"], 64)
        self.assertEqual(spec["text"], setup["text"])
        self.assertEqual(spec["anchor"]["y"], 470)

    def test_the_punch_sits_above_the_highest_meme(self):
        # the closet-flying meme (720x420 after trim) is the tallest: its top edge at 1290 canvas px = 645 reference
        plan = mc.build_plan(script(), profile(), Canvas(W, H, 30), self.sources())
        tops = [s.placement.fg.y for s in plan.segments if s.id != "setup"]
        self.assertEqual(min(tops), 1290)
        self.assertEqual(plan.texts["punch"]["anchor"], {"anchor": "bottom-center", "y": 617.0, "align": "center"})
        self.assertTrue(24 <= 645 - plan.texts["punch"]["anchor"]["y"] <= 40)
        s = script()
        s["punch"]["style"] = "stroke"
        plan = mc.build_plan(s, profile(), Canvas(W, H, 30), self.sources())
        self.assertEqual(mc.overlay_spec(plan.texts["punch"], 30, profile())["preset"], "tiktok-caption-stroke")
        # every insert fills the frame: no band, the profile's y
        s["inserts"] = [dict(i, fit="fill") for i in s["inserts"]]
        plan = mc.build_plan(s, profile(), Canvas(W, H, 30), self.sources())
        self.assertEqual(plan.texts["punch"]["anchor"]["y"], profile()["text"]["punch_anchor"]["y"])

    def test_the_presets_exist_in_the_renderer(self):
        from cf.script_schema import known_presets  # noqa: PLC0415
        known = known_presets()
        ty = profile()["typography"]
        self.assertIn(ty["preset"], known)
        for v in ty["variants"].values():
            self.assertIn(v["preset"], known)
        self.assertIn("tiktok-list", known)
        self.assertIn("bold-outline-wide", known)  # legacy, still renders

    def test_an_old_script_plans_its_finale(self):
        plan = mc.build_plan(old_script(), profile(), Canvas(W, H, 30), self.sources())
        self.assertEqual(plan.problems, [])
        self.assertEqual([s.frames for s in plan.segments], [74, 27, 27, 27, 27, 27, 36])
        self.assertEqual(plan.segments[-1].placement.fit, "fill")
        self.assertEqual(plan.segments[4].placement.crop, mc.Rect(0, 60, 940, 940))

    def test_a_source_too_short_for_its_cut_is_a_problem(self):
        src = self.sources(**{"@meme/confused-travolta": mc.Source(Path("/m/t.mp4"), 498, 280, 1.0)})
        plan = mc.build_plan(script(), profile(), Canvas(W, H, 30), src)
        self.assertTrue(any("travolta" in p and "short" in p for p in plan.problems), plan.problems)

    def test_a_low_res_fill_is_a_warning(self):
        s = script()
        s["inserts"][0]["fit"] = "fill"
        plan = mc.build_plan(s, profile(), Canvas(W, H, 30), self.sources())
        self.assertEqual(plan.problems, [])
        self.assertTrue(any("upscale" in w for w in plan.warnings), plan.warnings)

    def test_filtergraph_crops_exactly_and_scales_to_the_placement(self):
        plan = mc.build_plan(old_script(), profile(), Canvas(W, H, 30), self.sources())
        args = mc.ffmpeg_args(plan, Path("/o/out.mp4"), overlays=None)
        fc = args[args.index("-filter_complex") + 1]
        self.assertIn("crop=940:940:0:60:exact=1", fc)
        self.assertIn("scale=2160:2160", fc)  # the 940x940 papers at full width
        self.assertIn("crop=1215:2160:1312:0:exact=1", fc)  # the explosion's fill window
        self.assertIn("concat=n=6", fc)  # the five inserts and the finale, under the punch line
        self.assertEqual(args[args.index("-frames:v") + 1], "245")
        plan = mc.build_plan(script(), profile(), Canvas(W, H, 30), self.sources())
        args = mc.ffmpeg_args(plan, Path("/o/out.mp4"), overlays=None)
        self.assertIn("concat=n=4", args[args.index("-filter_complex") + 1])  # four inserts, nothing after
        self.assertEqual(args[args.index("-frames:v") + 1], "210")


class SilentRenderCheckTest(unittest.TestCase):
    FACTS = {"video_codec": "h264", "width": W, "height": H, "fps": 30.0, "pix_fmt": "yuv420p",
             "color_range": "tv", "color_primaries": "bt709", "color_transfer": "bt709", "color_space": "bt709",
             "audio_codec": "aac", "sample_rate": 48000, "nb_frames": 245}
    SILENT = {"input_i": -math.inf, "input_tp": -math.inf}
    LOUD = {"input_i": -14.2, "input_tp": -1.5}

    def rows(self, loud, silent):
        exp = rc.expected_for(Canvas(W, H, 30))
        return rc.evaluate(self.FACTS, loud, expected=exp, silent=silent)

    def test_a_silent_track_passes_when_the_format_has_no_music(self):
        self.assertTrue(rc.passed(self.rows(self.SILENT, True)))
        self.assertFalse(rc.passed(self.rows(self.SILENT, False)))

    def test_sound_on_a_silent_format_fails(self):
        self.assertFalse(rc.passed(self.rows(self.LOUD, True)))
        self.assertTrue(rc.passed(self.rows(self.LOUD, False)))

    def test_the_meme_cut_profile_says_silent(self):
        self.assertTrue(rc.silent_for(profile()))
        self.assertFalse(rc.silent_for(json.loads(rc.STYLE_PATH.read_text())))

    def test_a_meme_cut_script_next_to_out_picks_its_profile(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t) / "meme-x"
            (folder / "out").mkdir(parents=True)
            (folder / "script.json").write_text(json.dumps(script()))
            self.assertEqual(rc.format_for(folder / "out" / "meme-x.mp4"), "meme-cut")
            (folder / "script.json").write_text(json.dumps({"schema": "cf-script/1"}))
            self.assertIsNone(rc.format_for(folder / "out" / "meme-x.mp4"))


@unittest.skipUnless(HAVE_FFMPEG, "ffmpeg and ffprobe are needed")
class ComposeTest(unittest.TestCase):
    """A real ffmpeg compose at a 216x384 canvas from synthetic sources; the file passes render_check."""

    def test_compose_end_to_end(self):
        cw, ch = 216, 384
        with tempfile.TemporaryDirectory() as t:
            t = Path(t)

            def make(name, size, dur, rate=30):
                p = t / name
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                                f"testsrc2=s={size}:d={dur}:r={rate}", "-c:v", "libx264", "-pix_fmt", "yuv420p",
                                str(p)], check=True)
                return p

            setup = make("setup.mp4", "108x192", 4)
            meme = make("meme.mp4", "64x36", 3, 10)
            s = script()
            src = {"setup": mc.Source(setup, 108, 192, 4.0)}
            for i in s["inserts"]:
                src[i["ref"]] = mc.Source(meme, 64, 36, 3.0)
                i["in_s"] = 0.5
                i.pop("trim", None)
            s["setup"]["in_s"] = 0.2
            canvas = Canvas(cw, ch, 30, 108)
            plan = mc.build_plan(s, profile(), canvas, src)
            self.assertEqual(plan.problems, [])
            out = t / "out.mp4"
            mc.compose(plan, out, overlays=None)
            exp = rc.expected_for(canvas)
            rows, facts, _ = rc.check_file(out, expected=exp, expect_duration=210 / 30, silent=True)
            self.assertTrue(rc.passed(rows), rc.format_table(out, rows, facts))
            self.assertEqual(facts["nb_frames"], 210)


if __name__ == "__main__":
    unittest.main()


class RectGapTest(unittest.TestCase):
    def test_gap_between_boxes(self):
        self.assertEqual(mc.rect_gap((0, 0, 10, 10), (5, 5, 20, 20)), 0.0)   # overlap
        self.assertEqual(mc.rect_gap((0, 0, 10, 10), (30, 0, 40, 10)), 20.0)  # side by side
        self.assertEqual(mc.rect_gap((0, 0, 10, 10), (0, 25, 10, 40)), 15.0)  # text above her
        self.assertEqual(mc.rect_gap((0, 0, 10, 10), (13, 14, 20, 20)), 5.0)  # diagonal
