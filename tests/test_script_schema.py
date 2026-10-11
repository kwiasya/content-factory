"""Validator tests on hand-built Scripts; no Resolve needed."""

import copy
import json
import subprocess
import sys
import unittest
from pathlib import Path

from cf.script_schema import ScriptError, from_dict, load, validate

ROOT = Path(__file__).resolve().parents[1]
STYLE = json.loads((ROOT / "style.json").read_text())
MANIFEST = {
    "walk": "test-walk",
    "clips": [
        {"file": "A.MOV", "fps": 60.0, "duration_s": 13.0},
        {"file": "B.MOV", "fps": 24.0, "duration_s": 29.0},
        {"file": "C.mov", "fps": 30.0, "duration_s": 33.0},
    ],
}


def good() -> dict:
    return {
        "schema": "cf-script/1",
        "walk": "test-walk",
        "concept": "A slow afternoon by the lake.",
        "format": "pov",
        "target_length_s": 9,
        "hook": {"type": "visual_payoff", "text": "This lake hides a whole palace", "clip": "A.MOV"},
        "shots": [
            {"clip": "A.MOV", "in_s": 1.0, "out_s": 4.0, "role": "hook", "speed": 1.0, "overlay": None,
             "transition": "cut", "beat_index": None},
            {"clip": "B.MOV", "in_s": 2.0, "out_s": 5.0, "role": "build", "speed": 1.0,
             "overlay": {"text": "Sanssouci, Potsdam", "type": "place"}, "transition": "dissolve",
             "beat_index": None},
            {"clip": "C.mov", "in_s": 0.0, "out_s": 3.0, "role": "payoff", "transition": "cut"},
        ],
        "ending": "reveal_last",
        "cta": "Send this to your travel buddy",
        "caption": "Potsdam in October\nQuiet paths.\nSend this to your travel buddy",
        "hashtags": ["#potsdam", "#citybreak"],
        "location_tag": "Potsdam, Germany",
        "alt_text": "A lake and a palace.",
        "track": None,
        "metrics": None,
    }


def problems(d: dict, manifest=MANIFEST) -> list[str]:
    return validate(from_dict(d), manifest, STYLE)


class GoodScriptTest(unittest.TestCase):
    def test_good_script_has_no_violations(self):
        self.assertEqual(problems(good()), [])

    def test_shot_ids_default_to_index(self):
        s = from_dict(good())
        self.assertEqual([x.id for x in s.shots], ["s01", "s02", "s03"])
        self.assertEqual(s.total_s, 9.0)

    def test_first_pass_without_overlays_caption_or_track(self):
        d = good()
        for sh in d["shots"]:
            sh["overlay"] = None
        for k in ("caption", "cta", "track", "metrics", "alt_text"):
            d.pop(k)
        self.assertEqual(problems(d), [])

    def test_manifest_is_optional(self):
        self.assertEqual(problems(good(), manifest=None), [])


