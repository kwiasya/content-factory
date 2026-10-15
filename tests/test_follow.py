"""Follow-mode window choice (cf.follow) on synthetic person positions, and the seam grouping. No model."""

import unittest

from cf.build import follow_groups, effective_reframes
from cf.follow import Box, choose_window, coverage, left_for_x, subject_boxes, window_fraction, x_for_left
from cf.script_schema import from_dict

W = window_fraction(3840, 2160, 2160, 3840)  # 0.3164 of the source width


def boxes(*cxs, width=0.1):
    return [None if c is None else Box(t=i * 0.2, x1=c - width / 2, x2=c + width / 2) for i, c in enumerate(cxs)]


class WindowMathTest(unittest.TestCase):
    def test_window_fraction_and_x_mapping(self):
        self.assertAlmostEqual(W, 1215 / 3840)
        self.assertAlmostEqual(window_fraction(3840, 2160, 2160, 3840, zoom=1.35), 1215 / 3840 / 1.35)
        for x in (-1, -0.6, 0, 0.4, 1):
            self.assertAlmostEqual(x_for_left(left_for_x(x, W), W), x)
        self.assertAlmostEqual(left_for_x(-1, W), 0.0)
        self.assertAlmostEqual(left_for_x(1, W) + W, 1.0)


class ChooseWindowTest(unittest.TestCase):
    def test_static_person_is_centred_in_the_window(self):
        r = choose_window(boxes(0.7, 0.71, 0.69, 0.7), W)
        self.assertEqual((r.covered, r.detected, r.coverage_pct, r.fallback), (4, 4, 100.0, None))
        self.assertAlmostEqual(r.left + r.width / 2, 0.70, delta=0.01)
        self.assertGreater(r.x, 0)

    def test_hold_s_keeps_the_end_of_a_crossing_in_the_window(self):
        # Mallorca hook: she walks from 0.55 to 0.25 and smiles at the lens at the end. Without a
        # hold the window keeps the long early stretch; hold_s at the last frame keeps the smile.
        b = boxes(0.56, 0.55, 0.55, 0.54, 0.53, 0.52, 0.50, 0.45, 0.38, 0.30, width=0.16)
        free = choose_window(b, W)
        self.assertNotIn(1.8, free.covered_times)
        held = choose_window(b, W, hold_s=(1.8,))
        self.assertEqual((held.held, held.fallback), ([1.8], None))
        self.assertIn(1.8, held.covered_times)
        self.assertLess(held.coverage_pct, free.coverage_pct)
        self.assertLessEqual(held.left, 0.30 - 0.08 + 1e-9)

    def test_hold_s_that_cannot_fit_is_dropped(self):
        b = boxes(0.1, 0.9, width=0.1)  # 0.8 apart: no window holds both
        r = choose_window(b, W, hold_s=(0.0, 0.2))
        self.assertEqual((r.fallback, r.held), ("hold", []))
        r = choose_window(b, W, hold_s=(5.0,))  # no frame sampled near 5 s
        self.assertEqual(r.fallback, "hold")

    def test_window_never_leaves_the_source(self):
        r = choose_window(boxes(0.02, 0.03, 0.04, width=0.04), W)
        self.assertEqual(r.left, 0.0)
        self.assertEqual(r.x, -1.0)
        r = choose_window(boxes(0.98, 0.97, width=0.04), W)
        self.assertAlmostEqual(r.left + r.width, 1.0, places=6)
        self.assertEqual(r.x, 1.0)

    def test_most_frames_win(self):
        # 3 frames at 0.2, 5 frames at 0.8: the window goes right.
        r = choose_window(boxes(0.2, 0.2, 0.2, 0.8, 0.8, 0.8, 0.8, 0.8), W)
        self.assertEqual(r.covered, 5)
        self.assertGreater(r.left + r.width / 2, 0.6)
        self.assertEqual(r.missed_times, [0.0, 0.2, 0.4])

    def test_ties_go_to_the_end_of_the_shot(self):
        r = choose_window(boxes(0.2, 0.2, 0.2, 0.8, 0.8, 0.8), W)
        self.assertEqual(r.covered, 3)
        self.assertGreater(r.left, 0.5)  # the last three frames (0.8)
        r = choose_window(boxes(0.8, 0.8, 0.8, 0.2, 0.2, 0.2), W)
        self.assertLess(r.left + r.width, 0.5)

    def test_moving_person_takes_the_densest_run(self):
        # Walks from 0.55 to 0.15 (like reel-01 s01): no static window holds all of it.
        r = choose_window(boxes(0.55, 0.52, 0.48, 0.45, 0.40, 0.34, 0.29, 0.23, 0.15, width=0.12), W)
        self.assertLess(r.coverage_pct, 100)
        self.assertGreaterEqual(r.covered, 5)
        self.assertEqual(coverage(boxes(0.55, 0.52, 0.48, 0.45, 0.40, 0.34, 0.29, 0.23, 0.15, width=0.12),
                                  r.left, W)[0], r.covered)

    def test_frames_without_a_person_count_as_frames_not_detections(self):
        r = choose_window(boxes(None, 0.5, None, 0.5), W)
        self.assertEqual((r.frames, r.detected, r.covered, r.coverage_pct), (4, 2, 2, 100.0))

    def test_nobody_gives_the_centre(self):
        r = choose_window(boxes(None, None), W)
        self.assertEqual((r.fallback, r.x, r.coverage_pct), ("no_person", 0.0, 0.0))

    def test_box_wider_than_the_window_falls_back_to_overlap(self):
        r = choose_window(boxes(0.3, 0.31, 0.32, width=0.45), W)
        self.assertEqual((r.fallback, r.covered), ("overlap", 0))
        self.assertAlmostEqual(r.left + r.width / 2, 0.31, delta=0.02)
        self.assertGreaterEqual(r.left, 0.0)


