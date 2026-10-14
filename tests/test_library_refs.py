"""Refs, suggestions, queries and the Author's fields at the Library CLI seam (synthetic Pack)."""

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from cf import library
from cf.library import cli, refs
from cf.library.index import read_index, write_index
from cf.research.store import open_store
from library_fixture import IDS, PACK, make_library
from library_pack import SyntheticPack, needs_ffmpeg


class GrammarTest(unittest.TestCase):
    def test_ref_grammar_finds_refs_after_whitespace_and_openers_only(self):
        text = "Реакция @face/шок, (@sfx/вуш-2) «@img/фон-1» mail@face/x @nope/x @emoji/в-шоке"
        self.assertEqual(refs.find(text), ["@face/шок", "@sfx/вуш-2", "@img/фон-1", "@emoji/в-шоке"])


@needs_ffmpeg
class RefsTest(SyntheticPack):
    def setUp(self):
        super().setUp()
        self.add_and_index("--no-key", "--no-previews", "--no-loudness")

    def refs_of(self, cards):
        return [c["ref"] for c in cards]

    def test_suggest_ranks_prefix_then_name_then_caption(self):
        faces = self.refs_of(self.cli("suggest", "fac")["suggestions"])
        self.assertEqual(faces, ["@face/1000001-sticker", "@face/1000002-sticker", "@face/1000003-sticker"])
        self.assertEqual(self.refs_of(self.cli("suggest", "sfx/ву")["suggestions"]), ["@sfx/вуш-2", "@sfx/вуш-2-2"])
        self.cli("author", "set", "@face/1000002-sticker", "--caption", "Шок и смех")
        found = self.refs_of(self.cli("suggest", "шок")["suggestions"])
        self.assertEqual(found[:2], ["@emoji/в-шоке", "@face/1000002-sticker"])

    def test_query_filters_by_category_tags_text_and_rights(self):
        self.cli("author", "set", "@sfx/вуш-2", "--tag", "переход", "--tag", "удар")
        self.cli("author", "set", "@sfx/plus-1", "--tag", "переход")
        both = self.cli("query", "--tag", "переход", "--tag", "удар")["assets"]
        self.assertEqual(self.refs_of(both), ["@sfx/вуш-2"])
        own = self.cli("query", "--rights", "own")["assets"]
        self.assertEqual({c["category"] for c in own}, {"face"})
        self.cli("author", "set", "@emoji/в-шоке", "--name", "ох")
        self.cli("author", "set", "@emoji/ох", "--name", "ах")
        by_alias = self.cli("query", "--q", "@emoji/ох")["assets"]
        self.assertEqual(self.refs_of(by_alias), ["@emoji/ах"])
        self.assertEqual(self.refs_of(self.cli("query", "--category", "font")["assets"]), ["@font/komika-title"])

    def test_author_name_must_be_free_and_slug_clean(self):
        code, _, err = self.run_cli("author", "set", "@sfx/plus-1", "--name", "Шок!")
        self.assertEqual(code, 1)
        self.assertIn("'шок'", err)
        code, _, err = self.run_cli("author", "set", "@sfx/plus-1", "--name", "вуш-2")
        self.assertEqual(code, 1)
        self.assertIn("@sfx/вуш-2", err)
        named = self.cli("author", "set", "@sfx/plus-1", "--name", "плюс")
        self.assertEqual(named["canonical"], "@sfx/плюс")
        shown = self.cli("show", "@sfx/plus-1")
        self.assertEqual((shown["canonical"], shown["alias"]), ("@sfx/плюс", True))

    def test_check_returns_suggestions_for_broken_refs(self):
        with open_store(self.db, seed=False) as s:
            lib = library.load(self.footage, s)
        out = lib.check(["@sfx/вуш-2", "@sfx/вуш-3", "@face/несуществует"])
        self.assertEqual(out["@sfx/вуш-2"].ref, "@sfx/вуш-2")
        self.assertIn("@sfx/вуш-2", [a.ref for a in out["@sfx/вуш-3"]])
        self.assertTrue(out["@face/несуществует"])
        self.assertTrue(all(a.category == "face" for a in out["@face/несуществует"]))


class AgentTagsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        _, self.footage, self.db = make_library(Path(self.tmp.name))
        data = read_index(self.footage, PACK)
        for a in data["assets"]:
            if a["id"] in (IDS["whoosh"], IDS["boom"]):
                a["agent"] = {"caption": None, "tags": ["удар", "ветер"], "at": "x"}
        write_index(self.footage, PACK, data)

    def cli(self, *args: str):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main([*args, "--db", str(self.db), "--footage-root", str(self.footage), "--json"])
        self.assertEqual(code, 0, err.getvalue())
        return json.loads(out.getvalue())

    def refs(self, *args: str) -> list[str]:
        return [c["ref"] for c in self.cli("query", *args)["assets"]]

    def test_query_ranks_author_tag_hits_first_and_skips_hidden_agent_tags(self):
        self.assertEqual(self.refs("--tag", "удар"), ["@sfx/boom", "@sfx/вуш-2"])
        self.cli("author", "set", "@sfx/вуш-2", "--tag", "удар")
        self.assertEqual(self.refs("--tag", "удар"), ["@sfx/вуш-2", "@sfx/boom"])
        shown = self.cli("author", "set", "@sfx/boom", "--hide-agent-tag", "Удар")["asset"]
        self.assertEqual((shown["agent_tags"], shown["hidden_agent_tags"]), (["ветер"], ["Удар"]))
        self.assertEqual(self.refs("--tag", "удар"), ["@sfx/вуш-2"])
        shown = self.cli("author", "set", "@sfx/boom", "--show-agent-tag", "удар")["asset"]
        self.assertEqual(shown["hidden_agent_tags"], [])
        self.assertEqual(self.refs("--tag", "удар"), ["@sfx/вуш-2", "@sfx/boom"])
