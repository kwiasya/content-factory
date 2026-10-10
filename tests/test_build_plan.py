"""Pure planning tests for cf.build: Script + manifest -> AppendToTimeline infos. No Resolve."""

import unittest

from cf.build import BuildError, append_infos, plan_shots, source_end, timecode
from cf.script_schema import from_dict

START = 108000  # 01:00:00:00 at 30 fps (read from GetStartFrame() in a real build)
MANIFEST = {
    "walk": "w",
    "clips": [
        {"file": "A60.MOV", "fps": 60.0, "duration_s": 13.1, "nb_frames": 786, "path": "/raw/A60.MOV"},
        {"file": "B24.MOV", "fps": 24.0, "duration_s": 29.2, "nb_frames": 701, "path": "/raw/B24.MOV"},
        {"file": "C30.mov", "fps": 30.0, "duration_s": 33.6, "nb_frames": 1008, "path": "/raw/C30.mov"},
        {"file": "D5994.MOV", "fps": 59.94006, "duration_s": 16.84, "nb_frames": 1009, "path": "/raw/D5994.MOV"},
    ],
}


def script(shots):
    return from_dict({
        "schema": "cf-script/1", "walk": "w", "concept": "c", "format": "pov", "target_length_s": 10,
        "hook": {"type": "pov", "text": "one two three four five", "clip": shots[0]["clip"]},
        "shots": shots, "ending": "reveal_last", "location_tag": "x",
    })


def shot(clip, a, b, **kw):
    return {"clip": clip, "in_s": a, "out_s": b, "role": kw.pop("role", "build"), **kw}


class SourceFrameMathTest(unittest.TestCase):
    def test_60fps_clip_takes_two_source_frames_per_timeline_frame(self):
        plan, _ = plan_shots(script([shot("A60.MOV", 2.0, 5.0)]), MANIFEST, START, 30)
        (p,) = plan
        self.assertEqual((p.src_start, p.src_end, p.duration), (120, 300, 90))
        self.assertIsInstance(p.src_end, int)

    def test_24fps_clip_whole_frames(self):
        plan, _ = plan_shots(script([shot("B24.MOV", 1.0, 3.5)]), MANIFEST, START, 30)
        (p,) = plan
        self.assertEqual((p.src_start, p.src_end, p.duration), (24, 84, 75))  # 60 source frames = 75 timeline

    def test_24fps_fractional_span_rounds_up_just_enough(self):
        # 77 timeline frames = 61.6 source frames; Resolve floors (end-start)*30/24, so a
        # float end a hair above 61.6 lays exactly 77 frames.
        end = source_end(0, 77, 24.0, 30)
        self.assertGreater(end, 61.6)
        self.assertLess(end, 61.61)
        self.assertEqual(int((end - 0) * 30 / 24), 77)
        for dur in range(1, 200):
            e = source_end(10, dur, 24.0, 30)
            self.assertEqual(int((e - 10) * 30 / 24), dur, dur)

    def test_endframe_is_exclusive(self):
        # duration (timeline) = (endFrame - startFrame) * tl_fps / clip_fps, no +1
        plan, _ = plan_shots(script([shot("C30.mov", 0.0, 3.0)]), MANIFEST, START, 30)
        (p,) = plan
        self.assertEqual(p.src_end - p.src_start, p.duration)
        self.assertEqual((p.src_start, p.src_end), (0, 90))

    def test_resolve_fps_overrides_manifest(self):
        # Resolve 21.1.1 reads a 60000/1001 iPhone clip as FPS 60.0.
        s = script([shot("D5994.MOV", 1.0, 4.0)])
        plan, _ = plan_shots(s, MANIFEST, START, 30, clip_fps={"D5994.MOV": 60.0})
        self.assertEqual((plan[0].src_start, plan[0].src_end), (60, 240))
        plan, _ = plan_shots(s, MANIFEST, START, 30)
        self.assertEqual(plan[0].src_start, 60)
        self.assertAlmostEqual(plan[0].src_end, 60 + 90 * 59.94006 / 30, places=2)

    def test_speed_keeps_timeline_duration_and_scales_source(self):
        # 1.5 s of 60 fps source at 0.5x -> 3 s on the timeline. Appended at 100 % for 90
        # timeline frames (180 source frames); SetSpeed(50) then keeps 90 frames and shows 90.
        plan, _ = plan_shots(script([shot("A60.MOV", 2.0, 3.5, speed=0.5)]), MANIFEST, START, 30)
        (p,) = plan
        self.assertEqual(p.duration, 90)
        self.assertEqual((p.src_start, p.src_end, p.src_end_after_speed), (120, 300, 210))


