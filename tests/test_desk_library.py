"""Desk Library API and Pack media through the FastAPI TestClient: a byte-file Pack with a hand-written index."""

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from fastapi.testclient import TestClient

from cf.desk.app import create_app
from cf.library import register_pack
from cf.library.index import write_index
from cf.research.store import open_store

MP3 = bytes(range(256)) * 8
SFX, FACE, FONT, TPL = "a" * 16, "b" * 16, "c" * 16, "d" * 16


def variant(path, role="original", **kw):
    return {"role": role, "path": path, "size": len(MP3), "mtime": 1759491000.0, "mtime_ns": 1, "content_id": "0",
            "kind": kw.pop("kind", "audio"), "alpha": kw.pop("alpha", False), **kw}


def asset(aid, category, name, kind, variants, **kw):
    return {"id": aid, "category": category, "category_source": "mapping", "name": name, "slug": name, "kind": kind,
            "folder": variants[0]["path"].rsplit("/", 1)[0], "group": None, "variants": variants,
            "duration_s": kw.get("duration_s"), "fps": None, "width": None, "height": None,
            "has_audio": kind == "audio", "alpha": kw.get("alpha", False), "green_screen": False,
            "loudness": kw.get("loudness"),
            "derived": {"alpha": None, "converted": None, "png": None, "poster": kw.get("poster"), "preview": None},
            "rights_default": kw.get("rights", "unknown"), "agent": kw.get("agent")}


INDEX_ASSETS = [
    asset(SFX, "sfx", "вуш-2", "audio", [variant("sfx/a.mp3")], duration_s=1.0,
          loudness={"i": -20.5, "tp": -3.0, "lra": 1.0, "method": "loudnorm"},
          agent={"caption": "Свист ветра", "tags": ["переход", "ветер"], "at": "x", "basis": "name"}),
    asset(FACE, "face", "1-sticker", "video",
          [variant("face/1_sticker.webm", kind="video", alpha=True),
           variant("face-resolve/1_sticker.mov", role="alpha", kind="video", alpha=True)],
          duration_s=2.0, alpha=True, rights="own", poster=f"previews/{'b' * 16}.jpg"),
    asset(FONT, "font", "komika", "font", [variant("fonts/Komika.ttf", kind="font")]),
    asset(TPL, "template", "t", "template", [variant("T.drfx", kind="template")]),
]


def write(path: Path, data: bytes | str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data if isinstance(data, bytes) else data.encode())
    return path


class LibraryTestCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        base = Path(self.tmp.name)
        self.repo = base / "repo"
        self.repo.mkdir()
        self.pack = base / "pack"
        for rel in ("sfx/a.mp3", "face/1_sticker.webm", "face-resolve/1_sticker.mov", "fonts/Komika.ttf", "T.drfx",
                    "notes.txt", "img/x.jfif"):
            write(self.pack / rel, MP3)
        write(base / "outside.mp3", MP3)
        os.symlink(base / "outside.mp3", self.pack / "sfx/link.mp3")
        self.footage = base / "footage"
        self.db = self.footage / "factory.db"
        with open_store(self.db, seed=False, create=True) as s:
            register_pack(s, {"schema": "cf-pack/1", "id": "p", "root": str(self.pack),
                              "folders": {"sfx": {"category": "sfx"}}})
        self.write_index()
        write(self.footage / f"library/p/previews/{FACE}.jpg", b"\xff\xd8jpeg")
        (self.footage / "library/p/keyed").mkdir(parents=True)
        self.client = TestClient(create_app(self.repo, local_root=self.footage, db_path=self.db,
                                            web_dist=base / "dist"))

    def write_index(self, assets=None):
        write_index(self.footage, "p", {"schema": "cf-library-index/1", "pack": "p", "root": str(self.pack),
                                        "indexed_at": "2026-10-13T20:00:00Z", "assets": assets or INDEX_ASSETS,
                                        "report": {"fallback": {"misc": 2}}})

    def ok(self, response) -> dict:
        self.assertLess(response.status_code, 300, response.text)
        return response.json()

    def err(self, response, status, code):
        self.assertEqual((response.status_code, response.json()["code"]), (status, code), response.text)
        return response.json()

    def put(self, aid, **body):
        return self.client.put(f"/api/library/assets/{aid}/author", json=body)


