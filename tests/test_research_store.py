"""Research store: where the database lives and what a fresh one holds. No network."""

import os
import sqlite3
import tempfile
import threading
import unittest
from pathlib import Path
from unittest import mock

from cf.research import store as st


class StoreLocationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_database_lives_at_the_shared_root(self):
        for var in ("CF_SHARED_ROOT", "CF_FOOTAGE_ROOT"):
            with self.subTest(var), mock.patch.dict(os.environ, {var: str(self.dir)}, clear=False):
                for other in ("CF_FACTORY_DB", "CF_SHARED_ROOT", "CF_FOOTAGE_ROOT"):
                    if other != var:
                        os.environ.pop(other, None)
                self.assertEqual(st.default_db_path(), self.dir / "factory.db")

    def test_factory_db_variable_overrides_the_default(self):
        path = self.dir / "elsewhere" / "x.db"
        with mock.patch.dict(os.environ, {"CF_FACTORY_DB": str(path)}):
            self.assertEqual(st.default_db_path(), path)

    def test_open_creates_the_file_and_its_folder(self):
        path = self.dir / "nested" / "factory.db"
        with st.open_store(path) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)
        self.assertTrue(path.exists())

    def test_fresh_store_has_every_table_of_the_spec(self):
        with st.open_store(self.dir / "f.db") as s:
            self.assertLessEqual(
                {"watchlist", "channel", "watchlist_channel", "video", "snapshot", "card",
                 "idea", "hook", "taxonomy", "quota", "note"},
                set(s.tables()))

    def test_reopening_keeps_the_schema_version(self):
        path = self.dir / "f.db"
        with st.open_store(path):
            pass
        with st.open_store(path) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)

    def test_a_newer_database_is_refused(self):
        path = self.dir / "f.db"
        with st.open_store(path) as s:
            s.conn.execute(f"PRAGMA user_version = {st.SCHEMA_VERSION + 1}")
        with self.assertRaises(st.StoreError) as cm:
            st.open_store(path)
        self.assertIn("newer", str(cm.exception))


class MigrationTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "v2.db"

    def tearDown(self):
        self.tmp.cleanup()

    def make_v2(self) -> None:
        conn = sqlite3.connect(self.path)
        for v, script in enumerate(st.MIGRATIONS[:2]):
            conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
        conn.execute("INSERT INTO watchlist (name, format_id, channel_id, language, queries, created_at) "
                     "VALUES ('lisbon', 'walk-reel', 'travelwalks', 'pt', '[\"alfama\"]', '2026-10-01T00:00:00Z')")
        conn.execute("INSERT INTO channel (external_id, handle) VALUES ('UCaaaaaaaaaaaaaaaaaaaaaa', '@alpha')")
        conn.execute("INSERT INTO watchlist_channel (watchlist_id, channel_id, added_at) VALUES (1, 1, 'x')")
        conn.commit()
        conn.close()

    def test_v3_renames_the_authors_channel_of_a_watchlist_and_keeps_the_data(self):
        self.make_v2()
        with st.open_store(self.path, seed=False) as s:
            self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)
            cols = [r["name"] for r in s.query("PRAGMA table_info(watchlist)")]
            self.assertIn("author_channel", cols)
            self.assertNotIn("channel_id", cols)
            self.assertEqual(s.one("SELECT name, format_id, author_channel, language, queries FROM watchlist"),
                             {"name": "lisbon", "format_id": "walk-reel", "author_channel": "travelwalks",
                              "language": "pt", "queries": '["alfama"]'})
            self.assertEqual(s.one("SELECT watchlist_id, channel_id FROM watchlist_channel"),
                             {"watchlist_id": 1, "channel_id": 1})


class V7Test(unittest.TestCase):
    def test_v7_adds_pack_and_asset_tables_to_a_v5_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v5.db"
            conn = sqlite3.connect(path)
            for v, script in enumerate(st.MIGRATIONS[:5]):
                conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
            conn.execute("INSERT INTO note (kind, key, text, created_at) VALUES ('skill', 'reel', 'keep', 'x')")
            conn.commit()
            conn.close()
            with st.open_store(path, seed=False) as s:
                self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)
                self.assertLessEqual({"pack", "asset_author", "asset_alias"}, set(s.tables()))
                self.assertEqual(s.one("SELECT kind, key, text FROM note"),
                                 {"kind": "skill", "key": "reel", "text": "keep"})


class V8Test(unittest.TestCase):
    def test_v8_adds_idea_video_to_a_v7_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v7.db"
            conn = sqlite3.connect(path)
            for v, script in enumerate(st.MIGRATIONS[:7]):
                conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
            conn.execute("INSERT INTO pack (id, root, config, created_at) VALUES ('p', '/x', '{}', 'x')")
            conn.commit()
            conn.close()
            with st.open_store(path, seed=False) as s:
                self.assertEqual(s.schema_version(), st.SCHEMA_VERSION)
                self.assertIn("idea_video", s.tables())
                self.assertEqual(s.one("SELECT id, root FROM pack"), {"id": "p", "root": "/x"})
                cols = [r["name"] for r in s.query("PRAGMA table_info(idea_video)")]
                self.assertEqual(cols, ["idea_id", "video_slug", "linked_at"])
                author_cols = [r["name"] for r in s.query("PRAGMA table_info(asset_author)")]
                self.assertEqual(author_cols[-1], "hidden_agent_tags")


class V9Test(unittest.TestCase):
    def test_schema_version_is_9(self):
        self.assertEqual(st.SCHEMA_VERSION, 9)

    def test_v9_moves_the_notes_of_ingest_walk_to_ingest_footage_once(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v8.db"
            conn = sqlite3.connect(path)
            for v, script in enumerate(st.MIGRATIONS[:8]):
                conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
            for kind, key in (("skill", "ingest-walk"), ("document", ".claude/skills/ingest-walk/SKILL.md"),
                              ("skill", "reel"), ("video", "x~y"), ("document", ".claude/skills/ingest-walker/a.md"),
                              ("general", "ingest-walk")):
                conn.execute("INSERT INTO note (kind, key, text, created_at) VALUES (?, ?, 't', 'x')", (kind, key))
            conn.commit()
            conn.close()
            want = [("skill", "ingest-footage"), ("document", ".claude/skills/ingest-footage/SKILL.md"),
                    ("skill", "reel"), ("video", "x~y"), ("document", ".claude/skills/ingest-walker/a.md"),
                    ("general", "ingest-walk")]
            for _ in range(2):
                with st.open_store(path, seed=False) as s:
                    self.assertEqual(s.schema_version(), 9)
                    self.assertEqual([(r["kind"], r["key"]) for r in s.query("SELECT kind, key FROM note ORDER BY id")],
                                     want)


class ConcurrentOpenTest(unittest.TestCase):
    def test_several_connections_opening_a_fresh_database_at_once_all_get_the_full_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            for trial in range(5):
                path = Path(tmp) / f"f{trial}.db"
                gate = threading.Barrier(4)
                results: list = []

                def opener():
                    gate.wait()
                    try:
                        with st.open_store(path) as s:
                            results.append((s.schema_version(), len(s.query("SELECT 1 FROM taxonomy"))))
                    except Exception as exc:  # noqa: BLE001 - the test reports any failure
                        results.append(repr(exc))
                threads = [threading.Thread(target=opener) for _ in range(4)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()
                self.assertEqual(len(set(results)), 1, results)
                self.assertEqual(results[0][0], st.SCHEMA_VERSION)
                self.assertGreater(results[0][1], 0)

if __name__ == "__main__":
    unittest.main()
