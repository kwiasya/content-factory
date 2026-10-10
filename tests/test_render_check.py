"""render_check parsing and verdict logic on hand-built ffprobe dicts (no Resolve, no ffmpeg)."""

import unittest
from pathlib import Path

from cf.render import JOB_EXPECT, job_mismatches
from cf.render_check import evaluate, normalized_path, parse_loudnorm, parse_probe, passed, video_duration

GOOD_VIDEO = {
    "codec_type": "video", "codec_name": "h264", "profile": "High", "width": 1080, "height": 1920,
    "pix_fmt": "yuv420p", "color_range": "tv", "color_space": "bt709", "color_transfer": "bt709",
    "color_primaries": "bt709", "r_frame_rate": "30/1", "avg_frame_rate": "30/1", "nb_frames": "705",
    "duration": "23.500000", "bit_rate": "22200000",
}
GOOD_AUDIO = {"codec_type": "audio", "codec_name": "aac", "sample_rate": "48000", "channels": 2,
              "bit_rate": "320000"}
GOOD_FORMAT = {"duration": "23.573333", "size": "66100000", "bit_rate": "22400000"}
LOUD_OK = {"input_i": -14.2, "input_tp": -1.3, "input_lra": 6.4, "input_thresh": -24.8, "target_offset": 0.2}

LOUDNORM_STDERR = """Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'reel-test.mp4':
  Duration: 00:00:23.57, start: 0.000000, bitrate: 22437 kb/s
[Parsed_loudnorm_0 @ 0x600000c94000]
{
	"input_i" : "-29.90",
	"input_tp" : "-8.85",
	"input_lra" : "21.00",
	"input_thresh" : "-44.16",
	"output_i" : "-16.87",
	"output_tp" : "-1.00",
	"output_lra" : "9.30",
	"output_thresh" : "-27.96",
	"normalization_type" : "dynamic",
	"target_offset" : "1.35"
}
"""


def probe(video=None, audio=None, fmt=None, drop_audio=False):
    streams = [dict(GOOD_VIDEO, **(video or {}))]
    if not drop_audio:
        streams.append(dict(GOOD_AUDIO, **(audio or {})))
    return {"streams": streams, "format": dict(GOOD_FORMAT, **(fmt or {}))}


def failing(rows):
    return {r.name for r in rows if not r.ok}


class ParseProbeTest(unittest.TestCase):
    def test_flattens_streams_and_format(self):
        f = parse_probe(probe())
        self.assertEqual((f["width"], f["height"], f["fps"], f["nb_frames"]), (1080, 1920, 30.0, 705))
        self.assertEqual((f["audio_codec"], f["sample_rate"], f["channels"]), ("aac", 48000, 2))
        self.assertAlmostEqual(f["duration"], 23.573333)
        self.assertFalse(f["dovi"])

    def test_ntsc_rate_and_missing_audio(self):
        f = parse_probe(probe(video={"r_frame_rate": "30000/1001"}, drop_audio=True))
        self.assertAlmostEqual(f["fps"], 29.97, places=2)
        self.assertIsNone(f["audio_codec"])
        self.assertIsNone(f["sample_rate"])

    def test_dovi_side_data_detected(self):
        side = [{"side_data_type": "DOVI configuration record", "dv_profile": 8},
                {"side_data_type": "Display Matrix", "rotation": -90}]
        f = parse_probe(probe(video={"side_data_list": side}))
        self.assertTrue(f["dovi"])
        self.assertIn("Display Matrix", f["side_data"])

    def test_video_duration_prefers_frames(self):
        f = parse_probe(probe())
        self.assertEqual(video_duration(f), 23.5)  # not the container's 23.573 (AAC tail)
        f = parse_probe(probe(video={"nb_frames": "N/A", "duration": "23.4"}))
        self.assertEqual(video_duration(f), 23.4)


class ParseLoudnormTest(unittest.TestCase):
    def test_last_json_block_numbers_as_floats(self):
        loud = parse_loudnorm(LOUDNORM_STDERR)
        self.assertEqual(loud["input_i"], -29.9)
        self.assertEqual(loud["input_tp"], -8.85)
        self.assertEqual(loud["target_offset"], 1.35)
        self.assertEqual(loud["normalization_type"], "dynamic")

    def test_no_json_raises(self):
        with self.assertRaises(ValueError):
            parse_loudnorm("Input #0 ...\nno loudnorm here\n")


