"""Library indexer at the CLI seam on a synthetic Pack: categories, refs, variants, derivations, the read-only rule."""

import shutil
import subprocess

from cf.research.store import open_store
from library_pack import CONFIG, SyntheticPack, needs_ffmpeg, snapshot


@needs_ffmpeg
class IndexTest(SyntheticPack):
    def test_index_lists_assets_by_category_and_ignores_junk_pdf_psd_and_symlinks(self):
        report = self.add_and_index()
        assets = self.index()["assets"]
        paths = {v["path"]: a for a in assets for v in a["variants"]}
        self.assertEqual(paths["sfx/вуш 2.wav"]["category"], "sfx")
        self.assertEqual(paths["emoji/в шоке.mp4"]["category"], "emoji")
        self.assertEqual(paths["face/1000001_sticker.webm"]["category"], "face")
        self.assertEqual(paths["img/фон 1.jfif"]["category"], "img")
        self.assertEqual(paths["fonts/Komika Title.otf"]["category"], "font")
        self.assertFalse([p for p in paths if p.startswith("junk/")])
        clip = paths["unmapped/clip.mp4"]
        self.assertEqual((clip["category"], clip["category_source"]), ("footage", "fallback"))
        self.assertEqual(paths["sfx/вуш 2.wav"]["category_source"], "mapping")
        self.assertEqual(report["fallback"], {"unmapped": 1})
        self.assertEqual(report["junk"], 6)
        self.assertEqual(report["symlinks"], 1)

    def test_refs_are_slugged_cyrillic_kept_and_clashes_numbered_deterministically(self):
        self.add_and_index()

        def ref(rel):
            a = self.by_path(rel)
            return f"@{a['category']}/{a['name']}"
        self.assertEqual(ref("sfx/вуш 2.mp3"), "@sfx/вуш-2")
        self.assertEqual(ref("sfx/вуш 2.wav"), "@sfx/вуш-2-2")
        self.assertEqual(ref("sfx/+1.mp3"), "@sfx/plus-1")
        self.assertEqual(ref("emoji/в шоке.mp4"), "@emoji/в-шоке")
        self.assertEqual(ref("face/1000001_sticker.webm"), "@face/1000001-sticker")
        self.assertEqual(ref("img/фон 1.jfif"), "@img/фон-1")
        self.assertEqual(ref("fonts/Komika Title.otf"), "@font/komika-title")
        self.assertEqual(ref("templates/T.drfx"), "@template/t")
        self.assertEqual(ref("templates/P.dra"), "@template/p")

    def test_numbering_is_sticky_when_a_lexically_earlier_file_arrives(self):
        self.add_and_index()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-f", "lavfi", "-i", "sine=f=220:d=1",
                        str(self.pack / "sfx/вуш 2.flac")], check=True)
        self.cli("index", "synth")
        self.assertEqual(self.by_path("sfx/вуш 2.mp3")["name"], "вуш-2")
        self.assertEqual(self.by_path("sfx/вуш 2.wav")["name"], "вуш-2-2")
        self.assertEqual(self.by_path("sfx/вуш 2.flac")["name"], "вуш-2-3")

    def test_second_run_is_incremental_and_derives_nothing(self):
        self.add_and_index()
        cache = self.footage / "library/synth"

        def mtimes():
            return {p: p.stat().st_mtime_ns for p in cache.rglob("*") if p.is_file() and p.name != "index.json"}
        before = mtimes()
        again = self.cli("index", "synth")
        self.assertEqual(again["probed"], 0)
        self.assertEqual(set(again["derived"].values()), {0})
        self.assertEqual(again["new"], 0)
        self.assertEqual(mtimes(), before)
        (self.pack / "unmapped/clip copy.mp4").write_bytes((self.pack / "unmapped/clip.mp4").read_bytes() + b"\0")
        third = self.cli("index", "synth")
        self.assertEqual((third["probed"], third["new"]), (1, 1))

    def test_the_pack_is_byte_for_byte_unchanged(self):
        before = snapshot(self.pack)
        self.add_and_index()
        self.cli("index", "synth")
        self.assertEqual(snapshot(self.pack), before)

    def test_index_refuses_a_root_inside_the_library_cache(self):
        inside = self.footage / "library/elsewhere"
        shutil.copytree(self.pack, inside, symlinks=True)
        self.write_config({**CONFIG, "id": "inside"}, root=inside)
        self.cli("pack", "add", "--config", str(self.config_path))
        code, _, err = self.run_cli("index", "inside")
        self.assertEqual(code, 1)
        self.assertIn("inside the Library cache", err)

    def test_templates_are_listed_as_entries_and_a_dra_bundle_is_one_entry(self):
        self.add_and_index()
        assets = self.index()["assets"]
        templates = {v["path"] for a in assets if a["kind"] == "template" for v in a["variants"]}
        self.assertEqual(templates, {"templates/T.drfx", "templates/P.dra"})
        self.assertFalse([v for a in assets for v in a["variants"] if v["path"].endswith("project.drp")])
        shown = self.cli("show", "@template/p")["asset"]
        self.assertEqual(set(shown["media"].values()), {None})

    def test_pack_add_rejects_bad_configs(self):
        cases = [
            ({**CONFIG, "folders": {"sfx": {"category": "noise"}}}, None, "unknown category"),
            ({**CONFIG, "folders": {"../sfx": {"category": "sfx"}}}, None, ".."),
            (CONFIG, self.pack / "missing", "is not a folder"),
        ]
        for config, root, message in cases:
            with self.subTest(message=message):
                self.write_config(config, root=root)
                code, _, err = self.run_cli("pack", "add", "--config", str(self.config_path))
                self.assertEqual(code, 1)
                self.assertIn(message, err)
        with open_store(self.db, seed=False) as s:
            self.assertEqual(s.query("SELECT id FROM pack"), [])
