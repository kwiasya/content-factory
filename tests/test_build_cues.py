"""Pure planning of Asset cues for cf.build: Script cues + planned shots + a Library -> lanes, record frames,
source frames, levels and transforms. No Resolve."""

import json
import tempfile
import unittest
from pathlib import Path

from cf import assets as ca
from cf.build import (BuildError, cue_append_infos, cue_plan_from_report, cue_tracks, default_walk_dir, plan_cues, plan_shots,
                      reference_level, source_end, sfx_volume)
from cf.canvas import resolve
from cf.script_schema import from_dict

from library_fixture import IDS, PACK, make_library
from test_script_schema import STYLE

START = 108000
MANIFEST = {"walk": "w", "clips": [{"file": "C30.mov", "fps": 30.0, "duration_s": 33.6, "nb_frames": 1008}]}
CANVAS = resolve(STYLE)


def script(cues_by_shot, ending="reveal_last"):
    shots = []
    for i, cues in enumerate(cues_by_shot):
        sh = {"clip": "C30.mov", "in_s": 3.0 * i, "out_s": 3.0 * i + 3.0, "role": "build"}
        if cues:
            sh["assets"] = cues
        shots.append(sh)
    return from_dict({"schema": "cf-script/1", "walk": "w", "concept": "c", "format": "pov",
                      "target_length_s": 3 * len(shots),
                      "hook": {"type": "pov", "text": "one two three four five", "clip": "C30.mov"},
                      "shots": shots, "ending": ending, "location_tag": "x"})


class CuePlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, cls.footage, cls.db = make_library(Path(cls.tmp.name))
        cls.pack = Path(cls.tmp.name) / "pack"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def plan(self, sc, cuts=None, reference=-14.0, file_fps=None):
        shots, _ = plan_shots(sc, MANIFEST, START, 30, cuts)
        return plan_cues(sc, shots, self.lib, fps=30, canvas=CANVAS, style=STYLE, reference_lufs=reference,
                         reference_source="test", file_fps=file_fps)

    def one(self, ref, **cue):
        cues, _ = self.plan(script([[{"ref": ref, "at_s": 0.0, **cue}], []]))
        return cues

    def test_sfx_cue_goes_on_a3_at_an_absolute_record_frame(self):
        cues, _ = self.plan(script([[], [{"ref": "@sfx/вуш-2", "at_s": 0.5}], []]))
        (c,) = cues
        self.assertEqual((c.cue, c.shot, c.canonical, c.asset_id), ("s02.1", "s02", "@sfx/вуш-2", IDS["whoosh"]))
        self.assertEqual((c.record_offset, c.record_frame), (105, START + 105))
        self.assertEqual((c.lane, c.track_type, c.track_index, c.media_type), ("A3", "audio", 3, 2))
        self.assertEqual((c.src_start, c.src_end, c.duration, c.record_end), (0, 9, 9, START + 114))
        self.assertEqual(c.path, str(self.pack / "sfx/вуш 2.mp3"))

    def test_cue_follows_its_shot_when_cuts_json_moves_it(self):
        sc = script([[], [{"ref": "@sfx/вуш-2", "at_s": 0.5}], []])
        cuts = {"fps": 30, "shots": [{"id": "s01", "record_frame_offset": 0, "duration_frames": 96},
                                     {"id": "s02", "record_frame_offset": 96, "duration_frames": 84},
                                     {"id": "s03", "record_frame_offset": 180, "duration_frames": 90}]}
        (c,), _ = self.plan(sc, cuts)
        self.assertEqual(c.record_frame, START + 111)

    def test_visual_variants(self):
        (face,) = self.one("@face/шок")
        self.assertEqual((face.path, face.variant), (str(self.pack / "face-resolve/1750738_sticker.mov"), "alpha"))
        self.assertEqual((face.lane, face.track_index, face.media_type), ("V4", 4, 1))
        self.assertEqual((face.duration, face.src_end), (63, 63))
        (emoji,) = self.one("@emoji/в-шоке")
        self.assertEqual((emoji.path, emoji.variant),
                         (str(self.footage / "library" / PACK / "keyed" / f"{IDS['emoji']}.mov"), "keyed"))
        (img,) = self.one("@img/фон-1")
        self.assertEqual((img.path, img.variant), (str(self.footage / f"library/{PACK}/png/{IDS['img']}.png"), "png"))
        self.assertEqual((img.duration, img.src_end), (45, 45))
        cues, notes = self.plan(script([[{"ref": "@face/1750770-sticker", "at_s": 0.0}], []]))
        self.assertEqual((cues[0].variant, cues[0].path),
                         ("still", str(self.pack / "face-resolve/still — улыбка — 1750770_sticker.png")))
        self.assertTrue(any("placing the still png" in n for n in notes), notes)
        (silent,) = self.one("@meme/silent")
        self.assertEqual((silent.path, silent.variant), (str(self.pack / "memes/silent.mp4"), "original"))

    def test_video_cue_source_frames_at_the_file_fps(self):
        path = str(self.pack / "memes/silent.mp4")
        sc = script([[{"ref": "@meme/silent", "at_s": 0.0, "dur_s": 1.0}], []])
        (c,), _ = self.plan(sc, file_fps={path: 60.0})
        self.assertEqual((c.duration, c.src_end, c.file_fps), (30, 60, 60.0))
        (c,), _ = self.plan(sc, file_fps={path: 29.97})
        self.assertEqual(c.src_end, source_end(0, 30, 29.97, 30))

    def test_levels_from_track_loudness_asset_loudness_and_db(self):
        lo = {"i": -22.0, "tp": -10.0, "method": "loudnorm"}
        self.assertEqual(sfx_volume(-11.0, lo, None, STYLE)["volume_db"], 5.0)
        self.assertEqual(sfx_volume(-11.0, lo, -3, STYLE)["volume_db"], 2.0)
        capped = sfx_volume(-11.0, {**lo, "tp": -3.0}, None, STYLE)
        self.assertEqual((capped["volume_db"], capped["capped"], capped["raw_db"]), (2.0, "true_peak", 5.0))
        loud = sfx_volume(-11.0, {"i": -60.0, "tp": None, "method": "loudnorm"}, None, STYLE)
        self.assertEqual((loud["volume_db"], loud["capped"]), (12.0, "range"))
        self.assertIsNone(sfx_volume(-11.0, lo, None, STYLE)["capped"])

    def test_without_a_track_the_reference_is_the_target(self):
        self.assertEqual(reference_level(STYLE, None), (-14.0, "style.audio.target_lufs"))
        self.assertEqual(reference_level(STYLE, -11.3), (-11.3, "track"))

    def test_meme_with_sound_is_a_v4_and_a3_pair(self):
        cues, _ = self.plan(script([[{"ref": "@meme/chipi", "at_s": 0.2, "dur_s": 2.0, "db": -3}], []]),
                            reference=-11.0)
        v, a = sorted(cues, key=lambda c: c.media_type)
        self.assertEqual((v.lane, a.lane, v.cue, a.cue), ("V4", "A3", "s01.1", "s01.1"))
        for k in ("record_frame", "duration", "src_start", "src_end", "path"):
            self.assertEqual(getattr(v, k), getattr(a, k), k)
        self.assertEqual(a.volume_db, -11.0 - 6 + 16.0 - 3)
        self.assertIsNone(v.volume_db)
        self.assertEqual(v.transform["pos"], "center")
        self.assertIsNone(a.transform)

    def test_transform_for_pos_presets(self):
        box = ca.pos_box(STYLE, CANVAS, "center")
        self.assertEqual(ca.transform(512, 512, box, 2160, 3840), {"ZoomX": 0.4444, "ZoomY": 0.4444, "Pan": 0.0,
                                                                  "Tilt": 120.0})
        self.assertEqual(ca.transform(1920, 1080, "cover", 2160, 3840),
                         {"ZoomX": 3.1605, "ZoomY": 3.1605, "Pan": 0.0, "Tilt": 0.0})
        land = resolve(STYLE, "landscape")
        got = ca.transform(512, 512, ca.pos_box(STYLE, land, "bottom-left"), 3840, 2160)
        self.assertEqual(got, {"ZoomX": 0.3704, "ZoomY": 0.3704, "Pan": -1300.0, "Tilt": -400.0})
        (face,) = self.one("@face/шок")
        self.assertEqual(face.transform, {"pos": "bottom-left", "ZoomX": 0.3704, "ZoomY": 0.3704, "Pan": -520.0,
                                          "Tilt": -160.0})

    def test_overlapping_cues_get_the_second_lane_and_a_third_fails(self):
        cues, _ = self.plan(script([[{"ref": "@sfx/own-hit", "at_s": 0.0}, {"ref": "@sfx/вуш-2", "at_s": 0.2},
                                     {"ref": "@face/шок", "at_s": 0.0}, {"ref": "@meme/silent", "at_s": 0.1}],
                                    [{"ref": "@sfx/вуш-2-2", "at_s": 0.0}]]))
        lanes = {c.canonical: c.lane for c in cues}
        self.assertEqual(lanes, {"@sfx/own-hit": "A3", "@sfx/вуш-2": "A4", "@face/шок": "V4", "@meme/silent": "V5",
                                 "@sfx/вуш-2-2": "A3"})
        self.assertEqual(cue_tracks(cues), {"video": 5, "audio": 4})
        with self.assertRaisesRegex(BuildError, "third"):
            self.plan(script([[{"ref": "@sfx/own-hit", "at_s": 0.0}, {"ref": "@sfx/вуш-2", "at_s": 0.2},
                               {"ref": "@sfx/вуш-2-2", "at_s": 0.1}], []]))

    def test_cue_past_the_end_fails_and_a_loop_clear_miss_is_a_note(self):
        sc = script([[], [{"ref": "@sfx/own-hit", "at_s": 2.0}]])
        cuts = {"fps": 30, "shots": [{"id": "s01", "record_frame_offset": 0, "duration_frames": 90},
                                     {"id": "s02", "record_frame_offset": 90, "duration_frames": 80}]}
        with self.assertRaisesRegex(BuildError, "past the end of the Reel"):
            self.plan(sc, cuts)
        sc = script([[], [{"ref": "@face/шок", "at_s": 0.5, "dur_s": 2.3}]], ending="loop_seamless")
        cues, notes = self.plan(sc)
        self.assertEqual(len(cues), 1)
        self.assertTrue(any("loop seam" in n for n in notes), notes)

    def test_no_cues_plan_nothing_and_need_no_library(self):
        sc = script([[], []])
        shots, _ = plan_shots(sc, MANIFEST, START, 30)
        self.assertEqual(plan_cues(sc, shots, None, fps=30, canvas=CANVAS, style=STYLE, reference_lufs=-14.0,
                                   reference_source="x"), ([], []))
        self.assertEqual(cue_tracks([]), {"video": 3, "audio": 1})
        self.assertEqual(cue_tracks([], base_audio=2), {"video": 3, "audio": 2})
        with self.assertRaisesRegex(BuildError, "Library"):
            sc = script([[{"ref": "@sfx/own-hit", "at_s": 0.0}], []])
            plan_cues(sc, plan_shots(sc, MANIFEST, START, 30)[0], None, fps=30, canvas=CANVAS, style=STYLE,
                      reference_lufs=-14.0, reference_source="x")

    def test_cue_plan_round_trips_through_the_build_report(self):
        from dataclasses import asdict

        cues, _ = self.plan(script([[{"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 1.0}], []]))
        report = json.loads(json.dumps({"cue_plan": [asdict(c) for c in cues]}))
        self.assertEqual(cue_plan_from_report(report), cues)
        self.assertEqual(cue_plan_from_report({}), [])
        self.assertEqual(cue_plan_from_report({"cue_plan": [{"cue": "x"}]}), [])

    def test_cue_append_infos(self):
        cues, _ = self.plan(script([[{"ref": "@meme/chipi", "at_s": 0.0, "dur_s": 1.0}], []]))
        items = {cues[0].path: "MPI"}
        got = cue_append_infos(cues, items)
        self.assertEqual(sorted(got, key=lambda d: d["mediaType"]), [
            {"mediaPoolItem": "MPI", "startFrame": 0, "endFrame": 30, "mediaType": 1, "trackIndex": 4,
             "recordFrame": START},
            {"mediaPoolItem": "MPI", "startFrame": 0, "endFrame": 30, "mediaType": 2, "trackIndex": 3,
             "recordFrame": START}])


class NoAssetsBuildTest(unittest.TestCase):
    def test_no_assets_builds_a_cue_script_without_the_library(self):
        from cf.build import Builder
        from test_script_schema import MANIFEST as SCHEMA_MANIFEST, good

        with tempfile.TemporaryDirectory() as t:
            walk = Path(t) / "test-walk"
            reel = walk / "reels/r1"
            reel.mkdir(parents=True)
            (walk / "clip_manifest.json").write_text(json.dumps(SCHEMA_MANIFEST))
            d = good()
            d["shots"][0]["assets"] = [{"ref": "@sfx/own-hit", "at_s": 0.0}]
            (reel / "script.json").write_text(json.dumps(d))
            none = Path(t) / "none.db"
            b = Builder(reel, walk, None, stills=False, footage_root=Path(t), db_path=none, use_assets=False)
            b.validate()
            self.assertIn("--no-assets: the Script's Asset cues are left out of this build", b.r.notes)
            self.assertFalse(b.cues_on())
            with self.assertRaisesRegex(BuildError, "need the Library"):
                Builder(reel, walk, None, stills=False, footage_root=Path(t), db_path=none).validate()


class WalkDirTest(unittest.TestCase):
    def test_default_walk_dir_for_legacy_reels_and_video_folders(self):
        sc = script([[]])
        with tempfile.TemporaryDirectory() as t:
            f = Path(t)
            reel = f / "potsdam/reels/reel-01"
            reel.mkdir(parents=True)
            self.assertEqual(default_walk_dir(reel, sc), f / "potsdam")
            video = f / "videos/boat"
            video.mkdir(parents=True)
            (video / "video.json").write_text(json.dumps({"format": "walk-reel"}))
            self.assertEqual(default_walk_dir(video, sc), f / "w")
            loose = f / "elsewhere/x"
            loose.mkdir(parents=True)
            self.assertEqual(default_walk_dir(loose, sc), f)


if __name__ == "__main__":
    unittest.main()
