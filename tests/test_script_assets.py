"""Asset cues in a Script (shots[].assets): loader, validator rules against a hand-written Library, md refs,
Video folders, the pos boxes in style.json and the validate CLI. Offline, no ffmpeg."""

import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf import assets as ca
from cf.canvas import resolve
from cf.script_schema import AssetCue, ScriptError, check, from_dict, validate

from library_fixture import make_library
from test_script_schema import STYLE, good

ROOT = Path(__file__).resolve().parents[1]


def with_cues(*cues_by_shot: list[dict], base: dict | None = None) -> dict:
    d = copy.deepcopy(base or good())
    for i, cues in enumerate(cues_by_shot):
        if cues:
            d["shots"][i]["assets"] = cues
    return d


def looping() -> dict:
    d = good()
    d["ending"] = "loop_seamless"
    d["shots"][0].update(in_s=4.0, out_s=7.0)
    d["shots"][2] = {"clip": "A.MOV", "in_s": 1.0, "out_s": 4.0, "role": "loop", "transition": "cut"}
    return d


class AssetsTestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, cls.footage, cls.db = make_library(Path(cls.tmp.name))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def ctx(self, md=None):
        return ca.AssetContext(self.lib, None, None, md or {})

    def findings(self, d, md=None, style=STYLE):
        return check(from_dict(d), None, style, self.ctx(md))

    def problems(self, d, md=None):
        return self.findings(d, md).problems

    def assertProblem(self, d, needle, md=None):
        found = self.problems(d, md)
        self.assertTrue(any(needle in p for p in found), f"{needle!r} not in {found}")

    def assertNoProblems(self, d, md=None):
        self.assertEqual(self.problems(d, md), [])


class LoaderTest(AssetsTestCase):
    def test_a_script_without_assets_is_unchanged_with_or_without_a_library(self):
        s = from_dict(good())
        self.assertEqual([sh.assets for sh in s.shots], [[], [], []])
        plain = validate(s, None, STYLE)
        self.assertEqual(plain, validate(s, None, STYLE, assets=self.ctx()))
        self.assertEqual(plain, validate(s, None, STYLE, assets=ca.AssetContext(None, "no factory.db", None, {})))
        self.assertEqual(check(s, None, STYLE, self.ctx()).warnings, [])
        d = good()
        d["shots"][0]["assets"] = None
        self.assertEqual(from_dict(d).shots[0].assets, [])

    def test_assets_structure_errors_are_script_errors(self):
        for cues in ({}, ["x"], [{"at_s": 0}], [{"ref": "@sfx/boom"}], [{"ref": "@sfx/boom", "at_s": "1"}],
                     [{"ref": "@sfx/boom", "at_s": 0, "pos": 3}], [{"ref": 5, "at_s": 0}],
                     [{"ref": "@sfx/boom", "at_s": 0, "dur_s": "2"}], [{"ref": "@sfx/boom", "at_s": 0, "db": True}]):
            d = good()
            d["shots"][1]["assets"] = cues
            with self.subTest(cues=cues), self.assertRaises(ScriptError):
                from_dict(d)

    def test_a_cue_loads_with_its_fields(self):
        d = with_cues([{"ref": "@face/шок", "at_s": 0.4, "dur_s": 1.2, "pos": "bottom-left"}])
        self.assertEqual(from_dict(d).shots[0].assets, [AssetCue("@face/шок", 0.4, 1.2, "bottom-left", None)])

    def test_unknown_cue_keys_are_violations(self):
        d = with_cues([], [], [{"ref": "@sfx/own-hit", "at_s": 0.1, "dur": 1}])
        self.assertProblem(d, "shots[2] (s03).assets[0]: unknown key 'dur' (known: ref, at_s, dur_s, pos, db)")


