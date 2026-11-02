"""The measured section of a Reference card, from recorded fixtures: yt-dlp info, stable-ts result, Shot log.

No network, no models, no OCR binary: OCR frames are given inline as tools/vision-score --text prints them.
"""

import copy
import json
import unittest
from pathlib import Path

from cf.research import measure

FIX = Path(__file__).parent / "fixtures" / "research"


def fixture(name: str) -> dict:
    return json.loads((FIX / name).read_text())


INFO = fixture("info_long.json")
TRANSCRIPT = fixture("transcript_long.json")
SHOTLOG = fixture("shotlog_long.json")


class CutsTest(unittest.TestCase):
    def test_cuts_are_seconds_above_the_scene_change_threshold_with_runs_merged(self):
        # fixture: spikes at 4 and 5 (one cut), 9, 40, 90; 8.0 at 20 is below 10; 100 at 0 is the first frame
        self.assertEqual(measure.cut_times(SHOTLOG["per_second"]), [4.0, 9.0, 40.0, 90.0])


    def test_editing_density_from_duration_and_cuts(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG)
        self.assertEqual(m["duration_s"], 120.0)
        self.assertEqual(m["kind"], "short")  # at most 180 s (cf.research.kinds)
        self.assertEqual(m["cut_count"], 4)
        self.assertEqual(m["cuts_per_min"], 2.0)
        self.assertEqual(m["cut_times_s"], [4.0, 9.0, 40.0, 90.0])
        self.assertEqual(m["first_shot_s"], 4.0)

    def test_a_single_take_has_no_cuts_and_one_shot_as_long_as_the_video(self):
        sl = copy.deepcopy(SHOTLOG)
        sl["per_second"]["scd_score"] = [0.0] * 120
        m = measure.measure(INFO, TRANSCRIPT, sl)
        self.assertEqual((m["cut_count"], m["cuts_per_min"], m["first_shot_s"]), (0, 0.0, 120.0))


class PeopleTest(unittest.TestCase):
    def test_first_person_and_first_face_are_the_first_seconds_the_shot_log_saw_them(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG)
        self.assertEqual(m["first_person_s"], 6.0)
        self.assertEqual(m["first_face_s"], 41.0)

    def test_nobody_on_screen_is_null(self):
        sl = copy.deepcopy(SHOTLOG)
        sl["per_second"]["persons"] = [0] * 120
        sl["per_second"]["faces"] = [None] * 120
        m = measure.measure(INFO, TRANSCRIPT, sl)
        self.assertIsNone(m["first_person_s"])
        self.assertIsNone(m["first_face_s"])


class SpeechTest(unittest.TestCase):
    def test_speech_onset_is_the_first_word_and_the_spoken_hook_the_words_begun_in_the_first_3_s(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG)
        self.assertEqual(m["speech_onset_s"], 0.62)
        self.assertEqual(m["spoken_hook"], "So this is Alfama, the oldest part of Lisbon.")
        self.assertEqual(m["language"], "en")

    def test_a_late_first_word_leaves_the_spoken_hook_empty(self):
        tr = copy.deepcopy(TRANSCRIPT)
        tr["segments"] = tr["segments"][1:]
        m = measure.measure(INFO, tr, SHOTLOG)
        self.assertEqual(m["speech_onset_s"], 41.2)
        self.assertEqual(m["spoken_hook"], "")

    def test_no_transcript_means_unknown_speech(self):
        m = measure.measure(INFO, None, SHOTLOG)
        self.assertIsNone(m["speech_onset_s"])
        self.assertIsNone(m["spoken_hook"])