class SubjectBoxesTest(unittest.TestCase):
    def test_subject_is_the_large_persistent_track(self):
        samples = [(0.0, [(1, 0.40, 0.50, 0.6), (2, 0.90, 0.92, 0.05)]),
                   (0.2, [(1, 0.41, 0.51, 0.6), (2, 0.89, 0.91, 0.05)]),
                   (0.4, [(2, 0.88, 0.90, 0.05)]),  # subject missed; the stranger is far away
                   (0.6, [(7, 0.43, 0.53, 0.6)])]   # id switch, near the last centre: rejoined
        out = subject_boxes(samples)
        self.assertEqual([None if b is None else round(b.cx, 2) for b in out], [0.45, 0.46, None, 0.48])

    def test_no_tracks_uses_the_tallest_box(self):
        out = subject_boxes([(0.0, [(None, 0.1, 0.2, 0.2), (None, 0.6, 0.7, 0.5)])])
        self.assertAlmostEqual(out[0].cx, 0.65)


class SeamGroupTest(unittest.TestCase):
    MANIFEST = {"footage": "w", "clips": [
        {"file": "DJI.mp4", "fps": 30.0, "duration_s": 100.0, "display_width": 3840, "display_height": 2160},
        {"file": "B.mp4", "fps": 30.0, "duration_s": 100.0, "display_width": 3840, "display_height": 2160}]}

    def script(self, last_reframe=None, ending="loop_seamless"):
        last = {"clip": "DJI.mp4", "in_s": 8, "out_s": 10, "role": "loop"}
        if last_reframe:
            last["reframe"] = last_reframe
        return from_dict({"schema": "cf-script/1", "footage": "w", "concept": "c", "format": "pov", "target_length_s": 7,
                          "hook": {"type": "pov", "text": "one two three four five", "clip": "DJI.mp4"},
                          "shots": [{"clip": "DJI.mp4", "in_s": 10, "out_s": 12.5, "role": "hook"},
                                    {"clip": "B.mp4", "in_s": 1, "out_s": 3.5, "role": "build"}, last],
                          "ending": ending, "location_tag": "x"})

    def groups(self, sc):
        return follow_groups(sc, effective_reframes(sc, self.MANIFEST, 2160, 3840))

    def test_seam_pair_shares_one_window(self):
        self.assertEqual(self.groups(self.script()), [["s02"], ["s03", "s01"]])

    def test_no_sharing_without_the_loop_or_with_another_mode(self):
        self.assertEqual(self.groups(self.script(ending="reveal_last")), [["s01"], ["s02"], ["s03"]])
        self.assertEqual(self.groups(self.script({"mode": "center"})), [["s01"], ["s02"]])
        self.assertEqual(self.groups(self.script({"mode": "follow", "zoom": 1.2})), [["s01"], ["s02"], ["s03"]])


if __name__ == "__main__":
    unittest.main()
