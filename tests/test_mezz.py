"""cf.mezz: which clips get an Apple SDR mezzanine, the cache, and (on a Mac with the tool built)
tools/apple-sdr on a small synthetic HLG clip."""

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cf import mezz
from cf.build import STYLE_PATH
from cf.script_schema import load_json

HLG_CLIP = {"file": "IMG_0477.MOV", "color_profile": "iphone_hlg_dv", "color_transfer": "arib-std-b67",
            "resolve_input_color_space": "Rec.2020 HLG ARIB STD-B67"}
SDR_CLIP = {"file": "DJI_0001.MP4", "color_profile": "rec709", "color_transfer": "bt709",
            "resolve_input_color_space": "Rec.709 Gamma 2.4"}


class ChoiceTest(unittest.TestCase):
    def test_hdr_detection(self):
        self.assertTrue(mezz.is_hdr(HLG_CLIP))
        self.assertTrue(mezz.is_hdr({"color_profile": "unknown", "color_transfer": "smpte2084"}))
        self.assertFalse(mezz.is_hdr(SDR_CLIP))
        self.assertFalse(mezz.is_hdr({"color_profile": "apple_log"}))

    def test_default_is_apple_sdr_and_style_says_so(self):
        self.assertEqual(mezz.hdr_source_default({}), "apple-sdr")
        self.assertEqual(mezz.hdr_source_default({"color": {"hdr_source": "resolve"}}), "resolve")
        with self.assertRaises(ValueError):
            mezz.hdr_source_default({"color": {"hdr_source": "lut"}})
        # The author's standing rule (2026-10-12): original colour, as on the Mac.
        style = load_json(STYLE_PATH)
        self.assertEqual(mezz.hdr_source_default(style), "apple-sdr")
        self.assertIsNone(style["look"]["lut"])

    def test_hdr_delivery_reads_hlg_through_resolve(self):
        self.assertEqual(mezz.effective_hdr_source("apple-sdr", "sdr"), "apple-sdr")
        self.assertEqual(mezz.effective_hdr_source("apple-sdr", "hdr-hlg"), "resolve")
        self.assertEqual(mezz.effective_hdr_source("resolve", "sdr"), "resolve")
        with self.assertRaises(ValueError):
            mezz.effective_hdr_source("apple", "sdr")

    def test_plan_sources(self):
        footage = Path("/w/potsdam")
        clips = {"IMG_0477.MOV": HLG_CLIP, "DJI_0001.MP4": SDR_CLIP}
        raw = {"IMG_0477.MOV": "/w/potsdam/raw/IMG_0477.MOV", "DJI_0001.MP4": "/w/potsdam/raw/DJI_0001.MP4"}
        plan = mezz.plan_sources(clips, footage, raw, "apple-sdr")
        self.assertEqual(plan["IMG_0477.MOV"], {"path": "/w/potsdam/mezz/IMG_0477.mov", "raw": raw["IMG_0477.MOV"],
                                                "mezz": True, "input_color_space": "Rec.709 Gamma 2.4"})
        self.assertEqual(plan["DJI_0001.MP4"], {"path": raw["DJI_0001.MP4"], "raw": raw["DJI_0001.MP4"],
                                                "mezz": False, "input_color_space": "Rec.709 Gamma 2.4"})
        plan = mezz.plan_sources(clips, footage, raw, "resolve")
        self.assertEqual(plan["IMG_0477.MOV"]["path"], raw["IMG_0477.MOV"])
        self.assertEqual(plan["IMG_0477.MOV"]["input_color_space"], "Rec.2020 HLG ARIB STD-B67")
        self.assertFalse(plan["IMG_0477.MOV"]["mezz"])