class LibraryListTest(LibraryTestCase):
    def test_library_lists_packs_with_counts_and_categories(self):
        data = self.ok(self.client.get("/api/library"))
        (pack,) = data["packs"]
        self.assertEqual((pack["id"], pack["assets"], pack["index_missing"], pack["fallback"]), ("p", 4, False, 1))
        self.assertEqual(pack["by_category"], {"sfx": 1, "face": 1, "font": 1, "template": 1})
        self.assertEqual(pack["indexed_at"], "2026-10-13T20:00:00Z")
        self.assertEqual(data["categories"][:3], ["sfx", "meme", "img"])
        self.assertEqual(data["rights"], ["own", "free", "unknown"])
        shutil.rmtree(self.footage / "library/p")
        (pack,) = self.ok(self.client.get("/api/library"))["packs"]
        self.assertEqual((pack["index_missing"], pack["assets"]), (True, 0))
        self.db.unlink()
        self.assertEqual(self.ok(self.client.get("/api/library"))["packs"], [])

    def test_assets_query_filters_and_facets(self):
        self.ok(self.put(SFX, tags=["удар", "переход"], caption="Резкий свист"))
        self.ok(self.put(FACE, tags=["удар"], name="шок"))
        self.ok(self.put(FACE, name="ох"))

        def refs(**params):
            data = self.ok(self.client.get("/api/library/assets", params=params))
            return [a["ref"] for a in data["assets"]], data

        self.assertEqual(refs(category="face")[0], ["@face/ох"])
        self.assertEqual(refs(tags="удар,переход")[0], ["@sfx/вуш-2"])
        self.assertEqual(refs(tags="ветер")[0], ["@sfx/вуш-2"])
        self.assertEqual(refs(q="резкий")[0], ["@sfx/вуш-2"])
        self.assertEqual(refs(q="@face/шок")[0], ["@face/ох"])
        self.assertEqual(refs(q="komika.ttf")[0], ["@font/komika"])
        self.assertEqual(refs(rights="own")[0], ["@face/ох"])
        page, data = refs(limit=2, offset=1)
        self.assertEqual((len(page), data["total"]), (2, 4))
        facets = refs()[1]["tags"]
        self.assertEqual(facets[0], {"tag": "удар", "n": 2, "author": True})
        self.assertIn({"tag": "ветер", "n": 1, "author": False}, facets)
        for param, value in (("category", "noise"), ("rights", "maybe"), ("pack", "nope")):
            with self.subTest(param=param):
                body = self.err(self.client.get("/api/library/assets", params={param: value}), 422,
                                "library_query_invalid")
                self.assertEqual(body["params"], {"param": param, "value": value})

    def test_get_asset_card_shape(self):
        a = self.ok(self.client.get(f"/api/library/assets/{FACE}"))["asset"]
        keys = {"id", "pack", "category", "category_source", "ref", "name", "author_name", "aliases", "kind", "file",
                "media", "duration_s", "fps", "width", "height", "has_audio", "alpha", "green_screen", "loudness",
                "rights", "rights_default", "rights_override", "caption", "tags", "agent_caption", "agent_tags",
                "variants", "updated_at"}
        self.assertLessEqual(keys, set(a))
        self.assertEqual(a["media"]["original"], "packs/p/face/1_sticker.webm")
        self.assertEqual(a["media"]["alpha"], "packs/p/face-resolve/1_sticker.mov")
        self.assertEqual(a["media"]["poster"], f"library/p/previews/{FACE}.jpg")
        self.assertEqual(a["file"]["name"], "1_sticker.webm")
        self.assertEqual([v["role"] for v in a["variants"]], ["original", "alpha"])
        tpl = self.ok(self.client.get(f"/api/library/assets/{TPL}"))["asset"]
        self.assertEqual(set(tpl["media"].values()), {None})
        self.assertEqual(tpl["file"]["path"], "T.drfx")
        self.err(self.client.get("/api/library/assets/nope"), 404, "asset_not_found")