class RefsTest(AssetsTestCase):
    def test_valid_cues_pass_without_warnings_for_own_and_free(self):
        d = with_cues([{"ref": "@face/шок", "at_s": 0.4}], [{"ref": "@meme/silent", "at_s": 0.5, "pos": "center"}],
                      [{"ref": "@sfx/own-hit", "at_s": 0.9}])
        f = self.findings(d)
        self.assertEqual((f.problems, f.warnings), ([], []))

    def test_file_derived_name_and_alias_resolve(self):
        self.assertNoProblems(with_cues([{"ref": "@face/1750738-sticker", "at_s": 0.0}]))
        f = self.findings(with_cues([{"ref": "@emoji/старое-имя", "at_s": 0.0}]),
                          md={"@emoji/в-шоке": ["brief.md"]})
        self.assertEqual(f.problems, [])

    def test_broken_ref_lists_nearest_matches(self):
        self.assertProblem(with_cues([{"ref": "@sfx/вуш2", "at_s": 0.0}]), "no such Asset; nearest: @sfx/вуш-2")
        self.assertProblem(with_cues([{"ref": "@face/шк", "at_s": 0.0}]), "@face/шок")
        self.assertProblem(with_cues([{"ref": "@face/шк", "at_s": 0.0}]), "shots[0] (s01).assets[0] (@face/шк):")

    def test_bad_grammar_is_not_an_asset_ref(self):
        for ref in ("sfx/вуш-2", "@nope/x"):
            with self.subTest(ref=ref):
                self.assertProblem(with_cues([{"ref": ref, "at_s": 0.0}]),
                                   "not an Asset ref (expected @<category>/<name>)")

    def test_categories_that_cues_cannot_place(self):
        for ref, cat in (("@bg/loop", "bg"), ("@music/pixabay", "music"), ("@font/komika-title", "font")):
            with self.subTest(ref=ref):
                self.assertProblem(with_cues([{"ref": ref, "at_s": 0.0}]),
                                   f"is a {cat} Asset; cues place sfx, meme, img, emoji, face, footage, fx")


