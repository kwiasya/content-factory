"""Pure planning tests for cf.build: Script + manifest -> AppendToTimeline infos. No Resolve."""

import unittest
from pathlib import Path

from cf.build import (BuildError, append_infos, beat_marker_plan, loop_seam, plan_shots, plan_track,
                      source_end, still_stats, timecode)
from cf import frames
from cf.script_schema import from_dict

START = 108000  # 01:00:00:00 at 30 fps (read from GetStartFrame() in a real build)
MANIFEST = {
    "walk": "w",
    "clips": [
        {"file": "A60.MOV", "fps": 60.0, "duration_s": 13.1, "nb_frames": 786, "path": "/raw/A60.MOV"},
        {"file": "B24.MOV", "fps": 24.0, "duration_s": 29.2, "nb_frames": 701, "path": "/raw/B24.MOV"},
        {"file": "C30.mov", "fps": 30.0, "duration_s": 33.6, "nb_frames": 1008, "path": "/raw/C30.mov"},
        {"file": "D2997.mp4", "fps": 29.97003, "duration_s": 383.783, "nb_frames": 11497, "path": "/raw/D2997.mp4"},
        {"file": "D5994.MOV", "fps": 59.94006, "duration_s": 16.84, "nb_frames": 1009, "path": "/raw/D5994.MOV"},
    ],
}