class AuthorTest(LibraryTestCase):
    def test_put_author_sets_and_clears_fields(self):
        a = self.ok(self.put(SFX, caption=" Свист ", tags=[" Удар ", "удар", "переход"]))["asset"]
        self.assertEqual((a["caption"], a["tags"]), ("Свист", ["Удар", "переход"]))
        a = self.ok(self.put(SFX, rights="free"))["asset"]
        self.assertEqual((a["rights"], a["rights_override"], a["caption"]), ("free", "free", "Свист"))
        a = self.ok(self.put(SFX, rights=None))["asset"]
        self.assertEqual((a["rights"], a["rights_override"]), ("unknown", None))
        a = self.ok(self.put(SFX, name="ветер"))["asset"]
        self.assertEqual((a["ref"], a["author_name"], a["aliases"]), ("@sfx/ветер", "ветер", []))
        a = self.ok(self.put(SFX, name="вжух"))["asset"]
        self.assertEqual((a["ref"], a["aliases"]), ("@sfx/вжух", ["@sfx/ветер"]))
        with open_store(self.db, seed=False, create=True) as s:
            s.conn.execute("INSERT INTO asset_alias VALUES ('@sfx/вуш-2', ?, 'import', 'x')", (SFX,))
            s.conn.commit()
        a = self.ok(self.client.get(f"/api/library/assets/{SFX}"))["asset"]
        self.assertEqual(a["aliases"], ["@sfx/ветер"])
        a = self.ok(self.put(SFX, caption=None, tags=None))["asset"]
        self.assertEqual((a["caption"], a["tags"]), (None, []))
        body = self.err(self.put(SFX, rights="mine"), 422, "rights_invalid")
        self.assertEqual(body["params"], {"rights": "mine", "values": "own, free, unknown"})
        self.err(self.put(SFX, tags="удар"), 422, "tags_invalid")
        self.err(self.put(SFX, tags=["a,b"]), 422, "tags_invalid")
        body = self.err(self.put(SFX, name="Шок!"), 422, "ref_name_invalid")
        self.assertEqual(body["params"], {"name": "Шок!", "slug": "шок"})
        self.err(self.put("nope", caption="x"), 404, "asset_not_found")

    def test_author_tag_hits_rank_before_agent_only_hits(self):
        other = "e" * 16
        self.write_index(INDEX_ASSETS + [asset(other, "sfx", "аа", "audio", [variant("sfx/a.mp3")],
                                               agent={"caption": None, "tags": ["удар"], "at": "x"})])
        self.ok(self.put(SFX, tags=["удар"]))
        data = self.ok(self.client.get("/api/library/assets", params={"tags": "удар"}))
        self.assertEqual([a["ref"] for a in data["assets"]], ["@sfx/вуш-2", "@sfx/аа"])
        self.ok(self.put(FACE, tags=["удар", "крик"]))
        data = self.ok(self.client.get("/api/library/assets", params={"tags": "удар"}))
        self.assertEqual([a["ref"] for a in data["assets"]], ["@face/1-sticker", "@sfx/вуш-2", "@sfx/аа"])

    def test_a_hidden_agent_tag_stops_matching_and_leaves_cards_and_facets(self):
        a = self.ok(self.put(SFX, hidden_agent_tags=[" Ветер "]))["asset"]
        self.assertEqual((a["agent_tags"], a["hidden_agent_tags"]), (["переход"], ["Ветер"]))
        self.assertEqual(self.ok(self.client.get("/api/library/assets", params={"tags": "ветер"}))["assets"], [])
        self.assertEqual(self.ok(self.client.get("/api/library/assets", params={"q": "ветер"}))["assets"], [])
        facets = self.ok(self.client.get("/api/library/assets"))["tags"]
        self.assertNotIn("ветер", [f["tag"] for f in facets])
        self.assertEqual(self.ok(self.client.get("/api/library/tags", params={"q": "вет"}))["tags"], [])
        self.err(self.put(SFX, hidden_agent_tags="ветер"), 422, "tags_invalid")
        a = self.ok(self.put(SFX, hidden_agent_tags=[]))["asset"]
        self.assertEqual((a["agent_tags"], a["hidden_agent_tags"]), (["переход", "ветер"], []))

    def test_name_taken_names_the_holder(self):
        self.ok(self.put(SFX, name="ветер"))
        self.ok(self.put(SFX, name="вжух"))
        self.write_index(INDEX_ASSETS + [asset("e" * 16, "sfx", "другой", "audio", [variant("sfx/a.mp3")])])
        for name in ("вжух", "ветер", "вуш-2"):
            with self.subTest(name=name):
                body = self.err(self.put("e" * 16, name=name), 409, "ref_name_taken")
                self.assertEqual(body["params"], {"ref": f"@sfx/{name}", "holder": "@sfx/вжух", "holder_id": SFX,
                                                  "holder_file": "sfx/a.mp3"})
        self.ok(self.put(FACE, name="вжух"))

    def test_author_fields_survive_an_index_rewrite_and_cache_deletion(self):
        self.ok(self.put(FACE, caption="Крик", tags=["шок"], rights="free", name="крик"))
        shutil.rmtree(self.footage / "library/p")
        self.write_index()
        a = self.ok(self.client.get(f"/api/library/assets/{FACE}"))["asset"]
        self.assertEqual((a["caption"], a["tags"], a["rights"], a["ref"]), ("Крик", ["шок"], "free", "@face/крик"))


