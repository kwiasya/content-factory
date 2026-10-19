"""Library indexer at the CLI seam on a synthetic Pack: categories, refs, variants, derivations, the read-only rule."""

import contextlib
import hashlib
import io
import json
import math
import shutil
import subprocess

from cf.library import load
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
        self.assertEqual(report["errors"], [])

    def probe(self, path, *extra):
        out = subprocess.run(["ffprobe", "-v", "error", *extra, "-show_streams", "-of", "json", str(path)],
                             check=True, capture_output=True, text=True).stdout
        return json.loads(out)["streams"]

    def test_green_screen_asset_is_keyed_to_prores_4444_with_alpha(self):
        self.add_and_index()
        a = self.by_path("emoji/в шоке.mp4")
        self.assertTrue(a["green_screen"])
        self.assertEqual(a["derived"]["alpha"], f"keyed/{a['id']}.mov")
        keyed = self.footage / "library/synth" / a["derived"]["alpha"]
        stream = self.probe(keyed)[0]
        self.assertEqual(stream["codec_name"], "prores")
        self.assertTrue(stream["pix_fmt"].startswith("yuva"), stream["pix_fmt"])
        stats = subprocess.run(["ffmpeg", "-v", "error", "-nostdin", "-i", str(keyed), "-frames:v", "1", "-vf",
                                "alphaextract,signalstats,metadata=print:file=-", "-f", "null", "-"],
                               check=True, capture_output=True, text=True).stdout
        values = dict(line.split("=", 1) for line in stats.splitlines() if "=" in line)
        self.assertLess(float(values["lavfi.signalstats.YMIN"]), float(values["lavfi.signalstats.YMAX"]))

    def test_loudness_is_measured_and_short_sounds_are_padded(self):
        self.add_and_index()
        tone = self.by_path("sfx/вуш 2.wav")["loudness"]
        self.assertEqual(tone["method"], "loudnorm")
        self.assertTrue(math.isfinite(tone["i"]))
        pop = self.by_path("sfx/поп.wav")["loudness"]
        self.assertEqual(pop["method"], "padded")
        self.assertTrue(math.isfinite(pop["i"]))
        self.assertIsNone(self.by_path("emoji/в шоке.mp4")["loudness"])

    def test_sticker_variants_merge_into_one_asset_with_duration_from_the_alpha_variant(self):
        self.add_and_index()
        faces = [a for a in self.index()["assets"] if a["category"] == "face"]
        self.assertEqual(len(faces), 3)
        first = self.by_path("face/1000001_sticker.webm")
        second = self.by_path("face/1000002_sticker.webm")
        self.assertEqual([v["role"] for v in first["variants"]], ["original", "alpha"])
        self.assertEqual([v["role"] for v in second["variants"]], ["original", "still"])
        self.assertAlmostEqual(first["duration_s"], 2.0, delta=0.1)
        self.assertTrue(first["alpha"])
        self.assertIsNone(first["derived"]["alpha"])
        self.assertFalse((self.footage / f"library/synth/keyed/{first['id']}.mov").exists())

    def test_one_frame_webm_stickers_are_stills(self):
        self.add_and_index()
        cache = self.footage / "library/synth"
        with_png = self.cli("show", "@face/1000002-sticker")["asset"]
        self.assertEqual((with_png["kind"], with_png["duration_s"], with_png["fps"]), ("image", None, None))
        self.assertEqual(with_png["media"]["png"], "packs/synth/face-resolve/still — улыбка — 1000002_sticker.png")
        alone = self.cli("show", "@face/1000003-sticker")["asset"]
        self.assertEqual((alone["kind"], alone["duration_s"]), ("image", None))
        self.assertEqual(alone["media"]["png"], f"library/synth/png/{alone['id']}.png")
        png = self.probe(cache / f"png/{alone['id']}.png")[0]
        self.assertTrue(png["pix_fmt"].startswith(("rgba", "ya")), png["pix_fmt"])
        moving = self.cli("show", "@face/1000001-sticker")["asset"]
        self.assertEqual(moving["kind"], "video")

    def test_alpha_path_points_at_a_file_build_can_use(self):
        self.add_and_index()
        with open_store(self.db, seed=False) as s:
            lib = load(self.footage, s)
        gif = lib.resolve("@img/anim")
        self.assertEqual(gif.alpha_path, self.footage / f"library/synth/converted/{gif.id}.mov")
        face = lib.resolve("@face/1000001-sticker")
        self.assertEqual(face.alpha_path, self.pack / "face-resolve/1000001_sticker.mov")
        emoji = lib.resolve("@emoji/в-шоке")
        self.assertEqual(emoji.alpha_path, self.footage / f"library/synth/keyed/{emoji.id}.mov")
        self.assertIsNone(lib.resolve("@face/1000003-sticker").alpha_path)

    def test_jfif_and_gif_get_converted_variants_and_previews(self):
        self.add_and_index("--no-previews")
        cache = self.footage / "library/synth"
        self.assertFalse((cache / "previews").exists() and any((cache / "previews").iterdir()))
        report = self.cli("index", "synth")
        self.assertGreater(report["derived"]["previews"], 0)
        jfif = self.by_path("img/фон 1.jfif")
        self.assertEqual(jfif["derived"]["png"], f"png/{jfif['id']}.png")
        self.assertTrue((cache / jfif["derived"]["png"]).is_file())
        gif = self.by_path("img/anim.gif")
        self.assertEqual(gif["kind"], "video")
        self.assertTrue(self.probe(cache / gif["derived"]["converted"])[0]["pix_fmt"].startswith("yuva"))
        for a in self.index()["assets"]:
            with self.subTest(asset=a["name"]):
                d = a["derived"]
                if a["kind"] in ("video", "image"):
                    self.assertTrue((cache / d["poster"]).is_file())
                else:
                    self.assertIsNone(d["poster"])
                if a["kind"] == "video":
                    self.assertTrue((cache / d["preview"]).is_file())
                    self.assertEqual(self.probe(cache / d["preview"])[0]["pix_fmt"], "yuv420p")
                else:
                    self.assertIsNone(d["preview"])

    def test_a_changed_file_gets_new_derived_files_and_the_stale_ones_are_removed(self):
        self.add_and_index()
        cache = self.footage / "library/synth"
        old = self.by_path("img/фон 1.jfif")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-nostdin", "-f", "lavfi", "-i", "color=c=navy:s=64x64:d=1",
                        "-frames:v", "1", "-f", "mjpeg", str(self.pack / "img/фон 1.jfif")], check=True)
        report = self.cli("index", "synth")
        new = self.by_path("img/фон 1.jfif")
        self.assertNotEqual(new["id"], old["id"])
        self.assertEqual(new["name"], "фон-1")
        self.assertTrue((cache / new["derived"]["png"]).is_file())
        self.assertFalse((cache / old["derived"]["png"]).exists())
        self.assertGreaterEqual(report["orphans_removed"], 2)

    def test_a_renamed_file_keeps_its_id_and_the_old_ref_as_an_alias(self):
        self.add_and_index()
        before = self.by_path("emoji/в шоке.mp4")
        keyed = self.footage / "library/synth" / before["derived"]["alpha"]
        mtime = keyed.stat().st_mtime_ns
        (self.pack / "emoji/в шоке.mp4").rename(self.pack / "emoji/шок.mp4")
        report = self.cli("index", "synth")
        after = self.by_path("emoji/шок.mp4")
        self.assertEqual(after["id"], before["id"])
        self.assertEqual(after["name"], "шок")
        self.assertEqual(report["aliases"], 1)
        shown = self.cli("show", "@emoji/в-шоке")
        self.assertEqual((shown["canonical"], shown["alias"]), ("@emoji/шок", True))
        self.assertEqual(keyed.stat().st_mtime_ns, mtime)

    def test_author_fields_survive_reindex_and_cache_deletion(self):
        self.add_and_index()
        (self.pack / "emoji/в шоке.mp4").rename(self.pack / "emoji/шок.mp4")
        self.cli("index", "synth")
        self.cli("author", "set", "@emoji/шок", "--caption", "Х", "--tag", "шок", "--rights", "free", "--name", "ох")
        self.cli("index", "synth")
        shutil.rmtree(self.footage / "library/synth")
        self.cli("index", "synth", "--no-key", "--no-previews")
        shown = self.cli("show", "@emoji/ох")
        a = shown["asset"]
        self.assertEqual((shown["canonical"], a["caption"], a["tags"], a["rights"]), ("@emoji/ох", "Х", ["шок"], "free"))
        self.assertEqual(self.cli("show", "@emoji/шок")["canonical"], "@emoji/ох")
        self.assertEqual(self.cli("show", "@emoji/в-шоке")["canonical"], "@emoji/ох")

    def test_author_rows_follow_an_asset_whose_original_variant_disappeared(self):
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        self.cli("author", "set", "@face/1000001-sticker", "--caption", "Красный")
        (self.pack / "face/1000001_sticker.webm").unlink()
        self.cli("index", "synth", "--no-key", "--no-previews", "--no-loudness")
        a = self.cli("show", "@face/1000001-sticker")["asset"]
        self.assertEqual([v["role"] for v in a["variants"]], ["alpha"])
        self.assertEqual(a["caption"], "Красный")

    def test_author_rows_stay_on_the_original_when_a_byte_identical_copy_exists(self):
        shutil.copy2(self.pack / "sfx/вуш 2.mp3", self.pack / "sfx/яяя копия.mp3")
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        self.cli("author", "set", "@sfx/вуш-2", "--caption", "Оригинал", "--name", "первый")
        self.cli("author", "set", "@sfx/первый", "--name", "оригинал")
        for _ in range(2):
            self.cli("index", "synth", "--no-key", "--no-previews", "--no-loudness")
        original = self.cli("show", "@sfx/оригинал")["asset"]
        self.assertEqual((original["file"]["path"], original["caption"]), ("sfx/вуш 2.mp3", "Оригинал"))
        self.assertEqual(original["aliases"], ["@sfx/первый"])
        copy = self.cli("show", "@sfx/яяя-копия")["asset"]
        self.assertEqual((copy["caption"], copy["author_name"], copy["aliases"]), (None, None, []))
        self.assertNotEqual(copy["id"], original["id"])

    def test_index_refuses_a_footage_root_inside_the_pack(self):
        self.write_config(CONFIG, root=self.pack)
        self.cli("pack", "add", "--config", str(self.config_path))
        inner = self.pack / "unmapped" / "footage"
        from cf.library import cli
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            code = cli.main(["index", "synth", "--db", str(self.db), "--footage-root", str(inner), "--quiet"])
        self.assertEqual(code, 1)
        self.assertIn("inside the Pack", err.getvalue())
        self.assertFalse(inner.exists())

    def test_author_names_and_aliases_hold_after_a_cache_wipe(self):
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        self.cli("author", "set", "@emoji/в-шоке", "--name", "шок")
        shutil.copy(self.pack / "unmapped/clip.mp4", self.pack / "emoji/шок.mp4")
        self.cli("index", "synth", "--no-key", "--no-previews", "--no-loudness")
        self.assertEqual(self.by_path("emoji/шок.mp4")["name"], "шок-2")
        shutil.rmtree(self.footage / "library/synth")
        self.cli("index", "synth", "--no-key", "--no-previews", "--no-loudness")
        self.assertEqual(self.by_path("emoji/шок.mp4")["name"], "шок-2")
        self.assertEqual(self.cli("show", "@emoji/шок")["asset"]["file"]["path"], "emoji/в шоке.mp4")

    def test_sheets_refuse_a_footage_root_inside_the_pack(self):
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        from cf.library import cli
        inner = self.pack / "unmapped" / "footage"
        err = io.StringIO()
        with contextlib.redirect_stderr(err), contextlib.redirect_stdout(io.StringIO()):
            code = cli.main(["tags", "todo", "synth", "--sheets", "--db", str(self.db), "--footage-root", str(inner)])
        self.assertEqual(code, 1)
        self.assertIn("inside the Pack", err.getvalue())
        self.assertFalse(inner.exists())

    def test_alias_rows_of_a_vanished_asset_do_not_take_file_names(self):
        with open_store(self.db, seed=False) as s:
            s.conn.execute("INSERT INTO asset_alias VALUES ('@sfx/вуш-2', 'ffffffffffffffff', 'rename', 'x')")
            s.conn.commit()
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        self.assertEqual(self.by_path("sfx/вуш 2.mp3")["name"], "вуш-2")

    def test_report_counts_author_rows_left_without_an_asset(self):
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        self.cli("author", "set", "@sfx/plus-1", "--caption", "Плюс")
        (self.pack / "sfx/+1.mp3").unlink()
        report = self.cli("index", "synth", "--no-key", "--no-previews", "--no-loudness")
        self.assertEqual(report["author_orphans"], 1)
        self.assertEqual(len(self.cli("author", "orphans", "synth")["orphans"]), 1)

    def test_only_keeps_ids_unique_with_a_byte_identical_file_outside_the_subtree(self):
        shutil.copy2(self.pack / "sfx/вуш 2.mp3", self.pack / "unmapped/копия.mp3")
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        before = {a["variants"][0]["path"]: a["id"] for a in self.index()["assets"]}
        self.cli("index", "synth", "--only", "unmapped", "--no-key", "--no-previews", "--no-loudness")
        after = {a["variants"][0]["path"]: a["id"] for a in self.index()["assets"]}
        self.assertEqual(after, before)
        self.assertEqual(len(set(after.values())), len(after))

    def test_leftover_temp_files_in_the_cache_are_removed(self):
        self.add_and_index("--no-key", "--no-loudness")
        left = self.footage / "library/synth/previews/.abc.part.mp4"
        left.write_bytes(b"x")
        self.cli("index", "synth", "--no-key", "--no-loudness")
        self.assertFalse(left.exists())

    def write_tags(self, entries: dict) -> str:
        path = self.footage.parent / "tags.json"
        path.write_text(json.dumps(entries, ensure_ascii=False))
        return str(path)

    def test_import_tags_maps_12_hex_ids_to_files_and_is_idempotent(self):
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        self.cli("author", "set", "@sfx/plus-1", "--caption", "Своя")
        mp3 = hashlib.sha256("вуш 2.mp3".encode()).hexdigest()[:12]
        plus = hashlib.sha256("+1.mp3".encode()).hexdigest()[:12]
        tags = self.write_tags({
            mp3: {"label": "Вжух", "tags": ["переход", "Вжух", "быстро, резко"]},
            plus: {"label": "Плюс один", "tags": ["счёт"], "category": "02 — Игровое"},
            "000000000000": {"label": "нет такого", "tags": []},
        })
        first = self.cli("import-tags", "synth", tags, "--base", "sfx")
        self.assertEqual((first["matched"], first["changed"], first["unmatched"]), (2, 2, ["000000000000"]))
        whoosh = self.cli("show", "@sfx/вуш-2")["asset"]
        self.assertEqual((whoosh["caption"], whoosh["tags"]), ("Вжух", ["переход"]))
        mine = self.cli("show", "@sfx/plus-1")["asset"]
        self.assertEqual((mine["caption"], mine["tags"]), ("Своя", ["счёт", "Игровое"]))
        again = self.cli("import-tags", "synth", tags, "--base", "sfx")
        self.assertEqual(again["changed"], 0)

    def test_import_with_names_makes_the_label_the_ref_and_keeps_the_numeric_ref(self):
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")
        one = hashlib.sha256("face/1000001_sticker.webm".encode()).hexdigest()[:12]
        two = hashlib.sha256("face/1000002_sticker.webm".encode()).hexdigest()[:12]
        self.cli("author", "set", "@face/1000002-sticker", "--name", "моё")
        tags = self.write_tags({one: {"label": "Крик в камеру", "tags": ["моё лицо"]},
                                two: {"label": "Улыбка", "tags": []}})
        report = self.cli("import-tags", "synth", tags, "--base", "", "--names")
        self.assertEqual(report["named"], 1)
        shown = self.cli("show", "@face/1000001-sticker")
        self.assertEqual((shown["canonical"], shown["alias"]), ("@face/крик-в-камеру", True))
        self.assertEqual(self.cli("show", "@face/1000002-sticker")["canonical"], "@face/моё")
        self.assertEqual(self.cli("import-tags", "synth", tags, "--base", "", "--names")["changed"], 0)

    def test_tags_todo_sheets_and_apply(self):
        self.add_and_index("--no-key", "--no-loudness")
        todo = self.cli("tags", "todo", "synth", "--sheets")
        total = len(self.index()["assets"])
        self.assertEqual(todo["todo"], total)
        sheets = self.footage / "library/synth/sheets"
        self.assertTrue((sheets / "01.jpg").is_file())
        listing = json.loads((sheets / "01.json").read_text())
        self.assertEqual(len(listing), min(total, 24))
        whoosh = self.by_path("sfx/вуш 2.mp3")["id"]
        emoji = self.by_path("emoji/в шоке.mp4")["id"]
        self.cli("author", "set", "@sfx/вуш-2", "--caption", "моё")
        proposals = self.footage.parent / "proposals.json"
        proposals.write_text(json.dumps({whoosh: {"caption": "Свист", "tags": ["переход"], "basis": "name"},
                                         emoji: {"caption": "Шок", "tags": ["шок", "реакция"]},
                                         "ffffffffffffffff": {"caption": "x"}}, ensure_ascii=False))
        applied = self.cli("tags", "apply", "synth", str(proposals))
        self.assertEqual((applied["applied"], applied["unknown"]), (2, ["ffffffffffffffff"]))
        self.cli("index", "synth", "--no-key", "--no-loudness")
        a = self.cli("show", "@sfx/вуш-2")["asset"]
        self.assertEqual((a["agent_caption"], a["agent_tags"], a["caption"]), ("Свист", ["переход"], "моё"))
        self.assertEqual(self.by_path("sfx/вуш 2.mp3")["agent"]["basis"], "name")
        self.assertEqual(self.cli("tags", "todo", "synth")["todo"], total - 2)

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