class RightsTest(AssetsTestCase):
    def test_unknown_rights_rejected_unless_short_sfx_or_referenced_in_md(self):
        meme = with_cues([{"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 2.0}])
        self.assertProblem(meme, "unknown rights: use it only after the Author references it")
        f = self.findings(meme, md={"@meme/chipi": ["notes.md"]})
        self.assertEqual(f.problems, [])
        self.assertTrue(any("allowed: the Author referenced it in notes.md" in w for w in f.warnings), f.warnings)
        emoji = with_cues([{"ref": "@emoji/в-шоке", "at_s": 0.0}])
        self.assertProblem(emoji, "unknown rights")
        self.assertEqual(self.findings(emoji, md={"@emoji/старое-имя": ["brief.md"]}).problems, [])
        f = self.findings(with_cues([{"ref": "@sfx/вуш-2", "at_s": 0.0}]))
        self.assertEqual(f.problems, [])
        self.assertTrue(any("allowed: a sound effect under 2 s" in w for w in f.warnings), f.warnings)
        self.assertProblem(with_cues([{"ref": "@sfx/boom", "at_s": 0.0}]), "unknown rights")

    def test_md_refs_reads_top_level_md_files_only(self):
        with tempfile.TemporaryDirectory() as t:
            folder = Path(t)
            (folder / "notes.md").write_text("Put @meme/chipi after the reveal, and @sfx/boom.\n")
            (folder / "brief.md").write_text("(@meme/chipi)")
            (folder / "sub").mkdir()
            (folder / "sub/x.md").write_text("@sfx/вуш-2")
            (folder / ".hidden.md").write_text("@sfx/вуш-2-2")
            (folder / "script.json").write_text('{"ref": "@face/шок"}')
            (folder / "script.md").write_text("@sfx/boom")
            (folder / "script.v2.md").write_text("@face/шок")
            (folder / "script-long.md").write_text("@face/шок")
            self.assertEqual(ca.md_refs(folder), {"@meme/chipi": ["brief.md", "notes.md"], "@sfx/boom": ["notes.md"]})
            (folder / "scripting-notes.md").write_text("@sfx/вуш-2")
            self.assertEqual(ca.md_refs(folder)["@sfx/вуш-2"], ["scripting-notes.md"])

    def test_the_script_file_rule_is_the_one_desk_uses(self):
        from cf.desk.videos_api import kind_of

        for name, script in (("script.md", True), ("script.json", True), ("script.v2.md", True),
                             ("script-long.json", True), ("script_2.md", True), ("scripting-notes.md", False),
                             ("scripts.md", False), ("script.txt", False), ("notes.md", False)):
            with self.subTest(name=name):
                self.assertEqual(ca.is_script_file(name), script)
                self.assertEqual(kind_of(name) == "script", script)

    def test_video_of_finds_new_and_legacy_video_folders(self):
        with tempfile.TemporaryDirectory() as t:
            f = Path(t)
            v = f / "videos/boat-day"
            v.mkdir(parents=True)
            (v / "video.json").write_text(json.dumps({"format": "walk-reel", "slug": "boat-day"}))
            got = ca.video_of(v / "script.json")
            self.assertEqual((got.slug, got.root, got.format, got.legacy), ("boat-day", f, "walk-reel", False))
            r = f / "potsdam/reels/reel-01"
            r.mkdir(parents=True)
            got = ca.video_of(r / "script.json")
            self.assertEqual((got.slug, got.root, got.format, got.legacy),
                             ("potsdam~reel-01", f, "walk-reel", True))
            self.assertIsNone(ca.video_of(f / "loose.json"))
            (v / "video.json").write_text("{not json")
            self.assertIsNone(ca.video_of(v / "script.json").format)


class TimingTest(AssetsTestCase):
    def test_cue_timing_rules(self):
        own = "@sfx/own-hit"
        self.assertProblem(with_cues([{"ref": own, "at_s": 3.0}]), "at_s 3 must be in [0, 3)")
        self.assertProblem(with_cues([{"ref": own, "at_s": -0.1}]), "at_s -0.1 must be in [0, 3)")
        self.assertProblem(with_cues([{"ref": own, "at_s": 0.0, "dur_s": 3.2}]),
                           "dur_s 3.2 is longer than the Asset (1 s)")
        self.assertProblem(with_cues([{"ref": "@meme/silent", "at_s": 0.0, "dur_s": 0.0}]), "dur_s 0 must be")
        self.assertProblem(with_cues([{"ref": "@img/фон-1", "at_s": 0.0, "dur_s": 6}]),
                           "dur_s 6 is longer than a still may stay (5 s)", md={"@img/фон-1": ["notes.md"]})
        self.assertNoProblems(with_cues([{"ref": own, "at_s": 2.5}]))
        self.assertProblem(with_cues([], [], [{"ref": own, "at_s": 2.6}]), "runs 0.60 s past the end of the Reel")

    def test_the_reel_end_is_checked_in_frames_as_the_build_snaps_them(self):
        d = good()
        d["shots"][2]["out_s"] = 3.03
        own = "@sfx/own-hit"
        self.assertProblem(with_cues([], [], [{"ref": own, "at_s": 2.03}], base=d), "past the end of the Reel")
        self.assertNoProblems(with_cues([], [], [{"ref": own, "at_s": 2.0}], base=d))
        manifest = {"clips": [{"file": "A.MOV", "fps": 30.0, "duration_s": 30.0}, {"file": "B.MOV", "fps": 30.0, "duration_s": 30.0},
                              {"file": "C.mov", "fps": 30.0, "duration_s": 30.0}]}
        d["shots"][2].update(in_s=0.02, out_s=3.02)
        late = from_dict(with_cues([], [], [{"ref": own, "at_s": 2.0}], base=d))
        self.assertTrue(any("past the end of the Reel" in p for p in check(late, manifest, STYLE, self.ctx()).problems))
        d["shots"][2].update(in_s=0.0, out_s=3.0)
        self.assertEqual(check(from_dict(with_cues([], [], [{"ref": own, "at_s": 2.0}], base=d)), manifest, STYLE,
                               self.ctx()).problems, [])

    def test_visual_cue_must_clear_the_loop_seam(self):
        base = looping()
        self.assertEqual(validate(from_dict(base), None, STYLE), [])
        late = with_cues([], [], [{"ref": "@face/шок", "at_s": 0.7, "dur_s": 2.1}], base=base)
        self.assertProblem(late, "jumps away when the Reel loops: end it ≥ 0.5 s before the end (at_s + dur_s ≤ 2.5)")
        self.assertNoProblems(with_cues([], [], [{"ref": "@face/шок", "at_s": 0.7, "dur_s": 2.1}]))
        self.assertNoProblems(with_cues([], [], [{"ref": "@sfx/own-hit", "at_s": 2.0}], base=base))

    def test_pos_and_db_rules(self):
        self.assertProblem(with_cues([{"ref": "@sfx/own-hit", "at_s": 0.0, "pos": "center"}]),
                           "pos is for pictures; @sfx/own-hit is a sound")
        self.assertProblem(with_cues([{"ref": "@meme/silent", "at_s": 0.0, "pos": "middle"}]),
                           "pos 'middle' is not one of center, top, bottom")
        self.assertProblem(with_cues([{"ref": "@meme/silent", "at_s": 0.0, "db": -3}]), "db on a silent picture")
        self.assertProblem(with_cues([{"ref": "@sfx/own-hit", "at_s": 0.0, "db": 20}]), "db 20 must be in [-24, 12]")
        self.assertNoProblems(with_cues([{"ref": "@meme/chipi", "at_s": 0.0, "db": -3, "dur_s": 2.0}]),
                              md={"@meme/chipi": ["notes.md"]})

    def test_variant_and_loudness_rules(self):
        self.assertProblem(with_cues([{"ref": "@emoji/не-ключён", "at_s": 0.0}], ),
                           "green screen not keyed yet", md={"@emoji/не-ключён": ["notes.md"]})
        self.assertProblem(with_cues([{"ref": "@face/1750799-sticker", "at_s": 0.0}]), "only a VP9 .webm")
        f = self.findings(with_cues([{"ref": "@face/1750770-sticker", "at_s": 0.0}]))
        self.assertEqual(f.problems, [])
        self.assertTrue(any("placing the still png" in w for w in f.warnings), f.warnings)
        self.assertProblem(with_cues([{"ref": "@sfx/тихо", "at_s": 0.0}]), "loudness not measured")

    def test_at_most_two_overlapping_cues_per_kind(self):
        own, w = "@sfx/own-hit", "@sfx/вуш-2"
        self.assertNoProblems(with_cues([{"ref": own, "at_s": 0.0}, {"ref": w, "at_s": 0.2}]))
        three = with_cues([{"ref": own, "at_s": 0.0}, {"ref": w, "at_s": 0.2}, {"ref": "@sfx/вуш-2-2", "at_s": 0.1}])
        self.assertProblem(three, "3 audio cues overlap at 0.20 s (s01 @sfx/own-hit, s01 @sfx/вуш-2-2, s01 @sfx/вуш-2)"
                                  "; at most 2")
        meme = with_cues([{"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 2.0}, {"ref": own, "at_s": 0.5},
                          {"ref": w, "at_s": 0.6}])
        self.assertProblem(meme, "3 audio cues overlap", md={"@meme/chipi": ["notes.md"]})
        self.assertNoProblems(with_cues([{"ref": "@meme/silent", "at_s": 0.0}, {"ref": "@face/шок", "at_s": 0.5}]))

    def test_no_library_with_cues_is_one_problem(self):
        d = with_cues([{"ref": "@sfx/own-hit", "at_s": 0.0}], [{"ref": "@sfx/boom", "at_s": 0.0}])
        got = check(from_dict(d), None, STYLE, ca.AssetContext(None, "no factory.db at /x", None, {})).problems
        self.assertEqual(got, ["assets: 2 cue(s) need the Library: no factory.db at /x (index a Pack with "
                               "python -m cf.library index, or pass --shared-root/--db)"])
        self.assertEqual(len(check(from_dict(d), None, STYLE, None).problems), 1)

    def test_structural_check_without_cue_rules(self):
        d = with_cues([{"ref": "@sfx/own-hit", "at_s": 0.0, "dur": 1}])
        self.assertEqual(check(from_dict(d), None, STYLE, None, cues=False), check(from_dict(good()), None, STYLE))


class LibraryRootTest(unittest.TestCase):
    def test_the_library_and_its_db_come_from_the_shared_root_not_the_videos_root(self):
        with tempfile.TemporaryDirectory() as t:
            _, shared, _ = make_library(Path(t), root=Path(t) / "shared")
            local = Path(t) / "local"
            video = local / "videos/boat"
            video.mkdir(parents=True)
            (video / "video.json").write_text(json.dumps({"format": "walk-reel"}))
            env = {"CF_SHARED_ROOT": str(shared), "CF_LOCAL_ROOT": str(local)}
            with mock.patch.dict(os.environ, env):
                os.environ.pop("CF_FACTORY_DB", None)
                ctx = ca.context(video / "script.json")
                self.assertIsNone(ctx.library_problem)
                self.assertEqual(ctx.library.root, shared)
                self.assertEqual(ctx.video.root, local)
                self.assertEqual(ca.library_root(), shared)
                other = ca.context(video / "script.json", root=local)
                self.assertIsNone(other.library)
                self.assertIn(str(local / "factory.db"), other.library_problem)


class PosBoxesTest(unittest.TestCase):
    def test_pos_boxes_in_style_json_are_inside_the_safe_zone(self):
        z = STYLE["safe_zone"]
        rail = z["right_rail"]
        for name, b in STYLE["assets"]["pos"].items():
            if not isinstance(b, dict):
                continue
            with self.subTest(portrait=name):
                self.assertGreaterEqual(b["x"], z["left"])
                self.assertGreaterEqual(b["y"], z["top"])
                self.assertLessEqual(b["x"] + b["w"], 1080 - z["right"])
                self.assertLessEqual(b["y"] + b["h"], 1920 - z["bottom"])
                if b["y"] + b["h"] > rail["from_y"]:
                    self.assertLessEqual(b["x"] + b["w"], 1080 - z["right"] - rail["width"])
        land = STYLE["canvases"]["landscape"]
        lz = land["safe_zone"]
        for name, b in land["asset_pos"].items():
            if not isinstance(b, dict):
                continue
            with self.subTest(landscape=name):
                self.assertGreaterEqual(b["x"], lz["left"])
                self.assertGreaterEqual(b["y"], lz["top"])
                self.assertLessEqual(b["x"] + b["w"], 1920 - lz["right"])
                self.assertLessEqual(b["y"] + b["h"], 1080 - lz["bottom"])
        self.assertEqual(set(STYLE["assets"]["pos"]), set(ca.POS_PRESETS))
        self.assertEqual({k for k in land["asset_pos"] if not k.startswith("_")}, set(ca.POS_PRESETS))

    def test_pos_box_is_in_canvas_px(self):
        self.assertEqual(ca.pos_box(STYLE, resolve(STYLE), "center"), ca.Box(580, 1320, 1000, 960))
        self.assertEqual(ca.pos_box(STYLE, resolve(STYLE, "landscape"), "top-left"), ca.Box(220, 140, 800, 800))
        self.assertEqual(ca.pos_box(STYLE, resolve(STYLE), "full"), "cover")


class CliTest(unittest.TestCase):
    def run_cli(self, script: Path, *args: str):
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        return subprocess.run([sys.executable, "-m", "cf.script_schema", "validate", str(script), *args],
                              capture_output=True, text=True, env=env, cwd=ROOT)

    def test_cli_prints_warnings_and_exits_zero_and_fails_on_broken_refs(self):
        with tempfile.TemporaryDirectory() as t:
            _, footage, db = make_library(Path(t))
            v = footage / "videos/boat"
            v.mkdir(parents=True)
            (v / "video.json").write_text(json.dumps({"format": "walk-reel"}))
            (v / "notes.md").write_text("meme here: @meme/chipi\n")
            script = v / "script.json"
            script.write_text(json.dumps(with_cues([{"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 2.0}])))
            res = self.run_cli(script, "--shared-root", str(footage), "--db", str(db))
            self.assertEqual(res.returncode, 0, res.stdout + res.stderr)
            self.assertIn("OK ", res.stdout)
            self.assertIn("- WARN shots[0] (s01).assets[0] (@meme/chipi): unknown rights; allowed: the Author "
                          "referenced it in notes.md", res.stdout)
            res = self.run_cli(script, "--no-library")
            self.assertEqual(res.returncode, 1, res.stdout)
            self.assertIn("need the Library", res.stdout)
            script.write_text(json.dumps(with_cues([{"ref": "@meme/chipy", "at_s": 0.0}])))
            res = self.run_cli(script, "--footage-root", str(footage), "--db", str(db))
            self.assertEqual(res.returncode, 1, res.stdout)
            self.assertIn("nearest: @meme/chipi", res.stdout)


if __name__ == "__main__":
    unittest.main()
