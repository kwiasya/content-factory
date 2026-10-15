"""Classifier tests on hand-built ffprobe stream dicts and exiftool tag dicts."""

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf import probe
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
        self.assertEqual(r["resolve_input_color_space"], "Rec.2020 HLG ARIB STD-B67")
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


class ListClipsThroughLinksTest(unittest.TestCase):
    def test_symlinked_clips_are_listed_and_the_footage_is_the_raw_parent(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            source = base / "vienna"
            source.mkdir()
            (source / "DJI_0001.MP4").write_bytes(b"v")
            (source / "IMG_0001.JPG").write_bytes(b"s")
            raw = base / "vienna-2026-07-31" / "raw"
            raw.mkdir(parents=True)
            for name in ("DJI_0001.MP4", "IMG_0001.JPG"):
                (raw / name).symlink_to(source / name)
            self.assertEqual([p.name for p in probe.list_clips(raw)], ["DJI_0001.MP4"])
            with mock.patch.object(probe, "run_exiftool", return_value={}), \
                    mock.patch.object(probe, "probe_clip", side_effect=lambda p, exif: {"path": str(p.resolve())}):
                manifest = probe.build_manifest(raw)
            self.assertEqual(manifest["footage"], "vienna-2026-07-31")
            self.assertNotIn("walk", manifest)
            self.assertEqual(manifest["clips"], [{"path": str(source / "DJI_0001.MP4")}])


class DanglingLinksTest(unittest.TestCase):
    def test_dangling_links_stop_probe_and_keep_the_old_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp).resolve()
            raw = base / "town-2026-07-31" / "raw"
            raw.mkdir(parents=True)
            (base / "ok.MP4").write_bytes(b"v")
            (raw / "ok.MP4").symlink_to(base / "ok.MP4")
            (raw / "gone.MP4").symlink_to(base / "unplugged" / "gone.MP4")
            manifest = raw.parent / "clip_manifest.json"
            manifest.write_text('{"kept": true}\n')
            err = io.StringIO()
            with contextlib.redirect_stderr(err), \
                    mock.patch.object(probe, "build_manifest", side_effect=AssertionError("must not probe")):
                code = probe.main([str(raw)])
            self.assertEqual(code, 2)
            self.assertIn("gone.MP4 -> " + str(base / "unplugged" / "gone.MP4"), err.getvalue())
            self.assertNotIn("ok.MP4", err.getvalue())
            self.assertEqual(manifest.read_text(), '{"kept": true}\n')
            self.assertEqual(probe.dangling_links(raw), [raw / "gone.MP4"])


if __name__ == "__main__":
    unittest.main()