class BadScriptTest(unittest.TestCase):
    def assertViolation(self, d: dict, needle: str):
        found = problems(d)
        self.assertTrue(any(needle in p for p in found), f"{needle!r} not in {found}")

    def test_hook_too_long(self):
        d = good()
        d["hook"]["text"] = "one two three four five six seven eight nine"
        self.assertViolation(d, "hook.text: 9 words")

    def test_hook_too_short(self):
        d = good()
        d["hook"]["text"] = "Lake palace"
        self.assertViolation(d, "hook.text: 2 words")

    def test_hook_clip_must_open(self):
        d = good()
        d["hook"]["clip"] = "B.MOV"
        self.assertViolation(d, "must be the first shot's clip")

    def test_overlay_too_many_words(self):
        d = good()
        d["shots"][1]["overlay"]["text"] = "one two three four five six seven eight nine"
        self.assertViolation(d, "overlay has 9 words")

    def test_overlay_hold_too_short(self):
        d = good()
        d["shots"][1]["out_s"] = 3.8  # 1.8 s, also below the 2 s hold
        d["target_length_s"] = 8
        self.assertViolation(d, "overlay holds 1.80 s")

    def test_overlay_type(self):
        d = good()
        d["shots"][1]["overlay"]["type"] = "title"
        self.assertViolation(d, "overlay.type 'title'")

    def test_shot_too_short_and_too_long(self):
        d = good()
        d["shots"][0]["out_s"] = 2.0  # 1.0 s
        self.assertViolation(d, "lasts 1.00 s")
        d = good()
        d["shots"][0]["out_s"] = 7.0  # 6 s build/hook
        self.assertViolation(d, "lasts 6.00 s")

    def test_payoff_may_reach_payoff_max_but_not_beyond(self):
        style = copy.deepcopy(STYLE)
        style["pacing"]["shot_s"]["payoff_max"] = 7.0
        d = good()
        d["shots"][2]["out_s"] = 6.5
        d["target_length_s"] = 12.5
        self.assertEqual(validate(from_dict(d), MANIFEST, style), [])
        d["shots"][2]["out_s"] = 7.5
        d["target_length_s"] = 13.5
        self.assertTrue(any("lasts 7.50 s" in p for p in validate(from_dict(d), MANIFEST, style)))

    def test_speed_changes_timeline_duration(self):
        d = good()
        d["shots"][0]["speed"] = 0.5  # 3 s of source -> 6 s on the timeline
        self.assertViolation(d, "lasts 6.00 s")

    def test_out_past_clip_end(self):
        d = good()
        d["shots"][0].update(in_s=10.0, out_s=13.5)
        self.assertViolation(d, "past the end of A.MOV")

    def test_in_after_out(self):
        d = good()
        d["shots"][0].update(in_s=4.0, out_s=3.0)
        self.assertViolation(d, "need 0 <= in_s < out_s")

    def test_unknown_clip(self):
        d = good()
        d["shots"][2]["clip"] = "Z.MOV"
        self.assertViolation(d, "clip 'Z.MOV' not in the manifest")

    def test_total_outside_target(self):
        d = good()
        d["target_length_s"] = 45
        self.assertViolation(d, "shots add up to 9.00 s, target is 45")

    def test_too_many_hashtags(self):
        d = good()
        d["hashtags"] = [f"#t{i}" for i in range(6)]
        self.assertViolation(d, "hashtags: 6")

    def test_role_and_transition_enums(self):
        d = good()
        d["shots"][1]["role"] = "intro"
        d["shots"][1]["transition"] = "wipe"
        found = problems(d)
        self.assertTrue(any("role 'intro'" in p for p in found))
        self.assertTrue(any("transition 'wipe'" in p for p in found))

    def test_caption_must_carry_cta(self):
        d = good()
        d["caption"] = "Potsdam in October\nQuiet paths."
        self.assertViolation(d, "caption: must end with the CTA")

    def test_location_tag_required(self):
        d = good()
        d["location_tag"] = ""
        self.assertViolation(d, "location_tag")

    def test_wrong_schema_and_walk(self):
        d = good()
        d["schema"] = "cf-script/0"
        d["walk"] = "other"
        found = problems(d)
        self.assertTrue(any(p.startswith("schema:") for p in found))
        self.assertTrue(any(p.startswith("walk:") for p in found))

    def test_structural_errors_raise(self):
        d = good()
        del d["shots"][0]["in_s"]
        with self.assertRaises(ScriptError):
            from_dict(d)
        d = good()
        d["shots"] = []
        with self.assertRaises(ScriptError):
            from_dict(d)


def seamless() -> dict:
    """good() as a seamless loop: s04 is the run-up A.MOV 0.0-1.5 into the hook's first frame at 1.5."""
    d = good()
    d["ending"] = "loop_seamless"
    d["shots"][0].update(in_s=1.5, out_s=4.0)  # hook, 2.5 s
    d["shots"].append({"clip": "A.MOV", "in_s": 0.0, "out_s": 1.5, "role": "loop", "speed": 1.0,
                       "overlay": None, "transition": "cut", "beat_index": None})
    d["target_length_s"] = 10
    return d


