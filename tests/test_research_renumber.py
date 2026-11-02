"""db renumber: a store in the pre-merge numbering is refused by migrate() with the hint and repaired by renumber."""

import contextlib
import io
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

from cf.research import cli, renumber
from cf.research import store as st
from old_numbering import make_old_store


def counts(path: Path) -> dict:
    conn = sqlite3.connect(path)
    try:
        return renumber.counts(conn)
    finally:
        conn.close()


class OldNumberingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / "factory.db"

    def test_opening_an_old_store_fails_with_the_renumber_hint_and_changes_nothing(self):
        make_old_store(self.path)
        before = self.path.read_bytes()
        with self.assertRaises(st.StoreError) as cm:
            st.open_store(self.path, create=True)
        self.assertIn("db renumber", str(cm.exception))
        self.assertNotIn("already exists", str(cm.exception))
        self.assertEqual(self.path.read_bytes(), before)

    def test_renumber_brings_a_version_7_store_to_the_current_version_with_rows_unchanged(self):
        make_old_store(self.path)
        old = counts(self.path)
        r = renumber.renumber(self.path)
        self.assertTrue(r["renumbered"])
        self.assertEqual((r["from_version"], r["renumbered_to"], r["version"]), (7, 8, st.SCHEMA_VERSION))
        self.assertEqual(r["changed"], {})
        self.assertTrue(Path(r["backup"]).name.endswith("-pre-renumber.db"))
        self.assertEqual(counts(Path(r["backup"])), old)
        new = counts(self.path)
        self.assertEqual({t: new[t] for t in old}, old)
        self.assertLessEqual({"insight", "watchlist_pick", "rate", "rate_pressure"}, set(new))
        with st.open_store(self.path, create=True) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)
            self.assertEqual(s.one("SELECT platform FROM channel"), {"platform": "youtube"})
            self.assertEqual(s.one("SELECT marks FROM video"), {"marks": "[]"})
            self.assertEqual(s.query("PRAGMA foreign_key_check"), [])
            self.assertEqual(s.one("PRAGMA integrity_check"), {"integrity_check": "ok"})
            self.assertIn("video_platform", [r["name"] for r in s.query("PRAGMA index_list(video)")])

    def test_renumber_brings_a_version_6_store_through_v8(self):
        make_old_store(self.path, version=6)
        r = renumber.renumber(self.path)
        self.assertEqual((r["from_version"], r["renumbered_to"], r["version"]), (6, 7, st.SCHEMA_VERSION))
        with st.open_store(self.path, seed=False, create=True) as s:
            self.assertIn("idea_video", s.tables())
            self.assertIn("hidden_agent_tags", [c["name"] for c in s.query("PRAGMA table_info(asset_author)")])

    def test_renumber_is_idempotent(self):
        make_old_store(self.path)
        renumber.renumber(self.path)
        again = renumber.renumber(self.path)
        self.assertFalse(again["renumbered"])
        self.assertIsNone(again["backup"])

    def test_renumber_refuses_a_store_in_neither_shape(self):
        conn = sqlite3.connect(self.path)
        for v, script in enumerate(st.MIGRATIONS[:5]):
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
        conn.close()
        with self.assertRaises(st.StoreError) as cm:
            renumber.renumber(self.path)
        self.assertIn("not in the old numbering", str(cm.exception))
        self.assertFalse((self.path.parent / "backups").exists())

    def test_renumber_refuses_a_missing_file_and_creates_nothing(self):
        with self.assertRaises(st.StoreError):
            renumber.renumber(self.path)
        self.assertFalse(self.path.exists())

    def test_cli_renumber_then_any_command_works(self):
        make_old_store(self.path)
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(cli.main(["db", "renumber", "--db", str(self.path), "--json"]), 0)
        self.assertEqual(json.loads(out.getvalue())["version"], st.SCHEMA_VERSION)
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(cli.main(["watchlist", "list", "--db", str(self.path)]), 0)

    def test_cli_on_an_old_store_exits_1_with_the_hint(self):
        make_old_store(self.path)
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            self.assertEqual(cli.main(["watchlist", "list", "--db", str(self.path)]), 1)
        self.assertIn("db renumber", err.getvalue())


if __name__ == "__main__":
    unittest.main()