@needs_ffmpeg
class WholeRootPackTest(SyntheticPack):
    """``"."`` in ``include`` and ``folders`` is the Pack root itself: an inbox folder of loose files."""

    def test_dot_includes_root_level_files_and_deeper_mappings_still_win(self):
        shutil.copy(self.pack / "unmapped/clip.mp4", self.pack / "loose meme.mp4")
        self.write_config({**CONFIG, "include": ["."], "templates": False,
                           "folders": {".": {"category": "meme"}, "sfx": {"category": "sfx"}}})
        report = self.add_and_index()
        paths = {v["path"]: a for a in self.index()["assets"] for v in a["variants"]}
        self.assertEqual((paths["loose meme.mp4"]["category"], paths["loose meme.mp4"]["category_source"]),
                         ("meme", "mapping"))
        self.assertEqual(paths["unmapped/clip.mp4"]["category"], "meme")
        self.assertEqual(paths["sfx/вуш 2.wav"]["category"], "sfx")
        self.assertEqual(report["fallback"], {})

    def test_dot_is_refused_in_exclude(self):
        self.write_config({**CONFIG, "exclude": ["."]})
        code, _, err = self.run_cli("pack", "add", "--config", str(self.config_path))
        self.assertEqual(code, 1)
        self.assertIn("exclude", err)