class LoopSeamlessTest(unittest.TestCase):
    def found(self, d: dict, manifest=MANIFEST) -> list[str]:
        return [p for p in problems(d, manifest) if p.startswith("ending loop_seamless")]

    def assertSeam(self, d: dict, needle: str, manifest=MANIFEST):
        got = self.found(d, manifest)
        self.assertTrue(any(needle in p for p in got), f"{needle!r} not in {got}")

    def test_seamless_loop_is_valid(self):
        self.assertEqual(problems(seamless()), [])
        self.assertEqual(problems(seamless(), manifest=None), [])

    def test_loop_seamless_is_an_ending(self):
        d = seamless()
        d["ending"] = "loop_match"  # the weaker option needs no seam
        d["shots"][-1]["clip"] = "C.mov"
        self.assertEqual(problems(d), [])

    def test_last_shot_must_use_the_first_shots_clip(self):
        d = seamless()
        d["shots"][-1]["clip"] = "B.MOV"
        self.assertSeam(d, "must be the first shot's clip 'A.MOV'")

    def test_seam_in_frames_at_the_clip_fps(self):
        d = seamless()
        d["shots"][-1]["out_s"] = 1.5 + 0.02  # still 45 timeline frames: the next frame is 90 = 1.5 s
        self.assertEqual(self.found(d), [])
        d["shots"][-1]["out_s"] = 1.5 + 0.034  # 46 frames: two 60 fps source frames repeat
        self.assertSeam(d, "continue at frame 92 (repeats 2)")
        self.assertSeam(d, "start it at frame -2 (in_s -0.0333, out_s 1.5000)")
        # Without a manifest the clip runs at the timeline fps (30).
        self.assertSeam(d, "continue at frame 46 (repeats 1)", manifest=None)

    def test_gap_or_overlap_at_the_seam(self):
        d = seamless()
        d["shots"][-1].update(in_s=0.0, out_s=1.4)
        self.assertSeam(d, "must run into the first shot's first source frame 90")
        self.assertSeam(d, "(skips 6)")

    def test_2997_on_30_seam_is_one_source_frame_later_than_the_seconds(self):
        # Mallorca reel-01 v1: the seconds matched (out_s == in_s) but Resolve skipped frame 3610.
        man = {"walk": "w", "clips": [{"file": "A.MOV", "fps": 29.97003, "duration_s": 383.783}]}
        d = seamless()
        d["shots"][0].update(in_s=120.487, out_s=122.8894)
        d["shots"][-1].update(in_s=119.1857, out_s=120.487)
        self.assertSeam(d, "from frame 3572 (119.186 s) its 39 timeline frames at 30 fps continue at frame "
                           "3610 (skips 1); start it at frame 3573 (in_s 119.2191", manifest=man)
        d["shots"][-1].update(in_s=119.2191, out_s=120.5191)
        self.assertEqual(self.found(d, manifest=man), [])

    def test_both_shots_at_speed_one(self):
        d = seamless()
        d["shots"][0]["speed"] = 0.5
        d["shots"][0]["out_s"] = 2.75  # still 2.5 s on the timeline
        self.assertSeam(d, "s01 speed must be 1.0")
        d = seamless()
        d["shots"][-1]["speed"] = 1.25
        self.assertSeam(d, "s04 speed must be 1.0")

    def test_no_transition_or_fade_across_the_seam(self):
        d = seamless()
        d["shots"][0]["transition"] = "dip"
        self.assertSeam(d, "s01 transition must be 'cut'")
        d = seamless()
        d["shots"][0]["fade_in_s"] = 0.3
        self.assertSeam(d, "s01 fade_in_s must be 0")
        d = seamless()
        d["shots"][-1]["fade_out_s"] = 0.3
        self.assertSeam(d, "s04 fade_out_s must be 0")

    def test_no_overlay_on_the_last_shot(self):
        d = seamless()
        d["shots"][-1]["overlay"] = {"text": "Again?", "type": "line"}
        self.assertSeam(d, "s04 must have overlay null")
        # The hook overlay on the first shot is fine: it fades in after the seam.
        d = seamless()
        d["shots"][0]["overlay"] = {"text": "This lake hides a whole palace", "type": "line"}
        self.assertEqual(self.found(d), [])

    def test_needs_two_shots(self):
        d = seamless()
        d["shots"] = d["shots"][:1]
        d["target_length_s"] = 3
        self.assertSeam(d, "needs at least 2 shots")


class CliTest(unittest.TestCase):
    def run_cli(self, tmp: Path, d: dict) -> subprocess.CompletedProcess:
        (tmp / "script.json").write_text(json.dumps(d))
        (tmp / "m.json").write_text(json.dumps(MANIFEST))
        return subprocess.run([sys.executable, "-m", "cf.script_schema", "validate", str(tmp / "script.json"),
                               "--manifest", str(tmp / "m.json")], capture_output=True, text=True)

    def test_cli_exit_codes(self):
        import tempfile

        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            ok = self.run_cli(tmp, good())
            self.assertEqual(ok.returncode, 0, ok.stdout + ok.stderr)
            self.assertEqual(load(tmp / "script.json").walk, "test-walk")
            d = good()
            d["hashtags"] = [f"#t{i}" for i in range(7)]
            bad = self.run_cli(tmp, d)
            self.assertEqual(bad.returncode, 1)
            self.assertIn("hashtags: 7", bad.stdout)



class CanvasFieldTest(unittest.TestCase):
    def test_canvas_is_optional_and_parsed(self):
        self.assertIsNone(from_dict(good()).canvas)
        self.assertEqual(from_dict({**good(), "canvas": "landscape"}).canvas, "landscape")
        with self.assertRaises(ScriptError):
            from_dict({**good(), "canvas": 16})

    def test_unknown_canvas_is_a_violation(self):
        self.assertEqual(validate(from_dict({**good(), "canvas": "landscape"}), MANIFEST, STYLE), [])
        self.assertTrue(any(p.startswith("canvas:") for p in
                            validate(from_dict({**good(), "canvas": "cinema"}), MANIFEST, STYLE)))

if __name__ == "__main__":
    unittest.main()