class CacheTest(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.src = self.tmp / "raw" / "IMG_1.MOV"
        self.src.parent.mkdir()
        self.src.write_bytes(b"x" * 100)
        self.dst = mezz.mezz_path(self.tmp, "IMG_1.MOV")

    def write(self, **over):
        self.dst.parent.mkdir(exist_ok=True)
        self.dst.write_bytes(b"m")
        meta = {"version": mezz.TOOL_VERSION, "method": mezz.METHOD, "source_file": mezz.source_stamp(self.src)}
        meta.update(over)
        mezz.sidecar_path(self.dst).write_text(json.dumps(meta))

    def test_fresh_only_for_same_source_version_and_method(self):
        self.assertFalse(mezz.is_fresh(self.src, self.dst))
        self.write()
        self.assertTrue(mezz.is_fresh(self.src, self.dst))
        self.write(version="0")
        self.assertFalse(mezz.is_fresh(self.src, self.dst))
        self.write(method="vt709")
        self.assertFalse(mezz.is_fresh(self.src, self.dst))
        self.write()
        self.src.write_bytes(b"y" * 101)
        self.assertFalse(mezz.is_fresh(self.src, self.dst))

    def test_cached_mezz_is_not_remade(self):
        self.write()
        self.assertEqual(mezz.make_mezz(self.src, self.dst)["action"], "cached")


def _probe(path: Path) -> list[dict]:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["streams"]


@unittest.skipUnless(sys.platform == "darwin" and mezz.TOOL.exists() and shutil.which("ffmpeg"),
                     "needs macOS, a built tools/apple-sdr and ffmpeg")
class ToolTest(unittest.TestCase):
    """A 1 s HLG HEVC clip (rotated, with AAC audio) through the real tool."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp())
        cls.src = cls.tmp / "hlg.mov"
        plain = cls.tmp / "plain.mov"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=size=320x180:rate=60:duration=1",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=1", "-vf", "format=yuv420p10le",
             "-c:v", "libx265", "-x265-params", "log-level=error:colorprim=bt2020:transfer=arib-std-b67:colormatrix=bt2020nc",
             "-tag:v", "hvc1", "-color_primaries", "bt2020", "-color_trc", "arib-std-b67", "-colorspace", "bt2020nc",
             "-c:a", "aac", "-shortest", str(plain)],
            check=True)
        # A stream copy with -display_rotation writes the rotation matrix (as an iPhone clip has).
        subprocess.run(["ffmpeg", "-v", "error", "-display_rotation", "90", "-i", str(plain), "-c", "copy",
                        str(cls.src)], check=True)
        cls.dst = cls.tmp / "mezz" / "hlg.mov"
        cls.meta = mezz.make_mezz(cls.src, cls.dst)

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_prores_hq_rec709_same_size_fps_and_rotation(self):
        v = next(s for s in _probe(self.dst) if s["codec_type"] == "video")
        self.assertEqual((v["codec_name"], v["profile"]), ("prores", "HQ"))
        self.assertEqual((v["width"], v["height"]), (320, 180))
        self.assertEqual(v["r_frame_rate"], "60/1")
        self.assertEqual((v["color_primaries"], v["color_transfer"], v["color_space"]), ("bt709", "bt709", "bt709"))
        src_v = next(s for s in _probe(self.src) if s["codec_type"] == "video")
        rot = [d.get("rotation") for d in v.get("side_data_list", []) if "rotation" in d]
        src_rot = [d.get("rotation") for d in src_v.get("side_data_list", []) if "rotation" in d]
        self.assertEqual(rot, src_rot)
        self.assertEqual(int(v["nb_frames"]), int(src_v["nb_frames"]))

    def test_audio_copied_and_sidecar_written(self):
        a = [s for s in _probe(self.dst) if s["codec_type"] == "audio"]
        self.assertEqual([s["codec_name"] for s in a], ["aac"])
        self.assertEqual(self.meta["action"], "made")
        self.assertEqual(self.meta["method"], "colorsync")
        self.assertTrue(mezz.is_fresh(self.src, self.dst))
        self.assertFalse((self.tmp / "mezz" / "hlg.partial.mov").exists())


if __name__ == "__main__":
    unittest.main()
