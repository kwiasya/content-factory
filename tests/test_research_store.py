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

    def test_default_database_lives_at_the_footage_root(self):
        env = {"CF_FOOTAGE_ROOT": str(self.dir)}
        with mock.patch.dict(os.environ, env, clear=False):
            os.environ.pop("CF_FACTORY_DB", None)
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


class V6Test(unittest.TestCase):
    def test_v6_adds_pack_and_asset_tables_to_a_v5_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "v5.db"
            conn = sqlite3.connect(path)
            for v, script in enumerate(st.MIGRATIONS[:5]):
                conn.executescript(f"BEGIN;\n{script}\nPRAGMA user_version = {v + 1};\nCOMMIT;")
            conn.execute("INSERT INTO note (kind, key, text, created_at) VALUES ('skill', 'reel', 'keep', 'x')")
            conn.commit()
            conn.close()
            with st.open_store(path, seed=False) as s:
                self.assertEqual(s.schema_version(), 6)
                self.assertLessEqual({"pack", "asset_author", "asset_alias"}, set(s.tables()))
                self.assertEqual(s.one("SELECT kind, key, text FROM note"),
                                 {"kind": "skill", "key": "reel", "text": "keep"})


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