class RecordFrameTest(unittest.TestCase):
    def test_back_to_back_absolute_record_frames(self):
        s = script([shot("A60.MOV", 0.0, 2.5, role="hook"), shot("B24.MOV", 0.0, 3.1),
                    shot("C30.mov", 1.0, 3.9), shot("A60.MOV", 6.0, 9.4, role="payoff")])
        plan, notes = plan_shots(s, MANIFEST, START, 30)
        self.assertEqual([p.record_offset for p in plan], [0, 75, 168, 255])
        self.assertEqual([p.duration for p in plan], [75, 93, 87, 102])
        self.assertEqual([p.record_frame for p in plan], [START, START + 75, START + 168, START + 255])
        for a, b in zip(plan, plan[1:]):
            self.assertEqual(a.record_end, b.record_frame)
        self.assertTrue(any("back to back" in n for n in notes))

    def test_cumulative_rounding_does_not_drift(self):
        s = script([shot("C30.mov", 0.0, 1.71) for _ in range(10)])
        plan, _ = plan_shots(s, MANIFEST, START, 30)
        self.assertEqual(plan[-1].record_end - START, round(17.1 * 30))

    def test_cuts_json_overrides_record_positions(self):
        s = script([shot("A60.MOV", 0.0, 2.5, role="hook"), shot("B24.MOV", 1.0, 4.0)])
        cuts = {"shots": [{"id": "s01", "record_frame_offset": 0, "duration_frames": 72},
                          {"id": "s02", "record_frame_offset": 72, "duration_frames": 81}]}
        plan, notes = plan_shots(s, MANIFEST, START, 30, cuts=cuts)
        self.assertEqual([(p.record_frame, p.duration) for p in plan], [(START, 72), (START + 72, 81)])
        self.assertEqual(plan[1].src_start, 24)
        self.assertAlmostEqual(plan[1].src_end, 24 + 64.8, places=2)
        self.assertTrue(any("cuts.json" in n for n in notes))

    def test_cuts_json_missing_shot_or_overlap_fails(self):
        s = script([shot("A60.MOV", 0.0, 2.5, role="hook"), shot("B24.MOV", 1.0, 4.0)])
        with self.assertRaises(BuildError):
            plan_shots(s, MANIFEST, START, 30, cuts={"shots": [{"id": "s01", "record_frame_offset": 0,
                                                                "duration_frames": 72}]})
        cuts = {"shots": [{"id": "s01", "record_frame_offset": 0, "duration_frames": 80},
                          {"id": "s02", "record_frame_offset": 72, "duration_frames": 81}]}
        with self.assertRaises(BuildError):
            plan_shots(s, MANIFEST, START, 30, cuts=cuts)


class AppendInfosTest(unittest.TestCase):
    def test_append_dicts(self):
        s = script([shot("A60.MOV", 2.0, 5.0, role="hook"), shot("B24.MOV", 1.0, 3.5)])
        plan, _ = plan_shots(s, MANIFEST, START, 30, raw_dir="/walk/raw")
        items = {"A60.MOV": "<item A>", "B24.MOV": "<item B>"}
        video = append_infos(plan, items, media_type=1)
        self.assertEqual(video, [
            {"mediaPoolItem": "<item A>", "startFrame": 120, "endFrame": 300, "mediaType": 1, "trackIndex": 1,
             "recordFrame": START},
            {"mediaPoolItem": "<item B>", "startFrame": 24, "endFrame": 84, "mediaType": 1, "trackIndex": 1,
             "recordFrame": START + 90},
        ])
        audio = append_infos(plan, items, media_type=2)
        self.assertEqual([a["mediaType"] for a in audio], [2, 2])
        self.assertEqual([a["recordFrame"] for a in audio], [v["recordFrame"] for v in video])
        self.assertEqual(plan[0].path, "/walk/raw/A60.MOV")

    def test_timecode(self):
        self.assertEqual(timecode(108000, 30), "01:00:00:00")
        self.assertEqual(timecode(108000 + 45, 30), "01:00:01:15")
        self.assertEqual(timecode(108000 + 30 * 61 + 7, 30), "01:01:01:07")


if __name__ == "__main__":
    unittest.main()