class RefsTest(LibraryTestCase):
    def test_resolve_suggest_and_check(self):
        self.ok(self.put(FACE, name="шок"))
        self.ok(self.put(FACE, name="ох"))

        def resolve(ref):
            return self.client.get("/api/library/refs/resolve", params={"ref": ref})
        canonical = self.ok(resolve("@face/ох"))
        self.assertEqual((canonical["canonical"], canonical["alias"], canonical["asset"]["id"]), ("@face/ох", False, FACE))
        self.assertEqual(self.ok(resolve("@face/1-sticker"))["alias"], True)
        self.assertEqual(self.ok(resolve("@face/шок"))["canonical"], "@face/ох")
        missing = self.err(resolve("@sfx/вуш-3"), 404, "ref_not_found")
        self.assertEqual(missing["params"], {"ref": "@sfx/вуш-3"})
        self.assertIn("@sfx/вуш-2", [c["ref"] for c in missing["suggestions"]])
        self.assertLessEqual(len(missing["suggestions"]), 5)
        for bad in ("@nope/x", "face/x"):
            with self.subTest(bad=bad):
                self.err(resolve(bad), 422, "ref_invalid")
        suggest = self.ok(self.client.get("/api/library/refs/suggest", params={"q": "@fa"}))["suggestions"]
        self.assertEqual([c["ref"] for c in suggest], ["@face/ох"])
        by_caption = self.ok(self.client.get("/api/library/refs/suggest", params={"q": "ветр"}))["suggestions"]
        self.assertEqual([c["ref"] for c in by_caption], ["@sfx/вуш-2"])
        check = self.ok(self.client.post("/api/library/refs/check",
                                         json={"refs": ["@face/шок", "@sfx/вуш-3", "@nope/x"]}))["refs"]
        self.assertEqual(check["@face/шок"], {"ok": True, "id": FACE, "canonical": "@face/ох"})
        self.assertFalse(check["@sfx/вуш-3"]["ok"])
        self.assertIn("@sfx/вуш-2", check["@sfx/вуш-3"]["suggestions"])
        self.assertFalse(check["@nope/x"]["ok"])
        self.err(self.client.post("/api/library/refs/check", json={"refs": ["@sfx/x"] * 201}), 422, "request_invalid")

    def test_tags_endpoint_lists_author_tags_first(self):
        self.ok(self.put(FACE, tags=["моё лицо", "переход"]))
        tags = self.ok(self.client.get("/api/library/tags"))["tags"]
        self.assertEqual(tags[0], {"tag": "переход", "n": 2, "author": True})
        self.assertEqual([t["tag"] for t in tags], ["переход", "моё лицо", "ветер"])
        self.assertEqual([t["tag"] for t in self.ok(self.client.get("/api/library/tags",
                                                                     params={"q": "мо"}))["tags"]], ["моё лицо"])


