"""Classifier tests on hand-built ffprobe stream dicts and exiftool tag dicts."""

import unittest

from cf.probe import classify, parse_creation_time, parse_rate
from cf.proxy import build_filter, proxy_size

DOVI_8_4 = {
    "side_data_type": "DOVI configuration record",
    "dv_profile": 8,
    "dv_level": 5,
    "dv_bl_signal_compatibility_id": 4,
}
ROT_M90 = {"side_data_type": "Display Matrix", "rotation": -90}

IPHONE_HLG = {
    "codec_name": "hevc",
    "profile": "Main 10",
    "pix_fmt": "yuv420p10le",
    "color_range": "tv",
    "color_space": "bt2020nc",
    "color_transfer": "arib-std-b67",
    "color_primaries": "bt2020",
    "side_data_list": [DOVI_8_4, ROT_M90],
}
IPHONE_SDR = {
    "codec_name": "hevc",
    "profile": "Main",
    "pix_fmt": "yuvj420p",
    "color_range": "pc",
    "color_space": "bt709",
    "color_transfer": "bt709",
    "color_primaries": "bt709",
    "side_data_list": [ROT_M90],
}
DJI_STREAM = {
    "codec_name": "hevc",
    "pix_fmt": "yuv420p10le",
    "color_range": "tv",
    "color_space": "bt709",
    "color_transfer": "bt709",
    "color_primaries": "bt709",
}
APPLE_EXIF = {"Keys:Make": "Apple", "Keys:Model": "iPhone 16 Pro"}
DJI_EXIF = {"QuickTime:Make": "DJI", "QuickTime:Model": "Osmo Pocket 4"}


class ClassifyTest(unittest.TestCase):
    def test_iphone_hlg_dolby_vision(self):
        r = classify(IPHONE_HLG, APPLE_EXIF)
        self.assertEqual(r["color_profile"], "iphone_hlg_dv")
        self.assertEqual(r["confidence"], "high")
        self.assertEqual(r["resolve_input_color_space"], "Rec.2100 HLG (Scene)")
        self.assertIn("arib-std-b67", r["source_field"])

    def test_iphone_sdr(self):
        r = classify(IPHONE_SDR, {"Keys:Make": "Apple", "Keys:Model": "iPhone 15 Pro Max"})
        self.assertEqual(r["color_profile"], "rec709")
        self.assertEqual(r["confidence"], "high")
        self.assertEqual(r["resolve_input_color_space"], "Rec.709 Gamma 2.4")

    def test_bt709_with_dovi_is_not_sdr(self):
        stream = dict(IPHONE_SDR, side_data_list=[DOVI_8_4])
        r = classify(stream, APPLE_EXIF)
        self.assertNotEqual(r["color_profile"], "rec709")
        self.assertEqual(r["confidence"], "low")
        self.assertIsNone(r["resolve_input_color_space"])

    def test_dji_with_gamma_tag(self):
        cases = {
            "D-Log": "dji_dlog",
            "D-Log2": "dji_dlog2",
            "Rec.709": "rec709",
            "HLG": "hlg",
        }
        for value, profile in cases.items():
            with self.subTest(value=value):
                exif = dict(DJI_EXIF, **{"QuickTime:DjiCameraColorGammaSxS": value})
                r = classify(DJI_STREAM, exif)
                self.assertEqual(r["color_profile"], profile)
                self.assertEqual(r["confidence"], "high")
                self.assertIsNotNone(r["resolve_input_color_space"])
                self.assertIn("ColorGammaSxS", r["source_field"])

    def test_dji_raw_key_name(self):
        exif = dict(DJI_EXIF, **{"Keys:com.dji.camera.ColorGammaSxS": "D-Log2"})
        r = classify(DJI_STREAM, exif)
        self.assertEqual(r["color_profile"], "dji_dlog2")
        self.assertEqual(r["confidence"], "high")

    def test_dji_without_tag_is_low(self):
        r = classify(DJI_STREAM, DJI_EXIF)
        self.assertEqual(r["color_profile"], "unknown_dji")
        self.assertEqual(r["confidence"], "low")
        self.assertIsNone(r["resolve_input_color_space"])

    def test_apple_log_guess(self):
        stream = {"codec_name": "prores", "color_primaries": "bt2020", "color_transfer": None, "color_space": "bt2020nc"}
        r = classify(stream, APPLE_EXIF)
        self.assertEqual(r["color_profile"], "apple_log")
        self.assertEqual(r["confidence"], "medium")
        self.assertEqual(r["resolve_input_color_space"], "Apple Log")


class HelpersTest(unittest.TestCase):
    def test_parse_rate(self):
        self.assertEqual(parse_rate("60/1"), 60.0)
        self.assertAlmostEqual(parse_rate("58950/983"), 59.9695, places=3)
        self.assertIsNone(parse_rate("0/0"))

    def test_creation_time_prefers_keys_with_tz(self):
        exif = {"Keys:CreationDate": "2026:10:04 14:53:32+02:00", "QuickTime:CreateDate": "2026:10:04 12:53:32"}
        self.assertEqual(parse_creation_time(exif, {}), ("2026-10-04T14:53:32+02:00", "exiftool:Keys:CreationDate"))

    def test_creation_time_falls_back_to_utc(self):
        iso, src = parse_creation_time({"QuickTime:CreateDate": "2026:10:04 12:53:32"}, {})
        self.assertEqual(iso, "2026-10-04T12:53:32+00:00")
        self.assertIn("QuickTime:CreateDate", src)

    def test_proxy_size_follows_rotation(self):
        self.assertEqual(proxy_size({"width": 1920, "height": 1080, "rotation": -90}), (540, 960))
        self.assertEqual(proxy_size({"width": 3840, "height": 2160, "rotation": 90}), (540, 960))
        self.assertEqual(proxy_size({"width": 1920, "height": 1080, "rotation": 0}), (960, 540))

    def test_hdr_filter_chain(self):
        clip = {"width": 1920, "height": 1080, "rotation": -90, "color_profile": "iphone_hlg_dv", "color_range": "tv"}
        vf, approx = build_filter(clip, has_zscale=True)
        self.assertFalse(approx)
        self.assertIn("tonemap=hable", vf)
        vf, approx = build_filter(clip, has_zscale=False)
        self.assertTrue(approx)
        self.assertNotIn("zscale", vf)


if __name__ == "__main__":
    unittest.main()
