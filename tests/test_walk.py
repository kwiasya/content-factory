"""cf.walk init on a temporary source folder and footage root."""

import contextlib
import io
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from cf.walk import main


class WalkInitTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        base = Path(tmp.name).resolve()
        self.source = base / "source"
        self.source.mkdir()
        for name, data in {"A.MP4": b"a", "B.mp4": b"bb", "C.MOV": b"ccc", "D.JPG": b"d", "notes.txt": b"t",
                           ".DS_Store": b"x"}.items():
            (self.source / name).write_bytes(data)
        (self.source / "sub").mkdir()
        self.footage = base / "footage"
        self.footage.mkdir()
        env = mock.patch.dict(os.environ, {"CF_FOOTAGE_ROOT": str(self.footage)})
        env.start()
        self.addCleanup(env.stop)
        self.walk = self.footage / "town-2026-07-31"

    def run_cli(self, *args: str) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = main(["init", *args])
        return code, out.getvalue(), err.getvalue()

    def test_links_clips_and_stills_and_reports_the_rest(self):
        code, out, _ = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 0)
        self.assertEqual(sorted(p.name for p in self.walk.iterdir()), ["proxy", "raw", "shotlog", "stills"])
        raw = sorted(self.walk.glob("raw/*"))
        self.assertEqual([p.name for p in raw], ["A.MP4", "B.mp4", "C.MOV"])
        for p in raw:
            self.assertTrue(p.is_symlink())
            self.assertEqual(p.resolve(), self.source / p.name)
        still = self.walk / "stills" / "D.JPG"
        self.assertTrue(still.is_symlink())
        self.assertEqual(still.read_bytes(), b"d")
        self.assertIn("3 clips linked, 1 stills", out)
        self.assertIn("skipped: notes.txt", out)
        self.assertNotIn(".DS_Store", out)

    def test_second_run_is_a_no_op(self):
        self.run_cli("town-2026-07-31", "--from", str(self.source))
        before = {p.name: os.readlink(p) for p in self.walk.glob("raw/*")}
        code, out, _ = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 0)
        self.assertIn("0 clips linked, 0 stills, 4 already present", out)
        self.assertEqual({p.name: os.readlink(p) for p in self.walk.glob("raw/*")}, before)

    def test_the_same_source_spelled_differently_is_a_no_op(self):
        self.run_cli("town-2026-07-31", "--from", str(self.source))
        alias = self.source.parent / "alias"
        alias.symlink_to(self.source)
        for spelling in (self.source / ".." / "source", alias):
            with self.subTest(spelling=str(spelling)):
                code, out, err = self.run_cli("town-2026-07-31", "--from", str(spelling))
                self.assertEqual(code, 0, err)
                self.assertIn("0 clips linked, 0 stills, 4 already present", out)

    def test_links_point_at_the_resolved_source(self):
        alias = self.source.parent / "alias"
        alias.symlink_to(self.source)
        self.run_cli("town-2026-07-31", "--from", str(alias / ".." / "alias"))
        self.assertEqual(os.readlink(self.walk / "raw" / "A.MP4"), str(self.source / "A.MP4"))

    def test_symlinked_files_in_the_source_keep_their_own_names(self):
        elsewhere = self.source.parent / "elsewhere"
        elsewhere.mkdir()
        (elsewhere / "clip.bin").write_bytes(b"e")
        (self.source / "L.mov").symlink_to("A.MP4")
        (self.source / "M.mp4").symlink_to(self.source / "A.MP4")
        (self.source / "E.MP4").symlink_to(elsewhere / "clip.bin")
        (self.source / "S.png").symlink_to(elsewhere / "clip.bin")
        code, out, err = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 0, err)
        raw = {p.name: p.resolve() for p in (self.walk / "raw").iterdir()}
        self.assertEqual(sorted(raw), ["A.MP4", "B.mp4", "C.MOV", "E.MP4", "L.mov", "M.mp4"])
        self.assertEqual(raw["L.mov"], self.source / "A.MP4")
        self.assertEqual(raw["M.mp4"], self.source / "A.MP4")
        self.assertEqual(raw["E.MP4"], elsewhere / "clip.bin")
        self.assertEqual(sorted(p.name for p in (self.walk / "stills").iterdir()), ["D.JPG", "S.png"])
        self.assertIn("6 clips linked, 2 stills", out)
        code, out, err = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 0, err)
        self.assertIn("0 clips linked, 0 stills, 8 already present", out)

    def test_a_walk_subfolder_that_is_a_file_is_exit_2(self):
        self.walk.mkdir()
        (self.walk / "shotlog").write_text("x")
        code, _, err = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 2)
        self.assertIn("error:", err)

    def test_subfolders_are_reported_and_not_scanned(self):
        code, out, _ = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 0)
        self.assertIn("folders not scanned: sub", out)

    def test_a_card_layout_with_nothing_on_top_is_exit_2_and_creates_nothing(self):
        card = self.source.parent / "card"
        (card / "DCIM" / "100MEDIA").mkdir(parents=True)
        (card / "DCIM" / "100MEDIA" / "DJI_0001.MP4").write_bytes(b"v")
        code, _, err = self.run_cli("town-2026-07-31", "--from", str(card), "--copy")
        self.assertEqual(code, 2)
        self.assertIn("folders not scanned: DCIM", err)
        self.assertFalse(self.walk.exists())

    def test_copy_replaces_a_leftover_part_file_and_compares_by_size_and_mtime(self):
        raw = self.walk / "raw"
        raw.mkdir(parents=True)
        (raw / "A.MP4.part").write_bytes(b"half")
        code, _, err = self.run_cli("town-2026-07-31", "--from", str(self.source), "--copy")
        self.assertEqual(code, 0, err)
        self.assertEqual((raw / "A.MP4").read_bytes(), b"a")
        self.assertEqual(sorted(p.name for p in raw.iterdir()), ["A.MP4", "B.mp4", "C.MOV"])
        stat = (self.source / "B.mp4").stat()
        (raw / "B.mp4").write_bytes(b"XX")
        os.utime(raw / "B.mp4", ns=(stat.st_atime_ns, stat.st_mtime_ns))
        code, out, _ = self.run_cli("town-2026-07-31", "--from", str(self.source), "--copy")
        self.assertEqual(code, 0)
        self.assertIn("4 already present", out)
        os.utime(raw / "B.mp4", (stat.st_atime, stat.st_mtime + 60))
        code, _, err = self.run_cli("town-2026-07-31", "--from", str(self.source), "--copy")
        self.assertEqual(code, 2)
        self.assertIn("B.mp4", err)

    def test_an_entry_pointing_elsewhere_is_an_error_and_nothing_is_touched(self):
        (self.walk / "raw").mkdir(parents=True)
        other = self.source.parent / "other.MP4"
        other.write_bytes(b"o")
        (self.walk / "raw" / "B.mp4").symlink_to(other)
        code, _, err = self.run_cli("town-2026-07-31", "--from", str(self.source))
        self.assertEqual(code, 2)
        self.assertIn("B.mp4", err)
        self.assertEqual([p.name for p in (self.walk / "raw").iterdir()], ["B.mp4"])
        self.assertFalse((self.walk / "stills").exists())

    def test_copy_makes_regular_files_with_equal_bytes_and_reruns_cleanly(self):
        code, out, _ = self.run_cli("town-2026-07-31", "--from", str(self.source), "--copy")
        self.assertEqual(code, 0)
        self.assertIn("3 clips copied", out)
        for name in ("A.MP4", "B.mp4", "C.MOV"):
            p = self.walk / "raw" / name
            self.assertFalse(p.is_symlink())
            self.assertEqual(p.read_bytes(), (self.source / name).read_bytes())
        code, out, _ = self.run_cli("town-2026-07-31", "--from", str(self.source), "--copy")
        self.assertEqual(code, 0)
        self.assertIn("4 already present", out)

    def test_bad_walk_id_is_exit_2(self):
        for bad in ("Town-2026-07-31", "town", "town-26-07-31", str(self.footage / "my walk-2026-07-31")):
            with self.subTest(bad=bad):
                code, _, err = self.run_cli(bad, "--from", str(self.source))
                self.assertEqual(code, 2)
                self.assertIn("<place>-<YYYY-MM-DD>", err)
        self.assertEqual(list(self.footage.iterdir()), [])

    def test_a_path_is_used_as_is(self):
        target = self.source.parent / "elsewhere" / "town-2026-08-01"
        code, _, _ = self.run_cli(str(target), "--from", str(self.source))
        self.assertEqual(code, 0)
        self.assertTrue((target / "raw" / "A.MP4").is_symlink())
        self.assertEqual(list(self.footage.iterdir()), [])