class PackMediaTest(LibraryTestCase):
    def media(self, path, **headers):
        return self.client.get("/api/media", params={"path": path}, headers=headers)

    def test_media_serves_pack_and_cache_files_with_range_and_404s_everything_else(self):
        self.write_index(INDEX_ASSETS + [asset("f" * 16, "img", "x", "image", [variant("img/x.jfif", kind="image")])])
        write(self.pack / "excluded/y.mp3", MP3)
        r = self.media("packs/p/sfx/a.mp3")
        self.assertEqual((r.status_code, r.content), (200, MP3))
        r = self.media("packs/p/sfx/a.mp3", range="bytes=10-19")
        self.assertEqual((r.status_code, r.content), (206, MP3[10:20]))
        r = self.media(f"library/p/previews/{FACE}.jpg")
        self.assertEqual((r.status_code, r.headers["content-type"]), (200, "image/jpeg"))
        self.assertEqual(self.media("packs/p/img/x.jfif").headers["content-type"], "image/jpeg")
        self.assertEqual(self.media("packs/p/fonts/Komika.ttf").headers["content-type"], "font/ttf")
        for path in ("packs/p/notes.txt", "packs/p/T.drfx", "packs/p/../outside.mp3", "packs/unknown/sfx/a.mp3",
                     "packs/p/sfx/link.mp3", "library/p/index.json", "library/p/keyed", "library/p/keyed/",
                     "packs/p", "packs/p/sfx/missing.mp3", "packs/p/excluded/y.mp3"):
            with self.subTest(path):
                self.assertEqual(self.media(path).status_code, 404)

    def test_with_the_db_missing_pack_paths_are_404_and_cache_paths_still_work(self):
        self.db.unlink()
        self.assertEqual(self.media("packs/p/sfx/a.mp3").status_code, 404)
        self.assertEqual(self.media(f"library/p/previews/{FACE}.jpg").status_code, 200)


class RevealTest(LibraryTestCase):
    def test_reveal_runs_open_minus_r_for_an_asset(self):
        with mock.patch("cf.desk.library_api.subprocess.run") as run, \
                mock.patch("cf.desk.library_api.sys.platform", "darwin"):
            data = self.ok(self.client.post(f"/api/library/assets/{TPL}/reveal"))
            run.assert_called_once()
            self.assertEqual(run.call_args.args[0], ["/usr/bin/open", "-R", str(self.pack / "T.drfx")])
            self.assertEqual(data["path"], str(self.pack / "T.drfx"))
            self.err(self.client.post("/api/library/assets/nope/reveal"), 404, "asset_not_found")
        with mock.patch("cf.desk.library_api.sys.platform", "linux"):
            self.err(self.client.post(f"/api/library/assets/{TPL}/reveal"), 409, "reveal_unavailable")


if __name__ == "__main__":
    unittest.main()