def script(shots, **extra):
    return from_dict({
        "schema": "cf-script/1", "walk": "w", "concept": "c", "format": "pov", "target_length_s": 10,
        "hook": {"type": "pov", "text": "one two three four five", "clip": shots[0]["clip"]},
        "shots": shots, "ending": "reveal_last", "location_tag": "x", **extra,
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
        # At 59.94 fps, frames 60..239.76 hold 89.94 timeline frames: snapped down to 89.
        self.assertEqual(plan[0].duration, 89)
        self.assertAlmostEqual(plan[0].src_end, 60 + 89 * 59.94006 / 30, places=2)

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

    def test_each_shot_snaps_down_and_the_next_starts_at_the_snapped_end(self):
        # 1.71 s = 51.3 frames: every shot gets 51 (never 52, which would show source past
        # out_s), and the next record frame follows the snapped duration, so nothing overlaps
        # and no shot is stretched to absorb the rounding.
        s = script([shot("C30.mov", 0.0, 1.71) for _ in range(10)])
        plan, notes = plan_shots(s, MANIFEST, START, 30)
        self.assertEqual([p.duration for p in plan], [51] * 10)
        self.assertEqual([p.record_offset for p in plan], [51 * i for i in range(10)])
        self.assertEqual(plan[-1].record_end - START, 510)
        self.assertTrue(all(p.src_end <= 1.71 * 30 for p in plan))
        self.assertTrue(any("snapped down" in n for n in notes))

    def test_24fps_snapping_never_extends_past_out(self):
        # IMG_0493-like 24 fps clip on a 30 fps timeline. 1.25-4.5 s = 97.5 timeline frames
        # -> 97; source end 30 + 97 x 0.8 = 107.6 (+0.001) stays below out frame 108.
        # An in-point between frames (1.26 s = frame 30.24) starts at frame 31, not 30.
        s = script([shot("B24.MOV", 1.25, 4.5, role="hook"), shot("B24.MOV", 1.26, 4.5),
                    shot("A60.MOV", 0.0, 2.0)])
        plan, _ = plan_shots(s, MANIFEST, START, 30)
        a, b, c = plan
        self.assertEqual((a.src_start, a.duration), (30, 97))
        self.assertLessEqual(a.src_end, 108)
        self.assertEqual(int((a.src_end - a.src_start) * 30 / 24), 97)
        self.assertEqual((b.src_start, b.duration), (31, 96))  # (108 - 31) / 24 s = 96.25 frames
        self.assertLessEqual(b.src_end, 108)
        self.assertEqual([p.record_offset for p in plan], [0, 97, 193])
        self.assertEqual(c.duration, 60)

    def test_four_decimal_times_land_on_their_frames(self):
        # 6.8667 s is 412.002 frames at 60 fps and 9.2667 s is 556.002: frame 412, 72 frames.
        # 22.1667 s at 24 fps is frame 532.0008 -> 532; 16.9833 s (rounded down) still holds 43.
        s = script([shot("A60.MOV", 6.8667, 9.2667, role="hook"), shot("B24.MOV", 22.1667, 23.5667),
                    shot("A60.MOV", 15.55, 16.9833)])
        plan, _ = plan_shots(s, MANIFEST, START, 30)
        self.assertEqual([(p.src_start, p.duration) for p in plan], [(412, 72), (532, 42), (933, 43)])

    def test_cuts_json_overrides_record_positions(self):
        s = script([shot("A60.MOV", 0.0, 2.5, role="hook"), shot("B24.MOV", 1.0, 4.0)])
        cuts = {"shots": [{"id": "s01", "record_frame_offset": 0, "duration_frames": 72},
                          {"id": "s02", "record_frame_offset": 72, "duration_frames": 81}]}
        plan, notes = plan_shots(s, MANIFEST, START, 30, cuts=cuts)
        self.assertEqual([(p.record_frame, p.duration) for p in plan], [(START, 72), (START + 72, 81)])
        self.assertEqual(plan[1].src_start, 24)
        self.assertAlmostEqual(plan[1].src_end, 24 + 64.8, places=2)
        self.assertTrue(any("cuts.json" in n for n in notes))

    def test_cuts_json_is_the_authority_for_record_frames(self):
        # Gaps and positions come from cuts.json even where back-to-back would differ; the
        # source in-point comes from the cut's src_in_s.
        s = script([shot("A60.MOV", 0.0, 3.0, role="hook"), shot("B24.MOV", 1.0, 4.0)])
        cuts = {"fps": 30, "shots": [
            {"id": "s01", "record_frame_offset": 0, "duration_frames": 74, "src_in_s": 0.5, "src_out_s": 2.9667},
            {"id": "s02", "record_frame_offset": 74, "duration_frames": 72, "src_in_s": 1.25, "src_out_s": 3.65}]}
        plan, notes = plan_shots(s, MANIFEST, START, 30, cuts=cuts)
        self.assertEqual([(p.record_offset, p.duration) for p in plan], [(0, 74), (74, 72)])
        self.assertEqual([p.src_start for p in plan], [30, 30])
        self.assertAlmostEqual(plan[1].src_end, 30 + 72 * 0.8, places=2)
        self.assertTrue(any("s01" in n and "differs" in n for n in notes))

    def test_cuts_json_fps_must_match_and_overlong_cut_is_reported(self):
        s = script([shot("C30.mov", 0.0, 2.0, role="hook")])
        with self.assertRaises(BuildError):
            plan_shots(s, MANIFEST, START, 30, cuts={"fps": 24, "shots": [
                {"id": "s01", "record_frame_offset": 0, "duration_frames": 48}]})
        plan, notes = plan_shots(s, MANIFEST, START, 30, cuts={"fps": 30, "shots": [
            {"id": "s01", "record_frame_offset": 0, "duration_frames": 63}]})
        self.assertEqual(plan[0].duration, 63)
        self.assertTrue(any("3 more" in n for n in notes))

    def test_cuts_json_missing_shot_or_overlap_fails(self):
        s = script([shot("A60.MOV", 0.0, 2.5, role="hook"), shot("B24.MOV", 1.0, 4.0)])
        with self.assertRaises(BuildError):
            plan_shots(s, MANIFEST, START, 30, cuts={"shots": [{"id": "s01", "record_frame_offset": 0,
                                                                "duration_frames": 72}]})
        cuts = {"shots": [{"id": "s01", "record_frame_offset": 0, "duration_frames": 80},
                          {"id": "s02", "record_frame_offset": 72, "duration_frames": 81}]}
        with self.assertRaises(BuildError):
            plan_shots(s, MANIFEST, START, 30, cuts=cuts)


class LoopSeamTest(unittest.TestCase):
    def cuts(self, last_frames: int) -> dict:
        return {"fps": 30, "shots": [
            {"id": "s01", "record_frame_offset": 0, "duration_frames": 75, "src_in_s": 9.3},
            {"id": "s02", "record_frame_offset": 75, "duration_frames": 60, "src_in_s": 2.0},
            {"id": "s03", "record_frame_offset": 135, "duration_frames": last_frames, "src_in_s": 7.8333}]}

    def shots(self):
        return [shot("A60.MOV", 9.3, 11.8, role="hook"), shot("C30.mov", 2.0, 4.0),
                shot("A60.MOV", 7.8333, 9.3, role="loop")]

    def test_run_up_ends_on_the_hooks_first_source_frame(self):
        plan, notes = plan_shots(script(self.shots(), ending="loop_seamless"), MANIFEST, START, 30, self.cuts(44))
        seam = loop_seam(plan)
        self.assertEqual((plan[-1].src_start, seam["next_frame"], seam["first_src_start"]), (470, 558, 558))
        self.assertEqual(seam["last_shown_frame"], 556)  # 60 fps on 30: every other source frame
        self.assertEqual(seam["gap_frames"], 0)
        self.assertTrue(seam["ok"])
        self.assertFalse(any("in-point source frame" in n for n in notes))

    def test_a_frame_too_many_moves_the_run_up_in_point(self):
        # The plan derives the run-up's in-point from the seam, so one more timeline frame in
        # cuts.json starts it two 60 fps source frames earlier instead of breaking the seam.
        plan, notes = plan_shots(script(self.shots(), ending="loop_seamless"), MANIFEST, START, 30, self.cuts(45))
        self.assertEqual(plan[-1].src_start, 468)
        self.assertEqual(loop_seam(plan)["gap_frames"], 0)
        self.assertTrue(any("in-point source frame 470 -> 468" in n for n in notes))
        # Without loop_seamless nothing is derived, and loop_seam reports the skip.
        plan, _ = plan_shots(script(self.shots()), MANIFEST, START, 30, self.cuts(45))
        self.assertEqual(loop_seam(plan)["gap_frames"], -2)  # the run-up would repeat 2 source frames

    def test_2997_seam_from_frames_not_seconds(self):
        # Mallorca reel-01 v1: DJI 30000/1001 on 30 fps. The run-up A 119.1857-120.487 (39 frames)
        # into the hook at frame 3611 started at 3572 by the seconds; Resolve then showed 3609 on its
        # last frame and 3611 next: frame 3610 skipped (probe, stills vs source). From frames it
        # starts at 3573 and its last frame shows 3610.
        hook = shot("D2997.mp4", 120.487, 122.8894, role="hook")
        run = shot("D2997.mp4", 119.1857, 120.487, role="loop")
        s = script([hook, shot("C30.mov", 2.0, 4.0), run])
        plan, _ = plan_shots(s, MANIFEST, START, 30, clip_fps={"D2997.mp4": 29.97})
        self.assertEqual((plan[0].src_start, plan[-1].src_start, plan[-1].duration), (3611, 3572, 39))
        seam = loop_seam(plan)
        self.assertEqual((seam["last_shown_frame"], seam["next_frame"], seam["gap_frames"]), (3609, 3610, 1))
        self.assertFalse(seam["ok"])
        s.ending = "loop_seamless"
        plan, notes = plan_shots(s, MANIFEST, START, 30, clip_fps={"D2997.mp4": 29.97})
        seam = loop_seam(plan)
        self.assertEqual((plan[-1].src_start, seam["last_shown_frame"], seam["gap_frames"]), (3573, 3610, 0))
        self.assertTrue(seam["ok"])
        self.assertTrue(any("3572 -> 3573" in n for n in notes))

    def test_display_model_matches_the_probe(self):
        # Stills from smoke-2997: S=3572 showed 3605..3609 on j=34..38; S=3611 showed 3611, 3612,
        # 3613, 3613 on j=0..3.
        self.assertEqual([frames.shown(3572, j, 29.97, 30) for j in range(34, 39)], [3605, 3606, 3607, 3608, 3609])
        self.assertEqual([frames.shown(3611, j, 29.97, 30) for j in range(4)], [3611, 3612, 3613, 3613])
        self.assertEqual(frames.start_from_left_offset(3575.5719999999565, 29.97, 30), 3572)
        self.assertEqual(frames.start_from_left_offset(3614.611000000041, 29.97, 30), 3611)
        self.assertEqual(frames.run_up_start(3611, 39, 29.97, 30), 3573)
        self.assertEqual(frames.run_up_start(558, 44, 60, 30), 470)
        self.assertEqual(frames.run_up_start(100, 30, 30, 30), 70)
        self.assertEqual(frames.exact_fps(29.97), frames.exact_fps(29.97003))


class TrackPlanTest(unittest.TestCase):
    BEATS = {"intro_end": 1.62, "duration_s": 269.7}

    def test_in_point_from_script_snapped_to_a_frame(self):
        s = script([shot("C30.mov", 0.0, 3.0)], track="track/source.wav", track_in_s=2.12)
        tp, notes = plan_track(s, "/walk/reels/r", START, 475, 30, self.BEATS)
        self.assertEqual(tp.path, "/walk/reels/r/track/source.wav")
        self.assertEqual((tp.src_start, tp.src_end, tp.record_frame, tp.duration), (64, 539, START, 475))
        self.assertEqual(tp.fade_out, 18)  # 0.6 s default
        self.assertTrue(any("snapped" in n for n in notes))

    def test_default_in_point_is_intro_end_and_fade_from_script(self):
        s = script([shot("C30.mov", 0.0, 3.0)], track="/abs/t.wav", track_fade_out_s=1.0)
        tp, _ = plan_track(s, "/r", START, 90, 30, self.BEATS)
        self.assertEqual((tp.path, tp.in_source, tp.src_start, tp.fade_out),
                         ("/abs/t.wav", "beats.json intro_end", round(1.62 * 30), 30))
        tp, notes = plan_track(s, "/r", START, 90, 30, None)
        self.assertEqual(tp.src_start, 0)
        self.assertTrue(notes)

    def test_track_too_short_fails(self):
        s = script([shot("C30.mov", 0.0, 3.0)], track="t.wav", track_in_s=268.0)
        with self.assertRaises(BuildError):
            plan_track(s, "/r", START, 90, 30, self.BEATS)

    def test_beat_markers_inside_the_timeline(self):
        cuts = {"beat_markers": [{"frame": -1, "downbeat": True, "beat_index": 0},
                                 {"frame": 15, "downbeat": True, "beat_index": 2, "t": 0.5},
                                 {"frame": 31, "downbeat": False, "beat_index": 3, "t": 1.04},
                                 {"frame": 90, "downbeat": False, "beat_index": 9}]}
        got = beat_marker_plan(cuts, 90)
        self.assertEqual([(m["frame"], m["downbeat"]) for m in got], [(15, True), (31, False)])
        self.assertEqual(beat_marker_plan(None, 90), [])


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


class StillStatsTest(unittest.TestCase):
    def test_4k_still_is_compared_at_the_proxy_size(self):
        import tempfile

        import cv2
        import numpy as np

        # 2160x3840 still: top half white, bottom half black, one 1-px white line in the black.
        a = np.zeros((3840, 2160, 3), np.uint8)
        a[:1920] = 255
        a[3000] = 255
        with tempfile.TemporaryDirectory() as tmp:
            f = Path(tmp) / "s.png"
            cv2.imwrite(str(f), a)
            st = still_stats(f, (540, 960))
            self.assertEqual((st["width"], st["height"]), (2160, 3840))
            small = st["at_proxy_size"]
            self.assertEqual((small["width"], small["height"]), (540, 960))
            self.assertAlmostEqual(small["mean_luma"], st["mean_luma"], delta=0.5)
            # The 1-px line is averaged away on the proxy grid; at full size it counts.
            self.assertGreater(st["pct_ge_235"], small["pct_ge_235"])
            self.assertNotIn("at_proxy_size", still_stats(f, (2160, 3840)))


if __name__ == "__main__":
    unittest.main()