class EvaluateTest(unittest.TestCase):
    def test_good_file_passes(self):
        rows = evaluate(parse_probe(probe()), LOUD_OK, expect_duration=23.5)
        self.assertTrue(passed(rows), failing(rows))

    def test_untagged_transfer_fails(self):
        # 'Same as Project' GammaTag leaves the transfer unspecified (S8): the 1-2-1 trap.
        rows = evaluate(parse_probe(probe(video={"color_transfer": "unknown"})), LOUD_OK)
        self.assertEqual(failing(rows), {"color transfer"})

    def test_full_range_and_10bit_fail(self):
        rows = evaluate(parse_probe(probe(video={"color_range": "pc", "pix_fmt": "yuv420p10le"})), LOUD_OK)
        self.assertEqual(failing(rows), {"color range", "pixel format"})

    def test_hdr_leftovers_fail(self):
        side = [{"side_data_type": "DOVI configuration record"}]
        rows = evaluate(parse_probe(probe(video={"color_transfer": "arib-std-b67", "color_primaries": "bt2020",
                                                 "color_space": "bt2020nc", "side_data_list": side})), LOUD_OK)
        self.assertEqual(failing(rows), {"color transfer", "color primaries", "color matrix",
                                         "Dolby Vision side data"})

    def test_wrong_size_and_rate_fail(self):
        rows = evaluate(parse_probe(probe(video={"width": 1920, "height": 1080, "r_frame_rate": "60/1"})), LOUD_OK)
        self.assertEqual(failing(rows), {"resolution", "frame rate"})

    def test_audio_format_fails(self):
        rows = evaluate(parse_probe(probe(audio={"codec_name": "pcm_s16le", "sample_rate": "44100"})), LOUD_OK)
        self.assertEqual(failing(rows), {"audio codec", "audio sample rate"})

    def test_loudness_window_and_true_peak(self):
        f = parse_probe(probe())
        self.assertEqual(failing(evaluate(f, dict(LOUD_OK, input_i=-29.9))), {"integrated loudness (LUFS)"})
        self.assertEqual(failing(evaluate(f, dict(LOUD_OK, input_i=-12.9))), {"integrated loudness (LUFS)"})
        self.assertFalse(failing(evaluate(f, dict(LOUD_OK, input_i=-13.1))))
        self.assertEqual(failing(evaluate(f, dict(LOUD_OK, input_tp=-0.68))), {"true peak (dBTP)"})
        # Custom targets.
        self.assertFalse(failing(evaluate(f, dict(LOUD_OK, input_i=-16.2, input_tp=-2.1),
                                          target_lufs=-16, target_tp=-2)))

    def test_no_audio_fails_loudness_rows(self):
        rows = evaluate(parse_probe(probe(drop_audio=True)), None)
        self.assertEqual(failing(rows), {"audio codec", "audio sample rate", "integrated loudness (LUFS)",
                                         "true peak (dBTP)"})

    def test_duration_expectation(self):
        f = parse_probe(probe())
        self.assertFalse(failing(evaluate(f, LOUD_OK, expect_duration=23.45)))
        self.assertEqual(failing(evaluate(f, LOUD_OK, expect_duration=24.0)), {"duration (s)"})


class NamesAndJobsTest(unittest.TestCase):
    def test_normalized_name(self):
        self.assertEqual(normalized_path(Path("/x/out/reel-test.mp4")), Path("/x/out/reel-test.normalized.mp4"))

    def test_job_mismatches(self):
        out = Path("/tmp/reel/out/reel.mp4")
        job = {"FormatWidth": 1080, "FormatHeight": 1920, "FrameRate": "30", "IsExportVideo": True,
               "IsExportAudio": True, "AudioSampleRate": 48000, "TargetDir": "/tmp/reel/out",
               "OutputFilename": "reel.mp4"}
        self.assertEqual(job_mismatches(job, JOB_EXPECT, out), [])
        bad = job_mismatches(dict(job, FrameRate="29.97", OutputFilename="reel_1.mp4"), JOB_EXPECT, out)
        self.assertEqual(len(bad), 2)


if __name__ == "__main__":
    unittest.main()