class ChaptersAndHeatmapTest(unittest.TestCase):
    def test_chapters_are_copied_from_the_info(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG)
        self.assertEqual(m["chapters"], [
            {"start_s": 0.0, "end_s": 40.0, "title": "Intro"},
            {"start_s": 40.0, "end_s": 90.0, "title": "Alfama stairs"},
            {"start_s": 90.0, "end_s": 120.0, "title": "Sunset at the viewpoint"},
        ])

    def test_heatmap_peaks_are_runs_above_half_the_maximum_strongest_first_with_their_quotes(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG)
        self.assertEqual(m["heatmap_peaks"], [
            {"start_s": 0.0, "end_s": 12.0, "value": 1.0,
             "quote": "So this is Alfama, the oldest part of Lisbon."},
            {"start_s": 84.0, "end_s": 108.0, "value": 0.63, "quote": "Okay, sunset time."},
        ])

    def test_a_peak_with_nobody_talking_quotes_nothing(self):
        info = copy.deepcopy(INFO)
        info["heatmap"][4]["value"] = 0.9  # 48-60 s: silence between the stairs and the sunset
        peaks = measure.measure(info, TRANSCRIPT, SHOTLOG)["heatmap_peaks"]
        self.assertIn({"start_s": 48.0, "end_s": 60.0, "value": 0.9, "quote": ""}, peaks)

    def test_a_short_without_chapters_or_heatmap_has_empty_lists(self):
        m = measure.measure(fixture("info_short.json"), None, None)
        self.assertEqual((m["chapters"], m["heatmap_peaks"]), ([], []))
        self.assertEqual((m["duration_s"], m["kind"]), (47.0, "short"))
        self.assertIsNone(m["cut_count"])
        self.assertIn("cut_count", m["notes"])
        self.assertIn("speech_onset_s", m["notes"])


# tools/vision-score --text records for the first 2 s at 2 fps
OCR = [
    {"t": 0.0, "text": []},
    {"t": 0.5, "text": [{"s": "ok", "conf": 0.3, "h": 0.02}]},
    {"t": 1.0, "text": [{"s": "|", "conf": 0.9, "h": 0.02}]},
    {"t": 1.5, "text": [{"s": "LISBON IN 60s", "conf": 0.98, "h": 0.06}, {"s": "part 1", "conf": 0.7, "h": 0.03}]},
    {"t": 2.0, "text": [{"s": "LISBON IN 60s", "conf": 0.97, "h": 0.06}]},
]


class OnScreenTextTest(unittest.TestCase):
    def test_first_text_is_the_first_frame_with_a_confident_readable_line(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG, OCR)
        self.assertEqual(m["first_text_s"], 1.5)
        self.assertEqual(m["first_text"], "LISBON IN 60s / part 1")

    def test_no_text_in_the_sampled_seconds_is_null_and_says_how_far_ocr_looked(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG, OCR[:3])
        self.assertIsNone(m["first_text_s"])
        self.assertIn("no on-screen text in the first 1.0 s", m["notes"]["first_text_s"])

    def test_without_ocr_the_text_time_is_null_and_noted(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG, None)
        self.assertIsNone(m["first_text_s"])
        self.assertIn("OCR did not run", m["notes"]["first_text_s"])


class SectionsTest(unittest.TestCase):
    def test_transcript_sections_end_at_sentence_punctuation_or_a_long_pause(self):
        m = measure.measure(INFO, TRANSCRIPT, SHOTLOG)
        self.assertEqual(m["sections"], [
            {"start_s": 0.62, "end_s": 3.9, "text": "So this is Alfama, the oldest part of Lisbon."},
            {"start_s": 41.2, "end_s": 42.3, "text": "Watch the stairs."},
            {"start_s": 90.4, "end_s": 91.8, "text": "Okay, sunset time."},
        ])

    def test_unpunctuated_speech_splits_only_at_pauses_over_1_5_s(self):
        tr = {"language": "en", "segments": [{"words": [
            {"word": " walk", "start": 0.0, "end": 0.4}, {"word": " with", "start": 0.5, "end": 0.7},
            {"word": " me", "start": 1.9, "end": 2.1},   # 1.2 s gap: same section
            {"word": " here", "start": 4.0, "end": 4.3},  # 1.9 s gap: new section
        ]}]}
        self.assertEqual(measure.sections(measure.words(tr)), [
            {"start_s": 0.0, "end_s": 2.1, "text": "walk with me"},
            {"start_s": 4.0, "end_s": 4.3, "text": "here"},
        ])

    def test_common_abbreviations_do_not_end_a_section(self):
        text = ("Try street food, e.g. pastel de nata at 3.50 euros. Ask Dr. Silva or Mr. Costa (i.e. locals) "
                "on St. Paul street, cafes vs. bakeries, etc. Then go.")
        ws = [{"word": " " + w, "start": i * 0.3, "end": i * 0.3 + 0.2} for i, w in enumerate(text.split())]
        self.assertEqual([x["text"] for x in measure.sections(ws)], [
            "Try street food, e.g. pastel de nata at 3.50 euros.",
            "Ask Dr. Silva or Mr. Costa (i.e. locals) on St. Paul street, cafes vs. bakeries, etc. Then go.",
        ])

if __name__ == "__main__":
    unittest.main()
