"""The overlay font from a Format line or style.json typography.font, resolved against the Library."""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from cf import assets as ca

from library_fixture import make_library

ROOT = Path(__file__).resolve().parents[1]
FORMAT = "# Format: X\n\n- id: `walk-reel`\n- Overlay font: `@font/komika-title`\n- Ending: loop\n"


class FontTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.lib, cls.footage, cls.db = make_library(Path(cls.tmp.name))
        cls.font = Path(cls.tmp.name) / "pack/fonts/Komika Title.otf"

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def style(self, font=None):
        return {"typography": {"preset": "legacy", "font": font}}

    def test_format_line_wins_over_style_json(self):
        got = ca.overlay_font(self.style("@font/nope"), FORMAT, self.lib, format_id="walk-reel")
        self.assertEqual(got, ca.FontChoice("@font/komika-title", self.font, "format walk-reel"))

    def test_style_json_font_alone(self):
        got = ca.overlay_font(self.style("@font/komika-title"), "# Format\n- id: `x`\n", self.lib)
        self.assertEqual((got.ref, got.path, got.source), ("@font/komika-title", self.font, "style.json"))

    def test_neither_is_none_and_needs_no_library(self):
        self.assertIsNone(ca.overlay_font(self.style(), None, None))
        self.assertIsNone(ca.overlay_font({}, "no font line", None))

    def test_broken_ref_lists_nearest(self):
        with self.assertRaisesRegex(ca.AssetFontError, "no such Asset @font/komika; nearest: @font/komika-title"):
            ca.overlay_font(self.style("@font/komika"), None, self.lib)
        with self.assertRaisesRegex(ca.AssetFontError, "not an Asset ref"):
            ca.overlay_font(self.style("komika"), None, self.lib)

    def test_a_non_font_ref_is_an_error(self):
        with self.assertRaisesRegex(ca.AssetFontError, "is a sfx Asset, not a font"):
            ca.overlay_font(self.style("@sfx/boom"), None, self.lib)

    def test_no_library_with_a_font_set_is_an_error(self):
        with self.assertRaisesRegex(ca.AssetFontError, "needs the Library"):
            ca.overlay_font(self.style("@font/komika-title"), None, None, library_problem="no factory.db at /x")

    def test_a_missing_or_unusable_file_is_an_error(self):
        moved = self.font.with_suffix(".bak")
        self.font.rename(moved)
        try:
            with self.assertRaisesRegex(ca.AssetFontError, "file missing"):
                ca.overlay_font(self.style("@font/komika-title"), None, self.lib)
        finally:
            moved.rename(self.font)

    def test_cli_prints_the_json_line(self):
        v = self.footage / "videos/boat"
        v.mkdir(parents=True, exist_ok=True)
        (v / "video.json").write_text(json.dumps({"format": "walk-reel"}))
        (v / "script.json").write_text("{}")
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        with tempfile.TemporaryDirectory() as t:
            fmt = Path(t) / "walk-reel"
            fmt.mkdir()
            (fmt / "FORMAT.md").write_text(FORMAT)
            res = subprocess.run([sys.executable, "-m", "cf.assets", "font", str(v / "script.json"), "--footage-root",
                                  str(self.footage), "--db", str(self.db), "--formats", t],
                                 capture_output=True, text=True, env=env, cwd=ROOT)
            self.assertEqual(res.returncode, 0, res.stderr)
            self.assertEqual(json.loads(res.stdout.strip().splitlines()[-1]),
                             {"ref": "@font/komika-title", "path": str(self.font), "source": "format walk-reel"})
            (fmt / "FORMAT.md").write_text(FORMAT.replace("komika-title", "komica"))
            res = subprocess.run([sys.executable, "-m", "cf.assets", "font", str(v / "script.json"), "--footage-root",
                                  str(self.footage), "--db", str(self.db), "--formats", t],
                                 capture_output=True, text=True, env=env, cwd=ROOT)
            self.assertEqual(res.returncode, 1)
            self.assertIn("nearest: @font/komika-title", res.stderr)


if __name__ == "__main__":
    unittest.main()
